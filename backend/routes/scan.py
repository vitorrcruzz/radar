import os
from datetime import datetime
from flask import Blueprint, jsonify
from backend.database import db
from backend.models import Dispositivo, HistoricoVarredura

scan_bp = Blueprint("scan", __name__)

def executar_varredura(app, disparado_por: str = "automatico"):
    from collector.snmp_scanner import escanear_rede
    from backend.seed import popular_dispositivos_offline

    rede      = os.getenv("SCAN_NETWORK",   "172.20.0.0/24")
    community = os.getenv("SCAN_COMMUNITY", "public")

    with app.app_context():
        historico = HistoricoVarredura(
            iniciado_em=datetime.now(),
            disparado_por=disparado_por,
        )
        db.session.add(historico)
        db.session.commit()

        resultados   = escanear_rede(rede, community)
        total_online = 0

        for res in resultados:
            ip    = res["ip"]
            dados = res.get("dados", {})

            dispositivo = Dispositivo.query.filter_by(ip=ip).first()
            if dispositivo is None:
                dispositivo = Dispositivo(ip=ip)
                db.session.add(dispositivo)

            if res["status"] == "online":
                total_online += 1
                dispositivo.hostname      = dados.get("hostname")
                dispositivo.tipo          = dados.get("tipo")
                dispositivo.modelo        = dados.get("modelo")
                dispositivo.sistema_op    = dados.get("sistema_op")
                dispositivo.armazenamento = dados.get("armazenamento")
                dispositivo.memoria       = dados.get("memoria")
                dispositivo.processador    = dados.get("processador")
                dispositivo.mac_address    = dados.get("mac_address")
                dispositivo.serial_number  = dados.get("serial_number")
                dispositivo.descricao     = dados.get("descricao")
                dispositivo.localizacao   = dados.get("localizacao")
                dispositivo.contato       = dados.get("contato")
                dispositivo.uptime        = dados.get("uptime_fmt")
                try:
                    dispositivo.interfaces = int(dados.get("interfaces") or 0)
                except Exception:
                    dispositivo.interfaces = 0
                dispositivo.status     = "online"
                dispositivo.ultima_vez = datetime.now()
            else:
                dispositivo.status = "offline"

        db.session.commit()

        # Insere dispositivos fixos (infraestrutura + offline)
        popular_dispositivos_offline()

        # Conta totais reais do banco
        total_offline = Dispositivo.query.filter_by(status="offline").count()
        total_geral   = Dispositivo.query.count()

        historico.finalizado_em   = datetime.now()
        historico.total_escaneado = total_geral
        historico.total_online    = total_online
        historico.total_offline   = total_offline
        db.session.commit()

        return {
            "escaneados": total_geral,
            "online":     total_online,
            "offline":    total_offline,
        }

@scan_bp.route("/scan", methods=["POST"])
def disparar_varredura():
    from flask import current_app
    resultado = executar_varredura(
        current_app._get_current_object(),
        disparado_por="manual"
    )
    return jsonify({"mensagem": "Varredura concluída", **resultado})