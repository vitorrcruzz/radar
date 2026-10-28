from datetime import date, datetime
import os
from flask import Blueprint, jsonify, request
from sqlalchemy.orm import selectinload
from backend.database import db
from backend.auth import perfil_requerido
from backend.models import Agente, CampoManualDispositivo, Dispositivo, HistoricoVarredura, SoftwareInstalado
from backend.inventory_query import consulta_dispositivos_com_coleta

devices_bp = Blueprint("devices", __name__)


def _tipo_efetivo():
    tipo_manual = db.select(CampoManualDispositivo.valor).where(
        CampoManualDispositivo.dispositivo_id == Dispositivo.id,
        CampoManualDispositivo.campo == "tipo",
    ).correlate(Dispositivo).scalar_subquery()
    return db.func.coalesce(db.func.nullif(db.func.trim(tipo_manual), ""), Dispositivo.tipo, "Desconhecido")

LIMITES_CAMPOS_MANUAIS = {
    "hostname": 100,
    "tipo": 50,
    "modelo": 150,
    "sistema_op": 100,
    "processador": 100,
    "memoria": 50,
    "armazenamento": 50,
    "mac_address": 17,
    "serial_number": 50,
    "descricao": 1000,
    "localizacao": 200,
    "contato": 200,
    "licenca_software": 100,
    "licenca_expira": 10,
    "edicao_windows": 100,
    "rede": 100,
    "interfaces": 6,
    "uptime": 50,
    "status_ativacao_windows": 60,
    "licenca_windows_expira": 10,
}

LIMITES_SOFTWARE = {
    "nome": 150,
    "fabricante": 120,
    "versao": 80,
    "tipo_licenca": 80,
    "expira_em": 10,
    "observacao": 1000,
}


def _atualizar_status_agentes():
    """Expira status de agente sem esperar a próxima varredura de rede."""
    limite = max(60, int(os.getenv("AGENT_OFFLINE_AFTER_SECONDS", "900")))
    agora = datetime.now()
    alterado = False
    for agente in Agente.query.all():
        dispositivo = agente.dispositivo
        idade = (
            (agora - agente.ultima_coleta).total_seconds()
            if agente.ultima_coleta else limite + 1
        )
        expirado = not agente.ativo or idade > limite
        if expirado and dispositivo.status == "online":
            dispositivo.status = "offline"
            alterado = True
    if alterado:
        db.session.commit()


@devices_bp.route("/dispositivos")
def listar_dispositivos():
    _atualizar_status_agentes()
    tipo   = request.args.get("tipo")
    status = request.args.get("status")
    query  = consulta_dispositivos_com_coleta().options(
        selectinload(Dispositivo.campos_manuais)
    )
    if tipo:
        query = query.filter(_tipo_efetivo() == tipo)
    if status:
        query = query.filter(Dispositivo.status == status)
    dispositivos = query.order_by(Dispositivo.ip).all()
    return jsonify([d.to_dict() for d in dispositivos])

@devices_bp.route("/dispositivos/<int:device_id>")
def detalhar_dispositivo(device_id):
    _atualizar_status_agentes()
    d = consulta_dispositivos_com_coleta().options(
        selectinload(Dispositivo.campos_manuais)
    ).filter_by(id=device_id).first_or_404()
    return jsonify(d.to_dict(incluir_software=True))


@devices_bp.route("/dispositivos/<int:device_id>/manual", methods=["PUT"])
@perfil_requerido("admin")
def atualizar_campos_manuais(device_id):
    dispositivo = Dispositivo.query.get_or_404(device_id)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"erro": "Envie um objeto JSON com os campos a atualizar."}), 400

    desconhecidos = set(payload) - set(LIMITES_CAMPOS_MANUAIS)
    if desconhecidos:
        return jsonify({"erro": "Campos não editáveis: " + ", ".join(sorted(desconhecidos))}), 400

    existentes = {campo.campo: campo for campo in dispositivo.campos_manuais}
    for nome, valor in payload.items():
        texto = "" if valor is None else str(valor).strip()
        if len(texto) > LIMITES_CAMPOS_MANUAIS[nome]:
            return jsonify({"erro": f"O campo {nome} excede {LIMITES_CAMPOS_MANUAIS[nome]} caracteres."}), 400

        if nome == "interfaces":
            if texto and (not texto.isdigit() or int(texto) > 100000):
                return jsonify({"erro": "Interfaces deve ser um número inteiro não negativo."}), 400
            registro = existentes.get(nome)
            if not texto:
                if registro:
                    db.session.delete(registro)
            else:
                if registro is None:
                    registro = CampoManualDispositivo(dispositivo=dispositivo, campo=nome)
                    db.session.add(registro)
                registro.valor = texto
                registro.atualizado_em = datetime.now()
            continue

        if nome == "licenca_windows_expira" and texto:
            try:
                date.fromisoformat(texto)
            except ValueError:
                return jsonify({"erro": "A validade informada para o Windows deve ser uma data válida."}), 400

        if nome == "licenca_software":
            dispositivo.licenca_software = texto or None
            continue
        if nome == "licenca_expira":
            if not texto:
                dispositivo.licenca_expira = None
            else:
                try:
                    dispositivo.licenca_expira = date.fromisoformat(texto)
                except ValueError:
                    return jsonify({"erro": "A validade da licença deve ser uma data válida."}), 400
            continue

        registro = existentes.get(nome)
        if not texto:
            if registro:
                db.session.delete(registro)
            continue

        if registro is None:
            registro = CampoManualDispositivo(dispositivo=dispositivo, campo=nome)
            db.session.add(registro)
        registro.valor = texto
        registro.atualizado_em = datetime.now()

    db.session.commit()
    db.session.expire(dispositivo, ["campos_manuais"])
    return jsonify(dispositivo.to_dict(incluir_software=True))


