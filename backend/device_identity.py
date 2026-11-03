"""Identidade de ativos e mudança de endereço sem fundir históricos por IP."""
import os
import re
from datetime import datetime

from sqlalchemy.orm import selectinload

from backend.database import db
from backend.models import Agente, Dispositivo, HistoricoIP
from backend.network_labels import identificar_rede


def normalizar_mac(valor):
    texto = str(valor or '').strip()
    if not re.fullmatch(r'[0-9a-fA-F:.\-]+', texto):
        return None
    mac = re.sub(r'[:.\-]', '', texto).upper()
    if len(mac) != 12 or mac in {'000000000000', 'FFFFFFFFFFFF'}:
        return None
    if int(mac[:2], 16) & 1:  # multicast não identifica uma interface individual
        return None
    return mac


def normalizar_serial(valor):
    texto = str(valor or '').strip().upper()
    simples = re.sub(r'[^A-Z0-9]', '', texto)
    if len(simples) < 4 or len(set(simples)) == 1:
        return None
    if simples in {'UNKNOWN', 'NONE', 'NULL', 'NA', 'NOTAPPLICABLE', 'DEFAULTSTRING',
                   'TOBEFILLEDBYOEM', 'SYSTEMSERIALNUMBER', 'SERIALNUMBER',
                   'NOTSPECIFIED', 'NOTAVAILABLE', 'NAOINFORMADO', '123456789', '1234567890'}:
        return None
    return texto


def identidade(dispositivo):
    valores = {'mac_address': dispositivo.mac_address, 'serial_number': dispositivo.serial_number}
    for campo in dispositivo.campos_manuais:
        if campo.campo in valores and campo.valor:
            valores[campo.campo] = campo.valor
    return normalizar_mac(valores['mac_address']), normalizar_serial(valores['serial_number'])


def mesma_identidade(dispositivo, dados):
    mac, serial = identidade(dispositivo)
    novo_mac = normalizar_mac(dados.get('mac_address'))
    novo_serial = normalizar_serial(dados.get('serial_number'))
    # Um serial correspondente permite trocar Wi-Fi/Ethernet. Um MAC sozinho
    # não pode sobrepor dois números de série válidos e diferentes.
    if serial and novo_serial:
        return serial == novo_serial
    return bool(mac and novo_mac and mac == novo_mac)


def buscar_por_identidade(dados):
    mac = normalizar_mac(dados.get('mac_address'))
    serial = normalizar_serial(dados.get('serial_number'))
    if not mac and not serial:
        return None
    dispositivos = Dispositivo.query.options(selectinload(Dispositivo.campos_manuais)).all()
    candidatos = []
    for dispositivo in dispositivos:
        antigo_mac, antigo_serial = identidade(dispositivo)
        if (serial and antigo_serial == serial) or (mac and antigo_mac == mac):
            candidatos.append(dispositivo)
    if len(candidatos) > 1:
        raise ValueError('MAC ou serial repetido em cadastros diferentes; revisão necessária.')
    if candidatos and not mesma_identidade(candidatos[0], dados):
        raise ValueError('MAC correspondente com número de série diferente; revisão necessária.')
    return candidatos[0] if candidatos else None


def validar_identidade_no_ip(dispositivo, dados):
    if not dispositivo:
        return
    antiga = identidade(dispositivo)
    nova = (normalizar_mac(dados.get('mac_address')), normalizar_serial(dados.get('serial_number')))
    if any(antiga) and any(nova) and not mesma_identidade(dispositivo, dados):
        raise ValueError('O IP pertence a uma identidade diferente; cadastro preservado.')


def atividade_recente(dispositivo):
    limite = max(60, int(os.getenv('AGENT_OFFLINE_AFTER_SECONDS', '900')))
    agente = Agente.query.filter_by(dispositivo_id=dispositivo.id).first()
    instantes = [dispositivo.ultima_vez]
    if agente:
        instantes.append(agente.ultima_coleta)
    return any(instante and (datetime.now() - instante).total_seconds() <= limite for instante in instantes)


def definir_ip(dispositivo, ip, origem):
    if dispositivo.ip == ip:
        return
    db.session.add(HistoricoIP(dispositivo_id=dispositivo.id, ip_anterior=dispositivo.ip,
                               ip_novo=ip, origem=origem))
    dispositivo.ip = ip
    dispositivo.rede = identificar_rede(ip) if ip else None
    if not ip:
        dispositivo.status = 'offline'


def liberar_ocupante_antigo(ocupante, dispositivo, dados, origem, origem_confere):
    # A credencial do agente e a identidade de hardware precisam corroborar o
    # ativo que se moveu. Nunca libera um IP de outro ativo visto recentemente.
    if not origem_confere or not mesma_identidade(dispositivo, dados):
        raise ValueError('Não foi possível confirmar a identidade/origem para transferir o IP.')
    if mesma_identidade(ocupante, dados):
        raise ValueError('Há dois cadastros da mesma identidade; revisão necessária para preservar os vínculos.')
    if atividade_recente(ocupante):
        raise ValueError('O IP está associado a outro ativo com atividade recente; aguardando nova coleta.')
    definir_ip(ocupante, None, origem)
    db.session.flush()  # libera UNIQUE antes de atribuir ao novo ocupante
