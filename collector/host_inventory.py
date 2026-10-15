"""Coleta local multiplataforma para o agente RADAR (sem WinRM remoto)."""

import platform
import re
import socket
import time
from datetime import datetime
from pathlib import Path

import psutil


def _ler_texto(caminho):
    try:
        return Path(caminho).read_text(encoding="utf-8", errors="replace").strip()
    except (OSError, PermissionError):
        return ""


def _formatar_gib(bytes_total):
    return f"{bytes_total / (1024 ** 3):.2f} GiB"


def _data_wmi_para_iso(valor):
    """Converte EvaluationEndDate WMI (DMTF) para YYYY-MM-DD, se definida."""
    if not valor:
        return None
    if all(hasattr(valor, campo) for campo in ("year", "month", "day")):
        try:
            return valor.date().isoformat()
        except (AttributeError, ValueError):
            pass
    texto = str(valor).strip()
    if len(texto) >= 14 and texto[:14].isdigit():
        try:
            return datetime.strptime(texto[:14], "%Y%m%d%H%M%S").date().isoformat()
        except ValueError:
            return None
    return None


def _dados_windows():
    try:
        import pythoncom
        import win32com.client
    except ImportError as erro:
        raise RuntimeError("No Windows, instale as dependências de agente que incluem pywin32.") from erro

    pythoncom.CoInitialize()
    try:
        locator = win32com.client.Dispatch("WbemScripting.SWbemLocator")
        servico = locator.ConnectServer(".", r"root\cimv2")

        def primeiro(comando):
            resultado = servico.ExecQuery(comando)
            return next(iter(resultado), None)

        computador = primeiro("SELECT Manufacturer, Model, TotalPhysicalMemory FROM Win32_ComputerSystem")
        bios = primeiro("SELECT SerialNumber FROM Win32_BIOS")
        sistema = primeiro("SELECT Caption, BuildNumber, ProductType FROM Win32_OperatingSystem")
        try:
            produtos_windows = list(servico.ExecQuery(
                "SELECT Name, LicenseStatus, EvaluationEndDate FROM SoftwareLicensingProduct "
                "WHERE ApplicationID='55c92734-d682-4d71-983e-d6ec3f16059f' "
                "AND PartialProductKey IS NOT NULL"
            ))
        except Exception:
            # Falha nesta classe não deve impedir a coleta dos demais dados WMI.
            produtos_windows = []
        processadores = list(servico.ExecQuery("SELECT Name, NumberOfLogicalProcessors FROM Win32_Processor"))
        discos = servico.ExecQuery("SELECT DeviceID, Size FROM Win32_LogicalDisk WHERE DriveType = 3")
        adaptadores = servico.ExecQuery("SELECT IPEnabled FROM Win32_NetworkAdapterConfiguration WHERE IPEnabled = TRUE")
        if not computador or not sistema:
            raise RuntimeError("WMI local não retornou os dados básicos do computador.")

        build = int(sistema.BuildNumber or 0)
        tipo_servidor = int(sistema.ProductType or 1) != 1
        caption = str(sistema.Caption or "Windows").strip()
        if tipo_servidor:
            nome_sistema = caption
            tipo = "Servidor"
        elif build >= 22000:
            familia = "Windows 11"
            edicao = re.sub(r"^Microsoft Windows(?:\s+10|\s+11)?\s*", "", caption, flags=re.IGNORECASE).strip()
            nome_sistema = f"{familia} {edicao}".strip()
            tipo = "Computador"
        elif build >= 10240:
            familia = "Windows 10"
            edicao = re.sub(r"^Microsoft Windows(?:\s+10|\s+11)?\s*", "", caption, flags=re.IGNORECASE).strip()
            nome_sistema = f"{familia} {edicao}".strip()
            tipo = "Computador"
        else:
            nome_sistema = caption
            tipo = "Computador"
        edicao_windows = re.sub(r"^Microsoft\s+", "", caption, flags=re.IGNORECASE).strip()

        # Consulta apenas status e data de avaliação; nenhuma chave é coletada.
        status_ativacao = None
        expira_em = None
        try:
            produtos_windows = [
                p for p in produtos_windows
                if "windows" in str(p.Name or "").lower()
            ]
            produto_windows = next(
                (p for p in produtos_windows if int(p.LicenseStatus or 0) == 1),
                produtos_windows[0] if produtos_windows else None,
            )
            if produto_windows:
                status_numero = int(produto_windows.LicenseStatus or 0)
                status_ativacao = {
                    0: "Não licenciado",
                    1: "Ativo",
                    2: "Período de carência inicial",
                    3: "Período de carência",
                    4: "Período de carência não genuína",
                    5: "Notificação de ativação",
                    6: "Período de carência estendido",
                }.get(status_numero, "Estado de ativação desconhecido")
                expira_em = _data_wmi_para_iso(
                    getattr(produto_windows, "EvaluationEndDate", None)
                )
        except Exception:
            # A licença é complementar; uma falha no provider não pode derrubar o inventário.
            status_ativacao = None
            expira_em = None

        volumes = []
        for disco in discos:
            try:
                capacidade = int(disco.Size or 0)
            except (TypeError, ValueError):
                continue
            if capacidade > 0:
                volumes.append(f"{disco.DeviceID} {_formatar_gib(capacidade)}")

        uptime_segundos = max(0, int(time.time() - psutil.boot_time()))
        dias, resto = divmod(uptime_segundos, 86400)
        horas, resto = divmod(resto, 3600)
        minutos = resto // 60
        fabricante = str(computador.Manufacturer or "").strip()
        modelo = str(computador.Model or "").strip()
        nomes_cpu = sorted({str(cpu.Name).strip() for cpu in processadores if cpu.Name})
        processadores_logicos = sum(int(cpu.NumberOfLogicalProcessors or 0) for cpu in processadores)
        processador = " | ".join(nomes_cpu) or None
        if processador and processadores_logicos:
            processador = f"{processador}; {processadores_logicos} processadores lógicos"

        return {
            "hostname": socket.gethostname(),
            "tipo": tipo,
            "modelo": f"{fabricante} {modelo}".strip() or None,
            "serial_number": str(bios.SerialNumber or "").strip() or None if bios else None,
            "sistema_op": f"{nome_sistema} (build {build})",
            "edicao_windows": edicao_windows[:100],
            "status_ativacao_windows": status_ativacao,
            "licenca_windows_expira": expira_em,
            "processador": processador,
            "memoria": _formatar_gib(int(computador.TotalPhysicalMemory or 0)),
            "armazenamento": " | ".join(volumes) or None,
            "uptime_fmt": f"{dias}d {horas}h {minutos}m",
            "interfaces": sum(1 for _ in adaptadores),
        }
    finally:
        pythoncom.CoUninitialize()


