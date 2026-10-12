from datetime import datetime
from flask import Blueprint, jsonify, request
from backend.database import db
from backend.auth import perfil_requerido
from backend.models import CampoManualDispositivo, Dispositivo, HistoricoVarredura

devices_bp = Blueprint("devices", __name__)

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
}

@devices_bp.route("/dispositivos")
def listar_dispositivos():
    tipo   = request.args.get("tipo")
    status = request.args.get("status")
    query  = Dispositivo.query
    if tipo:
        query = query.filter(Dispositivo.tipo == tipo)
    if status:
        query = query.filter(Dispositivo.status == status)
    dispositivos = query.order_by(Dispositivo.ip).all()
    return jsonify([d.to_dict() for d in dispositivos])

@devices_bp.route("/dispositivos/<int:device_id>")
def detalhar_dispositivo(device_id):
    d = Dispositivo.query.get_or_404(device_id)
    return jsonify(d.to_dict())


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
    return jsonify(dispositivo.to_dict())

@devices_bp.route("/stats")
def estatisticas():
    total   = Dispositivo.query.count()
    online  = Dispositivo.query.filter_by(status="online").count()
    offline = Dispositivo.query.filter_by(status="offline").count()

    por_tipo = db.session.query(
        Dispositivo.tipo,
        db.func.count(Dispositivo.id)
    ).group_by(Dispositivo.tipo).all()

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
