import asyncio
import ipaddress
import re
from typing import Any

from pysnmp.hlapi.v3arch.asyncio import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    UsmUserData,
    USM_AUTH_NONE,
    USM_AUTH_HMAC96_MD5,
    USM_AUTH_HMAC96_SHA,
    USM_AUTH_HMAC192_SHA256,
    USM_AUTH_HMAC256_SHA384,
    USM_AUTH_HMAC384_SHA512,
    USM_PRIV_NONE,
    USM_PRIV_CBC56_DES,
    USM_PRIV_CFB128_AES,
    get_cmd,
    walk_cmd,
)


# OIDs padrão de MIB-II.
# Os OIDs privados 1.3.6.1.99.* do simulador foram removidos:
# equipamentos reais não têm obrigação de implementá-los.
OIDS = {
    "descricao": "1.3.6.1.2.1.1.1.0",
    "oid_empresa": "1.3.6.1.2.1.1.2.0",
    "uptime": "1.3.6.1.2.1.1.3.0",
    "contato": "1.3.6.1.2.1.1.4.0",
    "hostname": "1.3.6.1.2.1.1.5.0",
    "localizacao": "1.3.6.1.2.1.1.6.0",
    "interfaces": "1.3.6.1.2.1.2.1.0",
}

AUTH_PROTOCOLS = {
    "none": USM_AUTH_NONE,
    "md5": USM_AUTH_HMAC96_MD5,
    "sha": USM_AUTH_HMAC96_SHA,
    "sha1": USM_AUTH_HMAC96_SHA,
    "sha256": USM_AUTH_HMAC192_SHA256,
    "sha384": USM_AUTH_HMAC256_SHA384,
    "sha512": USM_AUTH_HMAC384_SHA512,
}

PRIV_PROTOCOLS = {
    "none": USM_PRIV_NONE,
    "des": USM_PRIV_CBC56_DES,
    "aes128": USM_PRIV_CFB128_AES,
}


def detectar_tipo(dados: dict[str, Any]) -> str:
    descricao = (dados.get("descricao") or "").lower()
    hostname = (dados.get("hostname") or "").lower()

    if "cisco" in descricao or "catalyst" in descricao or "sw-" in hostname:
        return "Switch"
    if any(termo in descricao for termo in ("routeros", "mikrotik", "vpn router", "multi-wan router")) or "rtr-" in hostname:
        return "Roteador"
    if "unifi" in descricao or "ubiquiti" in descricao or "ap-" in hostname:
        return "Access Point"
    if "hikvision" in descricao or "dahua" in descricao or "cam-" in hostname:
        return "Camera IP"
    if "smart-ups" in descricao or "apc" in descricao or "ups-" in hostname:
        return "Nobreak"
    if "laserjet" in descricao or "printer" in descricao or "imp-" in hostname:
        return "Impressora"
    if "windows" in descricao or "pc-" in hostname:
        return "Computador"
    if "notebook" in descricao or "nb-" in hostname:
        return "Notebook"
    if "linux" in descricao or "ubuntu" in descricao:
        return "Servidor"

    try:
        if int(dados.get("interfaces") or 0) >= 24:
            return "Switch"
    except (TypeError, ValueError):
        pass

    return "Desconhecido"


def formatar_uptime(centisegundos: str | None) -> str:
    try:
        if centisegundos is None:
            return "—"
        segundos = int(centisegundos) // 100
        dias = segundos // 86400
        horas = (segundos % 86400) // 3600
        minutos = (segundos % 3600) // 60
        return f"{dias}d {horas}h {minutos}m {segundos % 60}s"
    except (TypeError, ValueError):
        return "—"


