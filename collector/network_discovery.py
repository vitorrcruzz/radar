"""Descoberta auxiliar por ICMP para localizar hosts sem SNMP na rede autorizada."""

import concurrent.futures
import ipaddress
import os
import shutil
import subprocess


def _responde_ping(ip, executavel, timeout_ms):
    if os.name == "nt":
        comando = [executavel, "-n", "1", "-w", str(timeout_ms), ip]
    else:
        comando = [executavel, "-n", "-c", "1", "-W", str(max(1, (timeout_ms + 999) // 1000)), ip]
    try:
        resultado = subprocess.run(
            comando,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=(timeout_ms / 1000) + 1,
            check=False,
        )
        return resultado.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def descobrir_hosts(rede, max_concorrencia=32, timeout_ms=800, limite_hosts=4096):
    """Retorna IPv4 alcançáveis por ICMP; não tenta obter dados de hardware."""
    sub_rede = ipaddress.ip_network(rede, strict=False)
    if sub_rede.version != 4:
        raise ValueError("A descoberta auxiliar aceita somente IPv4.")
    if sub_rede.num_addresses > limite_hosts + 2:
        raise ValueError(f"A sub-rede excede o limite de {limite_hosts} hosts para descoberta ICMP.")

    executavel = shutil.which("ping")
    if not executavel:
        return []

    ips = [str(ip) for ip in sub_rede.hosts()]
    encontrados = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_concorrencia) as executor:
        tarefas = {executor.submit(_responde_ping, ip, executavel, timeout_ms): ip for ip in ips}
        for tarefa in concurrent.futures.as_completed(tarefas):
            if tarefa.result():
                encontrados.append(tarefas[tarefa])
    return sorted(encontrados, key=lambda valor: ipaddress.ip_address(valor))
