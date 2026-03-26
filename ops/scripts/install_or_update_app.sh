#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/ksr-tracker"
SERVICE_USER="tracker"
SERVICE_GROUP="tracker"
SERVICE_NAME="tracker-api"
REPO_DIR=""

usage() {
  cat <<'EOF'
Usage: sudo bash ops/scripts/install_or_update_app.sh [options]

Options:
  --repo-dir <path>        Source repository path (default: current working directory)
  --app-dir <path>         Deploy directory on server (default: /opt/ksr-tracker)
  --service-user <name>    Service user (default: tracker)
  --service-group <name>   Service group (default: tracker)
  --service-name <name>    Systemd service name without .service (default: tracker-api)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-dir)
      REPO_DIR="$2"
      shift 2
      ;;
    --app-dir)
      APP_DIR="$2"
      shift 2
      ;;
    --service-user)
      SERVICE_USER="$2"
      shift 2
      ;;
    --service-group)
      SERVICE_GROUP="$2"
      shift 2
      ;;
    --service-name)
      SERVICE_NAME="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ "$EUID" -ne 0 ]]; then
  echo "Run this script as root (sudo)." >&2
  exit 1
fi

if [[ -z "$REPO_DIR" ]]; then
  REPO_DIR="$(pwd)"
fi

if [[ ! -f "$REPO_DIR/server/requirements.txt" ]]; then
  echo "Could not find server/requirements.txt under $REPO_DIR" >&2
  exit 1
fi

echo "==> Installing system packages"
apt-get update
apt-get install -y python3 python3-venv python3-pip nginx rsync certbot python3-certbot-nginx

echo "==> Ensuring service user/group"
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --create-home --shell /bin/bash "$SERVICE_USER"
fi
if ! getent group "$SERVICE_GROUP" >/dev/null 2>&1; then
  groupadd --system "$SERVICE_GROUP"
fi
usermod -a -G "$SERVICE_GROUP" "$SERVICE_USER"

echo "==> Syncing application files to $APP_DIR"
mkdir -p "$APP_DIR"
rsync -a --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '.pytest_cache' \
  "$REPO_DIR/" "$APP_DIR/"

chown -R "$SERVICE_USER:$SERVICE_GROUP" "$APP_DIR"

echo "==> Creating virtualenv and installing Python dependencies"
sudo -u "$SERVICE_USER" python3 -m venv "$APP_DIR/.venv"
sudo -u "$SERVICE_USER" "$APP_DIR/.venv/bin/pip" install --upgrade pip
sudo -u "$SERVICE_USER" "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/server/requirements.txt"

echo "==> Writing systemd service"
cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=KSR Tracker API
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/.venv/bin/uvicorn server.app.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips=*
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

if [[ ! -f "$APP_DIR/.env" ]]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  chown "$SERVICE_USER:$SERVICE_GROUP" "$APP_DIR/.env"
  chmod 640 "$APP_DIR/.env"
  echo "==> Created $APP_DIR/.env from .env.example. Update secrets before production use."
fi

echo "==> Enabling and restarting service"
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"
systemctl restart "${SERVICE_NAME}.service"

systemctl --no-pager --full status "${SERVICE_NAME}.service" | sed -n '1,25p'

echo "\nDone. Next:"
echo "1) Edit ${APP_DIR}/.env with real keys/passwords"
echo "2) Configure nginx mode (http/dual/https-only) using ops/scripts/configure_nginx_mode.sh"
echo "3) Issue Let's Encrypt cert using ops/scripts/enable_https_letsencrypt.sh"