def _interface_principal():
    estatisticas = psutil.net_if_stats()
    interfaces = psutil.net_if_addrs()
    descartadas = ("loopback", "virtual", "vethernet", "docker", "tailscale", "vmware", "virtualbox", "hyper-v")
    candidatas = []
    for nome, enderecos in interfaces.items():
        estado = estatisticas.get(nome)
        if not estado or not estado.isup or any(item in nome.lower() for item in descartadas):
            continue
        ipv4 = next((a.address for a in enderecos if a.family == socket.AF_INET and not a.address.startswith("127.") and not a.address.startswith("169.254.")), None)
        mac = next((a.address for a in enderecos if getattr(psutil, "AF_LINK", None) == a.family), None)
        if not ipv4:
            continue
        prioridade = 0 if re.search(r"ethernet|wi-?fi|wlan|en[0-9]|eth[0-9]", nome, re.I) else 1
        candidatas.append((prioridade, nome, ipv4, mac))
    candidatas.sort()
    if not candidatas:
        raise RuntimeError("Nenhuma interface ativa com IPv4 foi encontrada.")
    _, nome, ipv4, mac = candidatas[0]
    return nome, ipv4, mac


def _dados_linux():
    os_info = {}
    try:
        os_info = platform.freedesktop_os_release()
    except (AttributeError, OSError):
        pass
    modelo = _ler_texto("/sys/class/dmi/id/product_name")
    fabricante = _ler_texto("/sys/class/dmi/id/sys_vendor")
    serial = _ler_texto("/sys/class/dmi/id/product_serial")
    if serial.lower() in {"none", "not specified", "unknown"}:
        serial = ""
    cpu = platform.processor()
    if not cpu:
        for linha in _ler_texto("/proc/cpuinfo").splitlines():
            if linha.lower().startswith(("model name", "hardware")):
                cpu = linha.split(":", 1)[-1].strip()
                break

    volumes = []
    for particao in psutil.disk_partitions(all=False):
        if not particao.device.startswith("/"):
            continue
        try:
            uso = psutil.disk_usage(particao.mountpoint)
        except (OSError, PermissionError):
            continue
        volumes.append(f"{particao.mountpoint} {_formatar_gib(uso.total)}")

    nome_if, ip, mac = _interface_principal()
    uptime_segundos = max(0, int(time.time() - psutil.boot_time()))
    dias, resto = divmod(uptime_segundos, 86400)
    horas, resto = divmod(resto, 3600)
    minutos = resto // 60
    return {
        "ip": ip,
        "hostname": socket.gethostname(),
        "tipo": "Computador",
        "modelo": f"{fabricante} {modelo}".strip() or None,
        "serial_number": serial or None,
        "sistema_op": f"{os_info.get('PRETTY_NAME') or platform.platform()} ({platform.machine()})",
        "processador": f"{cpu}; {psutil.cpu_count(logical=True)} processadores lógicos" if cpu and psutil.cpu_count(logical=True) else cpu or None,
        "memoria": _formatar_gib(psutil.virtual_memory().total),
        "armazenamento": " | ".join(volumes) or None,
        "mac_address": mac,
        "uptime_fmt": f"{dias}d {horas}h {minutos}m",
        "interfaces": len([n for n, s in psutil.net_if_stats().items() if s.isup]),
        "descricao": f"Interface principal: {nome_if}",
    }


def coletar_inventario_local(incluir_software=False):
    """Retorna o inventário local; o argumento legado não habilita coleta de programas."""
    sistema = platform.system()
    if sistema == "Windows":
        dados = _dados_windows()
        _, dados["ip"], dados["mac_address"] = _interface_principal()
        dados["hostname"] = socket.gethostname()
        dados.setdefault("tipo", "Computador")
        return dados
    if sistema == "Linux":
        return _dados_linux()
    raise RuntimeError(f"Sistema operacional não suportado pelo agente: {sistema}")
