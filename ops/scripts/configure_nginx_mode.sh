#!/usr/bin/env bash
set -euo pipefail

DOMAIN=""
MODE="http"
SITE_NAME="ksr-tracker"
UPSTREAM_PORT="8000"

usage() {
  cat <<'EOF'
Usage: sudo bash ops/scripts/configure_nginx_mode.sh --domain <domain> [options]

Options:
  --domain <domain>       Public DNS name, e.g. tracker.example.org
  --mode <http|dual|https-only>
                          http       : listen on port 80 only (development)
                          dual       : serve both 80 and 443 without redirect
                          https-only : redirect 80 -> 443 (production)
  --site-name <name>      Nginx site file name (default: ksr-tracker)
  --upstream-port <port>  Local uvicorn port (default: 8000)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain)
      DOMAIN="$2"
      shift 2
      ;;
    --mode)
      MODE="$2"
      shift 2
      ;;
    --site-name)
      SITE_NAME="$2"
      shift 2
      ;;
    --upstream-port)
      UPSTREAM_PORT="$2"
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

if [[ -z "$DOMAIN" ]]; then
  echo "--domain is required" >&2
  usage
  exit 1
fi

if [[ "$MODE" != "http" && "$MODE" != "dual" && "$MODE" != "https-only" ]]; then
  echo "Invalid mode: $MODE" >&2
  usage
  exit 1
fi

CERT_DIR="/etc/letsencrypt/live/${DOMAIN}"
if [[ "$MODE" != "http" ]]; then
  if [[ ! -f "${CERT_DIR}/fullchain.pem" || ! -f "${CERT_DIR}/privkey.pem" ]]; then
    echo "TLS certificate not found for ${DOMAIN}. Run enable_https_letsencrypt.sh first." >&2
    exit 1
  fi
fi

SITE_PATH="/etc/nginx/sites-available/${SITE_NAME}.conf"

cat > "$SITE_PATH" <<EOF
server {
    listen 80;
    server_name ${DOMAIN};
EOF

if [[ "$MODE" == "https-only" ]]; then
  cat >> "$SITE_PATH" <<'EOF'
    return 301 https://$host$request_uri;
}
EOF
else
  cat >> "$SITE_PATH" <<EOF
    location / {
        proxy_pass http://127.0.0.1:${UPSTREAM_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
    }

    location /api/stream {
        proxy_pass http://127.0.0.1:${UPSTREAM_PORT}/api/stream;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding off;
    }
}
EOF
fi

if [[ "$MODE" != "http" ]]; then
  cat >> "$SITE_PATH" <<EOF

server {
    listen 443 ssl http2;
    server_name ${DOMAIN};

    ssl_certificate ${CERT_DIR}/fullchain.pem;
    ssl_certificate_key ${CERT_DIR}/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:${UPSTREAM_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
    }

    location /api/stream {
        proxy_pass http://127.0.0.1:${UPSTREAM_PORT}/api/stream;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding off;
    }
}
EOF
fi

ln -sf "$SITE_PATH" "/etc/nginx/sites-enabled/${SITE_NAME}.conf"
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl reload nginx

echo "Nginx configured for ${DOMAIN} in mode=${MODE}."