def _criar_autenticacao(perfil: dict[str, Any]):
    versao = str(perfil.get("versao", "")).lower()

    if versao in {"1", "v1"}:
        community = perfil.get("community")
        if not community:
            raise ValueError("Perfil SNMPv1 precisa de community.")
        return CommunityData(str(community), mpModel=0)

    if versao in {"2", "2c", "v2c"}:
        community = perfil.get("community")
        if not community:
            raise ValueError("Perfil SNMPv2c precisa de community.")
        return CommunityData(str(community), mpModel=1)

    if versao in {"3", "v3"}:
        usuario = perfil.get("usuario")
        if not usuario:
            raise ValueError("Perfil SNMPv3 precisa de usuario.")

        protocolo_auth = str(perfil.get("auth_protocol", "none")).lower()
        protocolo_priv = str(perfil.get("priv_protocol", "none")).lower()
        chave_auth = perfil.get("auth_key") or None
        chave_priv = perfil.get("priv_key") or None

        if protocolo_auth not in AUTH_PROTOCOLS:
            raise ValueError("Protocolo de autenticação SNMPv3 não suportado.")
        if protocolo_priv not in PRIV_PROTOCOLS:
            raise ValueError("Protocolo de privacidade SNMPv3 não suportado.")
        if protocolo_auth != "none" and not chave_auth:
            raise ValueError("Perfil SNMPv3 precisa da chave de autenticação.")
        if protocolo_priv != "none" and not chave_priv:
            raise ValueError("Perfil SNMPv3 precisa da chave de privacidade.")

        return UsmUserData(
            str(usuario),
            authKey=chave_auth,
            privKey=chave_priv,
            authProtocol=AUTH_PROTOCOLS[protocolo_auth],
            privProtocol=PRIV_PROTOCOLS[protocolo_priv],
        )

    raise ValueError("Versão SNMP inválida. Use v1, v2c ou v3.")


def _normalizar_perfis(
    community: str,
    perfis_credenciais: list[dict[str, Any]] | None,
) -> list[Any]:
    # "public" fica somente como padrão para o laboratório simulado.
    # Na rede real, informe as credenciais SNMP fornecidas pela empresa.
    perfis = perfis_credenciais or [
        {"versao": "v2c", "community": community}
    ]

    if not perfis:
        raise ValueError("Informe ao menos um perfil de credenciais SNMP.")

    return [_criar_autenticacao(perfil) for perfil in perfis]


def _valor_texto(varbind) -> str | None:
    valor = varbind[1].prettyPrint()

    if not valor:
        return None

    inicio = valor.lower()
    if inicio.startswith(("no such object", "no such instance", "end of mib")):
        return None

    return valor


def detectar_sistema_operacional(descricao: str | None) -> str | None:
    if not descricao:
        return None

    windows = re.search(
        r"Windows Version\s+([\d.]+)(?:\s+\(Build\s+(\d+)\b[^)]*\))?",
        descricao,
        re.IGNORECASE,
    )
    if windows:
        versao, build = windows.groups()
        if build:
            # O serviço SNMP do Windows pode reportar a versão de
            # compatibilidade 6.3 mesmo em versões atuais. Quando o build é
            # conhecido, ele é uma identificação mais útil do produto.
            versoes_windows = {
                10240: "Windows 10 1507",
                10586: "Windows 10 1511",
                14393: "Windows 10 1607",
                15063: "Windows 10 1703",
                16299: "Windows 10 1709",
                17134: "Windows 10 1803",
                17763: "Windows 10 1809 / Windows Server 2019",
                18362: "Windows 10 1903",
                18363: "Windows 10 1909",
                19041: "Windows 10 2004",
                19042: "Windows 10 20H2",
                19043: "Windows 10 21H1",
                19044: "Windows 10 21H2",
                19045: "Windows 10 22H2",
                20348: "Windows Server 2022",
                22000: "Windows 11 21H2",
                22621: "Windows 11 22H2",
                22631: "Windows 11 23H2",
                26100: "Windows 11 24H2",
                26200: "Windows 11 25H2",
            }
            produto = versoes_windows.get(int(build))
            if produto:
                return f"{produto} (build {build})"
            return f"Windows build {build} (versão SNMP {versao})"

        return f"Windows (versão SNMP {versao})"

    linux = re.search(r"\bLinux\s+\S+\s+(\S+)", descricao, re.IGNORECASE)
    if linux:
        return f"Linux (kernel {linux.group(1)})"
    if re.search(r"\bLinux\b", descricao, re.IGNORECASE):
        return "Linux"

    return None


