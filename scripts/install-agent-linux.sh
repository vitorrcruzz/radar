#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Uso: sudo ./scripts/install-agent-linux.sh --server-url URL [opções]

Opções:
  --project-path DIR       Raiz do repositório (padrão: diretório pai de scripts/)
  --python PATH            Python 3 usado para criar o ambiente (padrão: python3)
  --ca-bundle ARQUIVO      CA PEM confiável para validar o HTTPS do RADAR
  --interval SEGUNDOS      Intervalo de coleta, mínimo 60 (padrão: 900)
  --allow-insecure-http     Permite HTTP apenas no laboratório isolado
  --help                    Mostra esta ajuda
EOF
}

PROJECT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="python3"
SERVER_URL=""
CA_BUNDLE=""
INTERVAL_SECONDS=900
ALLOW_INSECURE_HTTP=0

while (($#)); do
  case "$1" in
    --server-url) SERVER_URL="${2:?Informe a URL do servidor}"; shift 2 ;;
    --project-path) PROJECT_PATH="${2:?Informe a raiz do projeto}"; shift 2 ;;
    --python) PYTHON_BIN="${2:?Informe o executável Python}"; shift 2 ;;
    --ca-bundle) CA_BUNDLE="${2:?Informe o caminho do certificado CA}"; shift 2 ;;
    --interval) INTERVAL_SECONDS="${2:?Informe o intervalo em segundos}"; shift 2 ;;
    --allow-insecure-http) ALLOW_INSECURE_HTTP=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Opção desconhecida: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ $EUID -ne 0 ]]; then
  echo 'Execute com sudo; o serviço precisa ler os dados locais e proteger seu token.' >&2
  exit 1
fi
if [[ -z "$SERVER_URL" ]]; then
  echo '--server-url é obrigatório.' >&2
  usage >&2
  exit 2
fi
if [[ "$SERVER_URL" != https://* ]] && { ((ALLOW_INSECURE_HTTP == 0)) || [[ "$SERVER_URL" != http://* ]]; }; then
  echo 'Use HTTPS. HTTP só é aceito no laboratório com --allow-insecure-http.' >&2
  exit 2
fi
if ((ALLOW_INSECURE_HTTP)); then
  echo 'AVISO: HTTP está sem criptografia; use somente em laboratório isolado.' >&2
fi
if ! [[ "$INTERVAL_SECONDS" =~ ^[0-9]+$ ]] || ((INTERVAL_SECONDS < 60)); then
  echo '--interval deve ser um número de pelo menos 60 segundos.' >&2
  exit 2
fi
if [[ ! -f "$PROJECT_PATH/agent/client.py" || ! -f "$PROJECT_PATH/collector/host_inventory.py" ]]; then
  echo "ProjectPath não aponta para a raiz do RADAR: $PROJECT_PATH" >&2
  exit 2
fi
if [[ -n "$CA_BUNDLE" && ! -f "$CA_BUNDLE" ]]; then
  echo "Certificado CA não encontrado: $CA_BUNDLE" >&2
  exit 2
fi

INSTALL_ROOT=/opt/radar-agent
SOURCE_ROOT="$INSTALL_ROOT/src"
STATE_ROOT=/var/lib/radar-agent
STATE_FILE="$STATE_ROOT/agent.json"
LOG_FILE="$STATE_ROOT/agent.log"
UNIT_FILE=/etc/systemd/system/radar-agent.service

install -d -o root -g root -m 0755 "$INSTALL_ROOT" "$SOURCE_ROOT"
install -d -o root -g root -m 0700 "$STATE_ROOT"
cp -a "$PROJECT_PATH/agent" "$PROJECT_PATH/collector" "$SOURCE_ROOT/"
chown -R root:root "$INSTALL_ROOT"
chmod -R go-w "$INSTALL_ROOT"

if [[ ! -x "$INSTALL_ROOT/venv/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$INSTALL_ROOT/venv"
fi
"$INSTALL_ROOT/venv/bin/python" -m pip install -r "$PROJECT_PATH/agent-requirements.txt"

CA_PATH=""
if [[ -n "$CA_BUNDLE" ]]; then
  install -d -o root -g root -m 0755 /etc/radar-agent
  install -o root -g root -m 0644 "$CA_BUNDLE" /etc/radar-agent/radar-ca.pem
  CA_PATH=/etc/radar-agent/radar-ca.pem
fi

REGISTER_ARGS=(-m agent.client --register --server-url "$SERVER_URL" --state-file "$STATE_FILE")
if [[ -n "$CA_PATH" ]]; then REGISTER_ARGS+=(--ca-bundle "$CA_PATH"); fi
if ((ALLOW_INSECURE_HTTP)); then REGISTER_ARGS+=(--allow-insecure-http); fi
echo 'Informe o token de bootstrap quando solicitado; a senha não aparecerá na tela.'
(cd "$SOURCE_ROOT" && "$INSTALL_ROOT/venv/bin/python" "${REGISTER_ARGS[@]}")
chmod 0600 "$STATE_FILE"

HTTP_ARG=""
if ((ALLOW_INSECURE_HTTP)); then HTTP_ARG=' --allow-insecure-http'; fi
cat > "$UNIT_FILE" <<EOF
[Unit]
Description=Agente de inventário RADAR
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$SOURCE_ROOT
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=$INSTALL_ROOT/venv/bin/python -m agent.client --interval $INTERVAL_SECONDS --state-file $STATE_FILE --log-file $LOG_FILE$HTTP_ARG
Restart=on-failure
RestartSec=60
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ProtectKernelTunables=true
ProtectControlGroups=true
ReadWritePaths=$STATE_ROOT

[Install]
WantedBy=multi-user.target
EOF
chmod 0644 "$UNIT_FILE"
systemctl daemon-reload
systemctl enable --now radar-agent.service
echo 'Agente instalado e iniciado como serviço systemd (root; sem criar conta ou guardar senha).'
echo "Estado protegido: $STATE_FILE"
echo "Log: journalctl -u radar-agent.service"
