"""Consultas para ativos que já possuem inventário coletado ou mantido manualmente."""

from sqlalchemy import and_, or_

from backend.database import db
from backend.models import Agente, CampoManualDispositivo, Dispositivo, SoftwareInstalado


def consulta_dispositivos_com_coleta():
    """Retorna ativos com coleta de agente/SNMP ou dados cadastrados manualmente.

    Hosts conhecidos somente por ICMP continuam no banco para preservar o
    histórico, mas não fazem parte do inventário operacional.
    """
    coleta_agente = db.session.query(Agente.id).filter(
        Agente.dispositivo_id == Dispositivo.id,
        Agente.ultima_coleta.isnot(None),
    ).exists()
    dados_manuais = db.session.query(CampoManualDispositivo.id).filter(
        CampoManualDispositivo.dispositivo_id == Dispositivo.id,
        CampoManualDispositivo.valor.isnot(None),
        CampoManualDispositivo.valor != "",
    ).exists()
    software_cadastrado = db.session.query(SoftwareInstalado.id).filter(
        SoftwareInstalado.dispositivo_id == Dispositivo.id,
    ).exists()

    campos_texto = (
        Dispositivo.hostname,
        Dispositivo.modelo,
        Dispositivo.sistema_op,
        Dispositivo.armazenamento,
        Dispositivo.memoria,
        Dispositivo.processador,
        Dispositivo.mac_address,
        Dispositivo.serial_number,
        Dispositivo.descricao,
        Dispositivo.localizacao,
        Dispositivo.contato,
        Dispositivo.uptime,
        Dispositivo.licenca_software,
        Dispositivo.edicao_windows,
        Dispositivo.status_ativacao_windows,
    )
    campo_com_valor = or_(
        *(campo.isnot(None) & (campo != "") for campo in campos_texto),
        Dispositivo.interfaces.isnot(None),
        Dispositivo.licenca_expira.isnot(None),
        Dispositivo.licenca_windows_expira.isnot(None),
    )
    tipo_coletado = and_(
        Dispositivo.tipo.isnot(None),
        Dispositivo.tipo != "",
        Dispositivo.tipo != "Host sem coleta",
    )
    inventario_snmp = and_(
        or_(Dispositivo.tipo.is_(None), Dispositivo.tipo != "Host sem coleta"),
        or_(campo_com_valor, tipo_coletado),
    )

    return Dispositivo.query.filter(or_(coleta_agente, dados_manuais, software_cadastrado, inventario_snmp))