async def _coletar_modelo_serial(engine, autenticacao, destino):
    """Lê modelo e serial da linha chassis, se o agente expuser ENTITY-MIB."""
    raiz = "1.3.6.1.2.1.47.1.1.1.1"
    tabelas = {
        "classe": f"{raiz}.5",
        "modelo": f"{raiz}.13",
        "serial": f"{raiz}.11",
    }
    dados = {campo: None for campo in tabelas}
    for campo, oid in tabelas.items():
        dados[campo] = await _caminhar_oid(
            engine,
            autenticacao,
            destino,
            oid,
        )

    chassis = set()
    for oid_texto, valor in dados["classe"].items():
        try:
            sufixo = oid_texto.rsplit(".", 1)[1]
            if re.search(r"(?:^|\()3\)?$", valor.strip()):
                chassis.add(sufixo)
        except (IndexError, ValueError):
            continue

    resultado = {"modelo": None, "serial_number": None}
    for campo, coluna in (("modelo", "modelo"), ("serial", "serial_number")):
        for indice in sorted(chassis, key=lambda item: int(item)):
            valor = dados[campo].get(f"{raiz}.{13 if campo == 'modelo' else 11}.{indice}")
            if valor and valor.strip() and valor.strip().lower() not in {"unknown", "not specified"}:
                resultado[coluna] = valor.strip()
                break

    return resultado


async def _caminhar_oid(engine, autenticacao, destino, oid_raiz):
    valores = {}

    try:
        async for indicacao, estado, indice, varbinds in walk_cmd(
            engine,
            autenticacao,
            destino,
            ContextData(),
            ObjectType(ObjectIdentity(oid_raiz)),
            lookupMib=False,
            lexicographicMode=False,
            maxRows=100,
        ):
            if indicacao or estado:
                break

            for varbind in varbinds:
                oid = varbind[0].prettyPrint().lstrip(".")
                valores[oid] = varbind[1].prettyPrint()
    except Exception:
        return {}

    return valores


async def _coletar_memoria_armazenamento(engine, autenticacao, destino):
    dados = {"memoria": None, "armazenamento": None}

    # hrMemorySize informa a memória física em unidades de 1 KiB.
    try:
        indicacao, estado, indice, varbinds = await get_cmd(
            engine,
            autenticacao,
            destino,
            ContextData(),
            ObjectType(ObjectIdentity("1.3.6.1.2.1.25.2.2.0")),
        )

        if not indicacao and not estado and varbinds:
            memoria_kib = int(varbinds[0][1])
            dados["memoria"] = f"{memoria_kib / (1024 ** 2):.2f} GiB"
    except Exception:
        pass

    # A tabela contém descrição, tamanho da unidade e quantidade de unidades.
    raiz = "1.3.6.1.2.1.25.2.3.1"
    valores = await _caminhar_oid(engine, autenticacao, destino, raiz)
    prefixo = tuple(int(parte) for parte in raiz.split("."))
    linhas = {}

    for oid_texto, valor in valores.items():
        try:
            oid = tuple(int(parte) for parte in oid_texto.split("."))
        except ValueError:
            continue

        sufixo = oid[len(prefixo):]
        if oid[:len(prefixo)] != prefixo or len(sufixo) != 2:
            continue

        coluna, indice = sufixo
        linhas.setdefault(indice, {})[coluna] = valor

    volumes = []
    for linha in linhas.values():
        descricao = linha.get(3, "")
        unidade = linha.get(4)
        tamanho = linha.get(5)

        if not descricao or not unidade or not tamanho:
            continue

        # Inclui volumes com letra (C:, D: etc.) e deixa de fora RAM e swap.
        correspondencia = re.match(r"^([A-Za-z]):\\", descricao)
        if not correspondencia:
            continue

        try:
            total_bytes = int(unidade) * int(tamanho)
        except ValueError:
            continue

        total_gib = total_bytes / (1024 ** 3)
        volumes.append(f"{correspondencia.group(1).upper()}: {total_gib:.1f} GiB")

    if volumes:
        dados["armazenamento"] = " | ".join(sorted(volumes))

    return dados


async def _coletar_identificacao_processador(
    engine,
    autenticacao,
    destino,
    descricao_sistema: str | None,
) -> str | None:
    assinatura = None
    if descricao_sistema:
        correspondencia = re.search(
            r"Hardware:\s*(.+?)\s*-\s*Software:",
            descricao_sistema,
            re.IGNORECASE,
        )
        if correspondencia:
            assinatura = correspondencia.group(1).strip()

    raiz_carga_cpu = "1.3.6.1.2.1.25.3.3.1.2"
    cargas = await _caminhar_oid(
        engine,
        autenticacao,
        destino,
        raiz_carga_cpu,
    )
    quantidade_logica = 0
    for valor in cargas.values():
        try:
            int(valor)
            quantidade_logica += 1
        except ValueError:
            continue

    partes = []
    if assinatura:
        partes.append(assinatura)
    if quantidade_logica:
        partes.append(f"{quantidade_logica} processadores lógicos")

    return "; ".join(partes) or None


