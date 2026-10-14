import os
import ipaddress
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from flask import Blueprint, jsonify
from backend.auth import perfil_requerido
from backend.database import db
from backend.models import Agente, Dispositivo, HistoricoVarredura
from backend.network_labels import identificar_rede

scan_bp = Blueprint("scan", __name__)

def executar_varredura(app, disparado_por: str = "automatico"):
    from collector.snmp_scanner import escanear_rede
    from collector.wmi_collector import coletar_dados_windows, credenciais_configuradas

    rede      = os.getenv("SCAN_NETWORK",   "192.168.1.0/24")
    community = os.getenv("SCAN_COMMUNITY", "radar-lab-leitura-2026")
    sub_rede  = ipaddress.ip_network(rede, strict=False)

    with app.app_context():
        historico = HistoricoVarredura(
            iniciado_em=datetime.now(),
            disparado_por=disparado_por,
        )
        db.session.add(historico)
        db.session.commit()

        # Dispositivos conhecidos na rede começam a varredura como offline.
        # Os que responderem serão atualizados para online abaixo.
        agentes_por_dispositivo = {
            agente.dispositivo_id: agente
            for agente in Agente.query.filter_by(ativo=True).all()
        }
        for dispositivo in Dispositivo.query.all():
            etiqueta_rede = identificar_rede(dispositivo.ip)
            if etiqueta_rede:
                dispositivo.rede = etiqueta_rede
            agente = agentes_por_dispositivo.get(dispositivo.id)
            if agente:
                limite = int(os.getenv("AGENT_OFFLINE_AFTER_SECONDS", "900"))
                idade = (
                    (datetime.now() - agente.ultima_coleta).total_seconds()
                    if agente.ultima_coleta else limite + 1
                )
                if idade > limite:
                    dispositivo.status = "offline"
                elif dispositivo.status != "offline":
                    dispositivo.status = "online"
                # Agentes podem estar em outra rede autorizada (ex.: 9º andar),
                # fora da sub-rede que o scanner percorre.
                continue
            try:
                if ipaddress.ip_address(dispositivo.ip) in sub_rede:
                    dispositivo.status = "offline"
            except ValueError:
                continue

        resultados   = escanear_rede(rede, community)

        # Ping ajuda a localizar computadores sem SNMP para planejar a
        # implantação do agente. Não fornece hardware e pode ser bloqueado.
        from collector.network_discovery import descobrir_hosts
        ips_snmp = {item["ip"] for item in resultados}
        try:
            hosts_ping = descobrir_hosts(
                rede,
                max_concorrencia=int(os.getenv("DISCOVERY_CONCURRENCY", "32")),
                timeout_ms=int(os.getenv("DISCOVERY_PING_TIMEOUT_MS", "800")),
            )
        except (ValueError, OSError) as erro:
            logging.warning("Descoberta ICMP não executada (%s).", type(erro).__name__)
            hosts_ping = []
        for ip in hosts_ping:
            if ip in ips_snmp:
                continue
            resultados.append({
                "ip": ip,
                "status": "online",
                "dados": {
                    "tipo": "Host sem coleta",
                    "descricao": "Host identificado por ICMP; inventário detalhado exige agente RADAR ou resposta SNMP.",
                    "interfaces": 0,
                },
            })

        # WMI/WinRM é complementar: somente tenta hosts Windows que já
        # responderam a SNMP e somente quando o administrador configurou
        # credenciais no ambiente do RADAR.
        if credenciais_configuradas():
            alvos_windows = [
                item for item in resultados
                if "windows" in (
                    str(item.get("dados", {}).get("sistema_op", ""))
                    + " "
                    + str(item.get("dados", {}).get("descricao", ""))
                ).lower()
            ]
            with ThreadPoolExecutor(max_workers=8) as executor:
                tarefas = {
                    executor.submit(coletar_dados_windows, item["ip"]): item
                    for item in alvos_windows
                }
                for tarefa in as_completed(tarefas):
                    item = tarefas[tarefa]
                    try:
                        dados_wmi = tarefa.result()
                    except Exception as erro:
                        logging.warning(
                            "Consulta WMI/WinRM falhou para %s (%s).",
                            item["ip"],
                            type(erro).__name__,
                        )
                        continue

                    dados_snmp = item.setdefault("dados", {})
                    # WMI fornece identificação comercial; preserva os demais
                    # valores SNMP e só preenche campos ausentes, exceto CPU,
                    # onde o nome comercial é mais informativo.
                    for campo, valor in dados_wmi.items():
                        if campo == "processador" or not dados_snmp.get(campo):
                            dados_snmp[campo] = valor

        total_online = 0

        for res in resultados:
            ip    = res["ip"]
            dados = res.get("dados", {})

            dispositivo = Dispositivo.query.filter_by(ip=ip).first()
            if dispositivo is None:
                dispositivo = Dispositivo(ip=ip)
                db.session.add(dispositivo)
            etiqueta_rede = identificar_rede(ip)
            if etiqueta_rede:
                dispositivo.rede = etiqueta_rede
            agente = agentes_por_dispositivo.get(dispositivo.id)
            if agente and agente.ultima_coleta:
                limite = int(os.getenv("AGENT_OFFLINE_AFTER_SECONDS", "900"))
                idade = (datetime.now() - agente.ultima_coleta).total_seconds()
                if idade <= limite:
                    # A coleta local recente é a fonte principal do computador;
                    # SNMP não deve substituir dados mais completos do agente.
                    continue

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
                agente = agentes_por_dispositivo.get(dispositivo.id)
                if agente is None or not agente.ultima_coleta:
                    dispositivo.status = "offline"
                else:
                    limite = int(os.getenv("AGENT_OFFLINE_AFTER_SECONDS", "900"))
                    idade = (datetime.now() - agente.ultima_coleta).total_seconds()
                    dispositivo.status = "offline" if idade > limite else "online"

        db.session.commit()

        # Conta totais reais do banco
        total_offline = Dispositivo.query.filter_by(status="offline").count()
        total_online  = Dispositivo.query.filter_by(status="online").count()
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
@perfil_requerido("admin")
def disparar_varredura():
    from flask import current_app
    resultado = executar_varredura(
        current_app._get_current_object(),
        disparado_por="manual"
    )
    return jsonify({"mensagem": "Varredura concluída", **resultado})
