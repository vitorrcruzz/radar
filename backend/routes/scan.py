import os
import ipaddress
import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from flask import Blueprint, jsonify
from backend.auth import perfil_requerido
from backend.database import db
from backend.models import Agente, Dispositivo, HistoricoVarredura
from backend.network_labels import identificar_rede
from backend.inventory_query import consulta_dispositivos_com_coleta
from backend.device_identity import buscar_por_identidade, definir_ip, liberar_ocupante_antigo, validar_identidade_no_ip
from sqlalchemy.exc import IntegrityError

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
            if not dispositivo.ip:
                dispositivo.status = "offline"
                continue
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
                else:
                    # Uma coleta recente confirma que o agente está presente,
                    # mesmo que uma varredura anterior tenha marcado offline.
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

        # Descoberta ICMP é opcional: por padrão não varre nem persiste hosts
        # sem inventário, reduzindo carga e ruído no painel.
        if os.getenv("DISCOVERY_ICMP_ENABLED", "false").strip().lower() in {"1", "true", "yes", "sim"}:
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

            try:
                with db.session.begin_nested():
                    por_ip = Dispositivo.query.filter_by(ip=ip).first()
                    dispositivo = buscar_por_identidade(dados) if dados.get("tipo") != "Host sem coleta" else None
                    if dispositivo is not None:
                        if por_ip is not None and por_ip.id != dispositivo.id:
                            from backend.routes.agents import _host_apenas_descoberto
                            if _host_apenas_descoberto(por_ip):
                                db.session.delete(por_ip)
                                db.session.flush()
                            else:
                                liberar_ocupante_antigo(por_ip, dispositivo, dados, "snmp", True)
                        definir_ip(dispositivo, ip, "snmp")
                    else:
                        dispositivo = por_ip
                        validar_identidade_no_ip(dispositivo, dados)
                        if dispositivo is None:
                            dispositivo = Dispositivo(ip=ip)
                            db.session.add(dispositivo)
                            db.session.flush()
            except (ValueError, IntegrityError) as erro:
                logging.warning("Coleta SNMP com identidade ambígua: ip=%s motivo=%s", ip, erro)
                continue
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
                    dispositivo.status = "online"
                    continue

            if res["status"] == "online":
                if dados.get("tipo") == "Host sem coleta" and dispositivo.tipo != "Host sem coleta" and dispositivo.tipo:
                    # ICMP não comprova a identidade de quem recebeu um IP DHCP.
                    continue
                total_online += 1
                dispositivo.hostname      = dados.get("hostname")
                dispositivo.tipo          = dados.get("tipo")
                dispositivo.modelo        = dados.get("modelo")
                dispositivo.sistema_op    = dados.get("sistema_op")
                dispositivo.armazenamento = dados.get("armazenamento")
                dispositivo.memoria       = dados.get("memoria")
                dispositivo.processador    = dados.get("processador")
                dispositivo.mac_address    = dados.get("mac_address") or dispositivo.mac_address
                dispositivo.serial_number  = dados.get("serial_number") or dispositivo.serial_number
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
        inventariados = consulta_dispositivos_com_coleta()
        total_offline = inventariados.filter_by(status="offline").count()
        total_online  = inventariados.filter_by(status="online").count()
        total_geral   = inventariados.count()

        historico.finalizado_em   = datetime.now()
        historico.total_escaneado = total_geral
        historico.total_online    = total_online
        historico.total_offline   = total_offline
        db.session.commit()

        # Executado após salvar a varredura, para manter pequena a tabela de
        # resumos. Não toca em coletas dos agentes, ativos, usuários ou tokens.
        database = db.engine.url.database
        if database and database != ":memory:":
            from backend.history_retention import limpar_historico
            try:
                limpeza = limpar_historico(database, os.getenv("HISTORICO_MAX_REGISTROS", "500"))
                if limpeza["removidos"]:
                    logging.info("Retenção do histórico: removidos=%s mantidos=%s",
                                 limpeza["removidos"], limpeza["mantidos"])
            except (ValueError, OSError, sqlite3.Error):
                logging.exception("Não foi possível aplicar a retenção do histórico nesta varredura.")

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
