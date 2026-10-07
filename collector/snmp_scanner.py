import asyncio
import ipaddress
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
    if "routeros" in descricao or "mikrotik" in descricao or "rtr-" in hostname:
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
        segundos = int(centisegundos or 0) // 100
        dias = segundos // 86400
        horas = (segundos % 86400) // 3600
        minutos = (segundos % 3600) // 60
        return f"{dias}d {horas}h {minutos}m"
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

        dados["uptime_fmt"] = formatar_uptime(dados.get("uptime"))
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

    try:
        return asyncio.run(
            _consultar_dispositivo(engine, ip, autenticacoes, timeout)
        )
    finally:
        engine.close_dispatcher()


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