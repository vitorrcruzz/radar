"""Cliente de linha de comando para registrar e enviar inventário ao RADAR."""

import argparse
import getpass
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

import requests

from collector.host_inventory import coletar_inventario_local


def _caminho_estado():
    configurado = os.getenv("RADAR_AGENT_STATE")
    if configurado:
        return Path(configurado).expanduser()
    return Path.home() / ".radar" / "agent.json"


def _validar_url(url, permitir_http):
    partes = urlparse(url)
    if partes.scheme not in {"https", "http"} or not partes.netloc:
        raise ValueError("Informe uma URL completa, como https://radar.empresa.local.")
    if partes.scheme != "https" and not permitir_http:
        raise ValueError("HTTPS e obrigatório. HTTP so e permitido explicitamente em laboratorio isolado.")
    return url.rstrip("/")


def _salvar_estado(caminho, estado):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix(caminho.suffix + ".tmp")
    temporario.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(temporario, 0o600)
    except OSError:
        pass
    temporario.replace(caminho)


def _tls_verification(estado):
    ca = estado.get("ca_bundle")
    return ca if ca else True


def _configurar_log(caminho):
    if not caminho:
        return
    arquivo = Path(caminho).expanduser()
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(arquivo, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[handler],
    )


def _enviar(sessao, estado, url, dados):
    payload = {
        "agent_id": estado["agent_id"],
        "plataforma": sys.platform,
        "dados": dados,
    }
    resposta = sessao.post(
        f"{url}/api/agentes/inventario",
        json=payload,
        headers={"Authorization": f"Bearer {estado['token']}"},
        verify=_tls_verification(estado),
        timeout=20,
    )
    if not resposta.ok:
        try:
            detalhe = resposta.json().get("erro", "erro nao especificado")
        except (ValueError, AttributeError):
            detalhe = f"HTTP {resposta.status_code}"
        raise RuntimeError(f"Servidor recusou a coleta: {detalhe}")
    return resposta.json()


def registrar(args):
    url = _validar_url(args.server_url, args.allow_insecure_http)
    ca_bundle = str(Path(args.ca_bundle).expanduser().resolve()) if args.ca_bundle else None
    if ca_bundle and not Path(ca_bundle).is_file():
        raise FileNotFoundError(f"Certificado CA nao encontrado: {ca_bundle}")
    segredo = os.getenv("RADAR_AGENT_ENROLLMENT_TOKEN") or getpass.getpass("Token de registro RADAR: ")
    if not segredo.strip():
        raise ValueError("O token de registro nao pode ficar vazio.")

    caminho = Path(args.state_file).expanduser() if args.state_file else _caminho_estado()
    agente_id = None
    if caminho.is_file():
        try:
            agente_id = json.loads(caminho.read_text(encoding="utf-8")).get("agent_id")
            agente_id = str(uuid.UUID(str(agente_id))) if agente_id else None
        except (OSError, ValueError, AttributeError):
            agente_id = None
    agente_id = agente_id or str(uuid.uuid4())
    inventario = coletar_inventario_local()
    payload = {"agent_id": agente_id, "plataforma": sys.platform, "dados": inventario}
    estado_tls = {"ca_bundle": ca_bundle}
    sessao = requests.Session()
    resposta = sessao.post(
        f"{url}/api/agentes/registrar",
        json=payload,
        headers={"Authorization": f"Bearer {segredo.strip()}"},
        verify=_tls_verification(estado_tls),
        timeout=20,
    )
    if not resposta.ok:
        try:
            detalhe = resposta.json().get("erro", "erro nao especificado")
        except (ValueError, AttributeError):
            detalhe = f"HTTP {resposta.status_code}"
        raise RuntimeError(f"Registro recusado: {detalhe}")

    retorno = resposta.json()
    estado = {
        "server_url": url,
        "agent_id": retorno["agent_id"],
        "token": retorno["token"],
        "ca_bundle": ca_bundle,
    }
    _salvar_estado(caminho, estado)
    print(f"Agente registrado: {estado['agent_id']}")
    print(f"Configuraçao local gravada em: {caminho}")
    print("Guarde uma cópia segura da configuração; ela contém o token individual deste agente.")


def coletar_uma_vez(caminho, permitir_http):
    if not caminho.is_file():
        raise FileNotFoundError(f"Agente não registrado. Execute primeiro --register. Arquivo esperado: {caminho}")
    estado = json.loads(caminho.read_text(encoding="utf-8"))
    url = _validar_url(estado["server_url"], permitir_http)
    dados = coletar_inventario_local()
    retorno = _enviar(requests.Session(), estado, url, dados)
    mensagem = retorno.get("mensagem", "Coleta enviada.")
    logging.info(mensagem)
    print(mensagem)


def coletar(args):
    caminho = Path(args.state_file).expanduser() if args.state_file else _caminho_estado()
    if args.interval <= 0:
        coletar_uma_vez(caminho, args.allow_insecure_http)
        return
    while True:
        try:
            coletar_uma_vez(caminho, args.allow_insecure_http)
        except Exception as erro:
            logging.exception("Falha na coleta; nova tentativa em %ss: %s", args.interval, erro)
            print(f"Falha na coleta; nova tentativa em {args.interval:g}s: {erro}", file=sys.stderr)
        time.sleep(args.interval)


def main():
    parser = argparse.ArgumentParser(description="Coleta inventário local e envia ao servidor RADAR.")
    parser.add_argument("--state-file", help="Caminho do arquivo local com a identidade e token do agente.")
    parser.add_argument("--ca-bundle", help="Certificado CA PEM confiável para validar HTTPS na etapa de registro.")
    parser.add_argument("--log-file", help="Arquivo local de log com rotação; restrinja o acesso ao sistema e administradores.")
    parser.add_argument("--allow-insecure-http", action="store_true", help="Permite HTTP apenas para laboratório isolado; não usar em redes reais.")
    parser.add_argument("--interval", type=float, default=0, help="Repete a coleta neste intervalo em segundos; 0 envia apenas uma vez.")
    modos = parser.add_mutually_exclusive_group()
    modos.add_argument("--register", action="store_true", help="Registra este computador no servidor RADAR.")
    modos.add_argument("--once", action="store_true", help="Coleta e envia uma vez (modo padrão).")
    parser.add_argument("--server-url", help="URL base do servidor, necessária com --register.")
    args = parser.parse_args()
    _configurar_log(args.log_file)
    if args.interval and args.interval < 60:
        parser.error("--interval deve ser 0 (uma coleta) ou pelo menos 60 segundos.")

    if args.register:
        if not args.server_url:
            parser.error("--register exige --server-url.")
        registrar(args)
    else:
        coletar(args)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, requests.RequestException, RuntimeError, KeyError, subprocess.SubprocessError) as erro:
        print(f"Erro no agente RADAR: {erro}", file=sys.stderr)
        raise SystemExit(1)
