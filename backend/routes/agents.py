"""API privada para registrar agentes RADAR e receber inventário local."""

import hashlib
import hmac
import ipaddress
import json
import os
import secrets
import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request

from backend.database import db
from backend.models import Agente, ColetaAgente, Dispositivo

agents_bp = Blueprint("agents", __name__)

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
}


def _hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


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

    agente.plataforma = coleta["plataforma"]
    agente.ultima_coleta = datetime.now()
    db.session.add(ColetaAgente(
        agente_id=agente.id,
        dados_json=json.dumps(dados, ensure_ascii=False, sort_keys=True),
    ))


@agents_bp.route("/agentes/registrar", methods=["POST"])
def registrar_agente():
    segredo = os.getenv("RADAR_AGENT_ENROLLMENT_TOKEN", "")
    recebido = _token_bearer()
    if not segredo or not recebido or not hmac.compare_digest(segredo, recebido):
        return jsonify({"erro": "Autorização de registro inválida."}), 401

    coleta, erro = _validar_payload(request.get_json(silent=True))
    if erro:
        return jsonify({"erro": erro}), 400

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

    coleta, erro = _validar_payload(request.get_json(silent=True))
    if erro:
        return jsonify({"erro": erro}), 400
    if coleta["agent_id"] != agente.id:
        return jsonify({"erro": "agent_id não corresponde ao token autenticado."}), 403

    try:
        _aplicar_coleta(agente, coleta)
        db.session.commit()
    except ValueError as erro:
        db.session.rollback()
        return jsonify({"erro": str(erro)}), 409

    return jsonify({"mensagem": "Inventário recebido.", "ultima_coleta": agente.ultima_coleta.isoformat()}), 200