async def _obter_ifindex_por_ipv4(engine, autenticacao, destino, ip: str):
    octetos_ip = tuple(int(parte) for parte in ip.split("."))

    # Forma IPv4 legada: ipAdEntIfIndex.<octeto1>.<octeto2>.<octeto3>.<octeto4>
    raiz_legada = "1.3.6.1.2.1.4.20.1.2"
    prefixo_legado = tuple(int(parte) for parte in raiz_legada.split("."))
    entradas = await _caminhar_oid(
        engine,
        autenticacao,
        destino,
        raiz_legada,
    )

    for oid_texto, valor in entradas.items():
        try:
            oid = tuple(int(parte) for parte in oid_texto.split("."))
            if oid[:len(prefixo_legado)] == prefixo_legado:
                if oid[len(prefixo_legado):] == octetos_ip:
                    return int(valor)
        except ValueError:
            continue

    # Forma atual: ipAddressIfIndex.<ipv4(1)>.<comprimento(4)>.<octetos>
    raiz_atual = "1.3.6.1.2.1.4.34.1.3"
    prefixo_atual = tuple(int(parte) for parte in raiz_atual.split("."))
    entradas = await _caminhar_oid(
        engine,
        autenticacao,
        destino,
        raiz_atual,
    )

    sufixo_ip_atual = (1, 4, *octetos_ip)
    for oid_texto, valor in entradas.items():
        try:
            oid = tuple(int(parte) for parte in oid_texto.split("."))
            if oid[:len(prefixo_atual)] == prefixo_atual:
                if oid[len(prefixo_atual):] == sufixo_ip_atual:
                    return int(valor)
        except ValueError:
            continue

    return None


async def _coletar_mac_address(engine, autenticacao, destino, ip: str) -> str | None:
    indice = await _obter_ifindex_por_ipv4(engine, autenticacao, destino, ip)
    if indice is None:
        return None

    oid_mac = f"1.3.6.1.2.1.2.2.1.6.{indice}"
    try:
        indicacao, estado, indice_erro, varbinds = await get_cmd(
            engine,
            autenticacao,
            destino,
            ContextData(),
            ObjectType(ObjectIdentity(oid_mac)),
        )
        if indicacao or estado or not varbinds:
            return None

        valor = varbinds[0][1]
        octetos = valor.asOctets() if hasattr(valor, "asOctets") else bytes(valor)
        if len(octetos) != 6 or not any(octetos):
            return None

        return ":".join(f"{octeto:02X}" for octeto in octetos)
    except Exception:
        return None


