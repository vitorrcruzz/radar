"""Mapeia endereços IPv4 para etiquetas de rede configuradas pelo administrador."""

import ipaddress
import os


def identificar_rede(endereco):
    try:
        ip = ipaddress.ip_address(str(endereco or "").strip())
    except ValueError:
        return None

    configuracao = os.getenv("RADAR_NETWORK_LABELS", "")
    for item in configuracao.split(","):
        cidr, separador, etiqueta = item.strip().partition(":")
        if not separador or not etiqueta.strip():
            continue
        try:
            rede = ipaddress.ip_network(cidr.strip(), strict=False)
        except ValueError:
            continue
        if ip.version == rede.version and ip in rede:
            return etiqueta.strip()[:100]
    return None
