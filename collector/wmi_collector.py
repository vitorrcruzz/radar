"""Coleta complementar, sem agente, em computadores Windows via WinRM/WMI."""

import json
import os
from typing import Any


def credenciais_configuradas() -> bool:
    return bool(os.getenv("SCAN_WMI_USERNAME") and os.getenv("SCAN_WMI_PASSWORD"))


def coletar_dados_windows(ip: str) -> dict[str, Any]:
    """Consulta dados básicos de hardware com conta configurada no ambiente."""
    usuario = os.getenv("SCAN_WMI_USERNAME")
    senha = os.getenv("SCAN_WMI_PASSWORD")
    if not usuario or not senha:
        return {}

    import winrm

    porta = int(os.getenv("SCAN_WMI_PORT", "5985"))
    protocolo = "https" if os.getenv("SCAN_WMI_HTTPS", "false").lower() == "true" else "http"
    endpoint = f"{protocolo}://{ip}:{porta}/wsman"
    sessao = winrm.Session(
        endpoint,
        auth=(usuario, senha),
        transport="ntlm",
        operation_timeout_sec=15,
        read_timeout_sec=20,
    )

    script = r'''
$ErrorActionPreference = 'Stop'
$computer = Get-CimInstance Win32_ComputerSystem
$bios = Get-CimInstance Win32_BIOS
$os = Get-CimInstance Win32_OperatingSystem
$processors = @(Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name -Unique)
$disks = @(Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
    if ($_.Size) { "{0} {1:N1} GiB" -f $_.DeviceID, ($_.Size / 1GB) }
})
[ordered]@{
    modelo = $computer.Model
    serial_number = $bios.SerialNumber
    sistema_op = "{0} (build {1})" -f $os.Caption.Trim(), $os.BuildNumber
    processador = ($processors -join ' | ')
    memoria = "{0:N2} GiB" -f ($computer.TotalPhysicalMemory / 1GB)
    armazenamento = ($disks -join ' | ')
} | ConvertTo-Json -Compress
'''

    resposta = sessao.run_ps(script)
    if resposta.status_code != 0:
        raise RuntimeError("O computador recusou a consulta WMI/WinRM.")

    saida = resposta.std_out.decode("utf-8-sig", errors="replace").strip()
    resultado = json.loads(saida)
    if not isinstance(resultado, dict):
        raise ValueError("A resposta WMI/WinRM não contém um objeto JSON.")

    limites = {
        "modelo": 150,
        "serial_number": 50,
        "sistema_op": 100,
        "processador": 100,
        "memoria": 50,
        "armazenamento": 50,
    }
    return {
        campo: str(resultado[campo]).strip()[:limite]
        for campo, limite in limites.items()
        if resultado.get(campo) not in (None, "")
    }