def _dados_software(payload, existente=None):
    if not isinstance(payload, dict):
        return None, "Envie os dados do software em formato válido."
    desconhecidos = set(payload) - set(LIMITES_SOFTWARE)
    if desconhecidos:
        return None, "Campos de software inválidos: " + ", ".join(sorted(desconhecidos))

    dados = {}
    for campo, limite in LIMITES_SOFTWARE.items():
        valor = payload.get(campo, getattr(existente, campo, None))
        texto = "" if valor is None else str(valor).strip()
        if len(texto) > limite:
            return None, f"O campo {campo} excede {limite} caracteres."
        if campo == "expira_em":
            if texto:
                try:
                    dados[campo] = date.fromisoformat(texto)
                except ValueError:
                    return None, "Informe uma data de validade válida."
            else:
                dados[campo] = None
        else:
            dados[campo] = texto or None

    if not dados.get("nome"):
        return None, "O nome do software é obrigatório."
    return dados, None


@devices_bp.route("/dispositivos/<int:device_id>/softwares", methods=["POST"])
@perfil_requerido("admin")
def cadastrar_software(device_id):
    dispositivo = Dispositivo.query.get_or_404(device_id)
    payload = request.get_json(silent=True)
    dados, erro = _dados_software(payload)
    if erro:
        return jsonify({"erro": erro}), 400
    software = SoftwareInstalado(dispositivo=dispositivo, **dados)
    db.session.add(software)
    db.session.commit()
    return jsonify({"software": software.to_dict(), "softwares_instalados": [s.to_dict() for s in dispositivo.softwares_instalados]}), 201


@devices_bp.route("/dispositivos/<int:device_id>/softwares/<int:software_id>", methods=["PUT", "DELETE"])
@perfil_requerido("admin")
def gerenciar_software(device_id, software_id):
    software = SoftwareInstalado.query.filter_by(id=software_id, dispositivo_id=device_id).first_or_404()
    if request.method == "DELETE":
        db.session.delete(software)
        db.session.commit()
        lista = SoftwareInstalado.query.filter_by(dispositivo_id=device_id).order_by(SoftwareInstalado.nome).all()
        return jsonify({"softwares_instalados": [s.to_dict() for s in lista]})

    dados, erro = _dados_software(request.get_json(silent=True), existente=software)
    if erro:
        return jsonify({"erro": erro}), 400
    for campo, valor in dados.items():
        setattr(software, campo, valor)
    db.session.commit()
    lista = SoftwareInstalado.query.filter_by(dispositivo_id=device_id).order_by(SoftwareInstalado.nome).all()
    return jsonify({"software": software.to_dict(), "softwares_instalados": [s.to_dict() for s in lista]})

@devices_bp.route("/stats")
def estatisticas():
    _atualizar_status_agentes()
    inventariados = consulta_dispositivos_com_coleta()
    total   = inventariados.count()
    online  = inventariados.filter_by(status="online").count()
    offline = inventariados.filter_by(status="offline").count()

    tipo_efetivo = _tipo_efetivo()
    por_tipo = inventariados.with_entities(
        tipo_efetivo,
        db.func.count(Dispositivo.id)
    ).group_by(tipo_efetivo).all()

    ultima = HistoricoVarredura.query.order_by(
        HistoricoVarredura.id.desc()
    ).first()

    return jsonify({
        "total":   total,
        "online":  online,
        "offline": offline,
        "por_tipo": [{"tipo": t, "quantidade": q} for t, q in por_tipo],
        "ultima_varredura": ultima.to_dict() if ultima else None,
    })

@devices_bp.route("/historico")
def historico():
    registros = HistoricoVarredura.query.order_by(
        HistoricoVarredura.id.desc()
    ).all()  # Remove o .limit(20)
    return jsonify([r.to_dict() for r in registros])
