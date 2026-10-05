from flask import Blueprint, jsonify, request
from backend.database import db
from backend.models import Dispositivo, HistoricoVarredura

devices_bp = Blueprint("devices", __name__)

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