async def _consultar_dispositivo(
    engine: SnmpEngine,
    ip: str,
    autenticacoes: list[Any],
    timeout: float,
) -> dict[str, Any]:
    resultado = {"ip": ip, "status": "offline", "dados": {}}

    objetos = [
        ObjectType(ObjectIdentity(oid))
        for oid in OIDS.values()
    ]

    for autenticacao in autenticacoes:
        try:
            destino = await UdpTransportTarget.create(
                (ip, 161),
                timeout=timeout,
                retries=0,
            )

            indicacao, estado, indice, varbinds = await get_cmd(
                engine,
                autenticacao,
                destino,
                ContextData(),
                *objetos,
            )
        except Exception:
            continue

        # Uma resposta SNMP confirma que o equipamento suporta SNMP,
        # mesmo se algum objeto solicitado não estiver disponível.
        if indicacao:
            continue

        dados = {campo: None for campo in (
            "descricao",
            "oid_empresa",
            "uptime",
            "contato",
            "hostname",
            "localizacao",
            "interfaces",
            "roteador",
            "modelo",
            "sistema_op",
            "armazenamento",
            "memoria",
            "processador",
            "serial_number",
            "mac_address",
        )}

        for campo, varbind in zip(OIDS, varbinds):
            dados[campo] = _valor_texto(varbind)

        dados.update(
            await _coletar_memoria_armazenamento(
                engine,
                autenticacao,
                destino,
            )
        )
        dados.update(
            await _coletar_modelo_serial(
                engine,
                autenticacao,
                destino,
            )
        )
        dados["mac_address"] = await _coletar_mac_address(
            engine,
            autenticacao,
            destino,
            ip,
        )
        dados["sistema_op"] = detectar_sistema_operacional(dados.get("descricao"))
        dados["processador"] = await _coletar_identificacao_processador(
            engine,
            autenticacao,
            destino,
            dados.get("descricao"),
        )

        # hrSystemUptime mede o sistema; sysUpTime mede somente o agente SNMP.
        # Consulta separada para não comprometer a coleta em MIBs sem esse OID.
        uptime_sistema = None
        try:
            erro_uptime, estado_uptime, _, valores_uptime = await get_cmd(
                engine, autenticacao, destino, ContextData(),
                ObjectType(ObjectIdentity("1.3.6.1.2.1.25.1.1.0")),
            )
            if not erro_uptime and not estado_uptime and valores_uptime:
                valor = _valor_texto(valores_uptime[0])
                if valor is not None and int(valor) >= 0:
                    uptime_sistema = valor
        except Exception:
            pass
        if uptime_sistema is not None:
            dados["uptime"] = uptime_sistema
            dados["uptime_fonte"] = "hrSystemUptime"
            dados["uptime_fmt"] = formatar_uptime(uptime_sistema)
        else:
            dados["uptime_fonte"] = "sysUpTime"
            dados["uptime_fmt"] = formatar_uptime(dados.get("uptime"))
            if dados["uptime_fmt"] != "—":
                dados["uptime_fmt"] += " (serviço SNMP)"
        dados["tipo"] = detectar_tipo(dados)

        resultado["status"] = "online"
        resultado["dados"] = dados
        return resultado

    return resultado


def _listar_ips(rede: str, limite_hosts: int) -> list[str]:
    try:
        sub_rede = ipaddress.ip_network(rede, strict=False)
    except ValueError as erro:
        raise ValueError(f"sub_rede inválida: {rede}") from erro

    if sub_rede.version != 4:
        raise ValueError("Esta primeira versão do coletor aceita apenas IPv4.")

    quantidade = sub_rede.num_addresses
    if sub_rede.prefixlen < 31:
        quantidade -= 2

    if quantidade > limite_hosts:
        raise ValueError(
            f"A rede contém {quantidade} endereços. "
            f"O limite desta varredura é {limite_hosts}."
        )

    return [str(ip) for ip in sub_rede.hosts()]


async def _escanear_rede(
    ips: list[str],
    autenticacoes: list[Any],
    max_concorrencia: int,
    timeout: float,
) -> list[dict[str, Any]]:
    engine = SnmpEngine()
    semaforo = asyncio.Semaphore(max_concorrencia)

    async def consultar_com_limite(ip: str):
        async with semaforo:
            return await _consultar_dispositivo(
                engine,
                ip,
                autenticacoes,
                timeout,
            )

    try:
        tarefas = [consultar_com_limite(ip) for ip in ips]
        resultados = await asyncio.gather(*tarefas)
    finally:
        engine.close_dispatcher()

    return [
        resultado
        for resultado in resultados
        if resultado["status"] == "online"
    ]


def escanear_dispositivo(
    ip: str,
    community: str = "public",
    perfis_credenciais: list[dict[str, Any]] | None = None,
    timeout: float = 1.5,
) -> dict[str, Any]:
    autenticacoes = _normalizar_perfis(community, perfis_credenciais)
    engine = SnmpEngine()

    async def consultar_e_fechar_motor():
        try:
            return await _consultar_dispositivo(
                engine,
                ip,
                autenticacoes,
                timeout,
            )
        finally:
            engine.close_dispatcher()

    return asyncio.run(consultar_e_fechar_motor())


def escanear_rede(
    rede: str = "172.20.0.0/24",
    community: str = "public",
    perfis_credenciais: list[dict[str, Any]] | None = None,
    max_concorrencia: int = 32,
    limite_hosts: int = 4096,
    timeout: float = 1.5,
) -> list[dict[str, Any]]:
    ips = _listar_ips(rede, limite_hosts)
    autenticacoes = _normalizar_perfis(community, perfis_credenciais)

    return asyncio.run(
        _escanear_rede(
            ips,
            autenticacoes,
            max_concorrencia,
            timeout,
        )
    )
