"""API privada para registrar agentes RADAR e receber inventário local."""

import hashlib
import hmac
import ipaddress
import json
import logging
import os
import re
import secrets
import uuid
from datetime import date, datetime

from flask import Blueprint, jsonify, request

from backend.database import db
from backend.models import Agente, ColetaAgente, Dispositivo
from backend.network_labels import identificar_rede

agents_bp = Blueprint("agents", __name__)
logger = logging.getLogger(__name__)

LIMITES = {
    "hostname": 100,
    "tipo": 50,
    "modelo": 150,
    "sistema_op": 100,
    "armazenamento": 50,
    "memoria": 50,
    "processador": 100,
    "mac_address": 17,
    "serial_number": 50,
    "descricao": 1000,
    "uptime_fmt": 50,
    "edicao_windows": 100,
    "status_ativacao_windows": 60,
}


def _hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _redes_agente_autorizadas():
    """Retorna as sub-redes autorizadas para agentes."""
    configuracao = (
        os.getenv("RADAR_AGENT_ALLOWED_NETWORKS")
        or os.getenv("SCAN_NETWORK", "")
    )
    if not configuracao.strip():
        return []
    try:
        return [
            ipaddress.ip_network(item.strip(), strict=False)
            for item in configuracao.replace(";", ",").split(",")
            if item.strip()
        ]
    except ValueError:
        logger.error("RADAR_AGENT_ALLOWED_NETWORKS contém uma sub-rede inválida.")
        return []


def _ip_em_rede_agente_autorizada(endereco):
    try:
        ip = ipaddress.ip_address(str(endereco or "").strip())
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
    except ValueError:
        return False
    return any(ip.version == rede.version and ip in rede for rede in _redes_agente_autorizadas())


def _origem_agente_autorizada():
    """Aceita conexões de agentes apenas das redes explicitamente autorizadas."""
    origem = request.remote_addr
    try:
        endereco = ipaddress.ip_address(origem or "")
        if isinstance(endereco, ipaddress.IPv6Address) and endereco.ipv4_mapped:
            endereco = endereco.ipv4_mapped
    except ValueError:
        return False

    return any(endereco.version == rede.version and endereco in rede for rede in _redes_agente_autorizadas())


def _token_bearer():
    cabecalho = request.headers.get("Authorization", "")
    esquema, _, token = cabecalho.partition(" ")
    if esquema.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _validar_payload(payload):
    if not isinstance(payload, dict):
        return None, "O corpo deve ser um objeto JSON."
    try:
        agente_id = str(uuid.UUID(str(payload.get("agent_id", ""))))
    except (ValueError, AttributeError):
        return None, "agent_id deve ser um UUID válido."

    dados = payload.get("dados")
    if not isinstance(dados, dict):
        return None, "O campo dados deve ser um objeto JSON."

    ip = str(dados.get("ip", "")).strip()
    try:
        endereco = ipaddress.ip_address(ip)
        if endereco.version != 4:
            return None, "O inventário do agente aceita IPv4 nesta versão."
    except ValueError:
        return None, "O agente precisa informar um endereço IPv4 válido."

    normalizados = {"ip": ip}
    for campo, limite in LIMITES.items():
        valor = dados.get(campo)
        if valor is None:
            continue
        texto = str(valor).strip()
        if len(texto) > limite:
            return None, f"O campo {campo} excede {limite} caracteres."
        normalizados[campo] = texto or None

    try:
        normalizados["interfaces"] = max(0, int(dados.get("interfaces") or 0))
    except (TypeError, ValueError):
        normalizados["interfaces"] = 0

    if "licenca_windows_expira" in dados:
        data_expiracao = dados.get("licenca_windows_expira")
        if data_expiracao:
            try:
                normalizados["licenca_windows_expira"] = date.fromisoformat(str(data_expiracao)).isoformat()
            except ValueError:
                return None, "licenca_windows_expira deve estar no formato AAAA-MM-DD."
        else:
            normalizados["licenca_windows_expira"] = None

    plataforma = str(payload.get("plataforma", ""))[:40].strip()
    if not plataforma:
        return None, "O campo plataforma é obrigatório."
    return {"agent_id": agente_id, "plataforma": plataforma, "dados": normalizados}, None


def _aplicar_coleta(agente, coleta):
    dados = coleta["dados"]
    dispositivo = agente.dispositivo

    conflito = Dispositivo.query.filter(
        Dispositivo.ip == dados["ip"], Dispositivo.id != dispositivo.id
    ).first()
    if conflito:
        raise ValueError("O endereço IP informado já está associado a outro dispositivo.")

    dispositivo.ip = dados["ip"]
    # A etiqueta segue o IP local informado pelo agente. O IP de origem HTTP
    # pode ser de um roteador/NAT entre o equipamento e o servidor.
    etiqueta_rede = identificar_rede(dados["ip"])
    if etiqueta_rede:
        dispositivo.rede = etiqueta_rede
    dispositivo.status = "online"
    dispositivo.ultima_vez = datetime.now()
    dispositivo.interfaces = dados.get("interfaces", 0)
    for campo in LIMITES:
        if campo == "uptime_fmt":
            atributo = "uptime"
        else:
            atributo = campo
        valor = dados.get(campo)
        # Uma coleta parcial não deve apagar dados úteis já registrados.
        if valor:
            setattr(dispositivo, atributo, valor)

    if coleta["plataforma"].lower().startswith("win"):
        # A data é atualizada inclusive para None: WMI pode informar que não há prazo.
        if "licenca_windows_expira" in dados:
            dispositivo.licenca_windows_expira = (
                date.fromisoformat(dados["licenca_windows_expira"])
                if dados["licenca_windows_expira"] else None
            )

    if not dados.get("edicao_windows") and coleta["plataforma"].lower().startswith("win"):
        sistema_op = str(dados.get("sistema_op") or "").strip()
        edicao_windows = re.sub(r"\s*\(build\s+[^)]*\)\s*$", "", sistema_op, flags=re.IGNORECASE)
        if edicao_windows.lower().startswith("windows"):
            dispositivo.edicao_windows = edicao_windows[:100]

    agente.plataforma = coleta["plataforma"]
    agente.ultima_coleta = datetime.now()
    db.session.add(ColetaAgente(
        agente_id=agente.id,
        dados_json=json.dumps(dados, ensure_ascii=False, sort_keys=True),
    ))


@agents_bp.route("/agentes/registrar", methods=["POST"])
def registrar_agente():
    if not _origem_agente_autorizada():
        logger.warning("Registro de agente recusado; origem fora das redes permitidas: %s", request.remote_addr)
        return jsonify({"erro": "Agentes só podem se conectar pelas redes autorizadas."}), 403

    segredo = os.getenv("RADAR_AGENT_ENROLLMENT_TOKEN", "")
    recebido = _token_bearer()
    if not segredo or not recebido or not hmac.compare_digest(segredo, recebido):
        return jsonify({"erro": "Autorização de registro inválida."}), 401

    coleta, erro = _validar_payload(request.get_json(silent=True))
    if erro:
        return jsonify({"erro": erro}), 400
    if not _ip_em_rede_agente_autorizada(coleta["dados"]["ip"]):
        logger.warning(
            "Registro de agente recusado; IP informado fora das redes permitidas: %s",
            coleta["dados"]["ip"],
        )
        return jsonify({"erro": "O IP do equipamento não pertence às redes autorizadas."}), 403

    agente = db.session.get(Agente, coleta["agent_id"])
    if agente is None:
        dispositivo = Dispositivo.query.filter_by(ip=coleta["dados"]["ip"]).first()
        if dispositivo is None:
            dispositivo = Dispositivo(ip=coleta["dados"]["ip"])
            db.session.add(dispositivo)
            db.session.flush()
        elif Agente.query.filter_by(dispositivo_id=dispositivo.id).first():
            return jsonify({"erro": "Este ativo já possui um agente registrado com outra identidade."}), 409
        agente = Agente(
            id=coleta["agent_id"],
            dispositivo_id=dispositivo.id,
            token_hash="",
            plataforma=coleta["plataforma"],
        )
        db.session.add(agente)
    elif not agente.ativo:
        return jsonify({"erro": "Este agente foi desativado."}), 403

    conflito = Dispositivo.query.filter(
        Dispositivo.ip == coleta["dados"]["ip"],
        Dispositivo.id != agente.dispositivo_id,
    ).first()
    if conflito:
        return jsonify({"erro": "O endereço IP já pertence a outro ativo; solicite a resolução ao administrador."}), 409

    token = secrets.token_urlsafe(32)
    agente.token_hash = _hash_token(token)
    try:
        _aplicar_coleta(agente, coleta)
        db.session.commit()
    except ValueError as erro:
        db.session.rollback()
        return jsonify({"erro": str(erro)}), 409

    return jsonify({"agent_id": agente.id, "token": token, "mensagem": "Agente registrado."}), 201


@agents_bp.route("/agentes/inventario", methods=["POST"])
def receber_inventario():
    token = _token_bearer()
    if not token:
        return jsonify({"erro": "Token do agente obrigatório."}), 401
    agente = Agente.query.filter_by(token_hash=_hash_token(token)).first()
    if agente is None or not agente.ativo or not hmac.compare_digest(agente.token_hash, _hash_token(token)):
        return jsonify({"erro": "Token do agente inválido ou revogado."}), 401
    if not _origem_agente_autorizada():
        logger.warning("Coleta de agente recusada; origem fora das redes permitidas: %s", request.remote_addr)
        agente.dispositivo.status = "offline"
        agente.dispositivo.rede = None
        db.session.commit()
        return jsonify({"erro": "Agentes só podem se conectar pelas redes autorizadas."}), 403

    coleta, erro = _validar_payload(request.get_json(silent=True))
    if erro:
        return jsonify({"erro": erro}), 400
    if coleta["agent_id"] != agente.id:
        return jsonify({"erro": "agent_id não corresponde ao token autenticado."}), 403

    if not _ip_em_rede_agente_autorizada(coleta["dados"]["ip"]):
        logger.warning(
            "Coleta de agente recusada; IP informado fora das redes permitidas: origem=%s ip_informado=%s",
            request.remote_addr,
            coleta["dados"]["ip"],
        )
        agente.dispositivo.status = "offline"
        agente.dispositivo.rede = None
        db.session.commit()
        return jsonify({"erro": "O IP do equipamento não pertence às redes autorizadas."}), 403

    logger.info(
        "Coleta de agente aceita: origem=%s ip_informado=%s",
        request.remote_addr,
        coleta["dados"]["ip"],
    )

    try:
        _aplicar_coleta(agente, coleta)
        db.session.commit()
    except ValueError as erro:
        db.session.rollback()
        return jsonify({"erro": str(erro)}), 409

    return jsonify({"mensagem": "Inventário recebido.", "ultima_coleta": agente.ultima_coleta.isoformat()}), 200
