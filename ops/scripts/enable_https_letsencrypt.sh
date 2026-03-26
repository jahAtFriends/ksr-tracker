#!/usr/bin/env bash
set -euo pipefail

DOMAIN=""
EMAIL=""
MODE="https-only"

usage() {
  cat <<'EOF'
Usage: sudo bash ops/scripts/enable_https_letsencrypt.sh --domain <domain> --email <email> [--mode dual|https-only]

Examples:
  # Keep both HTTP and HTTPS during testing
  sudo bash ops/scripts/enable_https_letsencrypt.sh --domain tracker.example.org --email you@example.org --mode dual

  # Final race-day mode (redirect HTTP -> HTTPS)
  sudo bash ops/scripts/enable_https_letsencrypt.sh --domain tracker.example.org --email you@example.org --mode https-only
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain)
      DOMAIN="$2"
      shift 2
      ;;
    --email)
      EMAIL="$2"
      shift 2
      ;;
    --mode)
      MODE="$2"
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

if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
  echo "--domain and --email are required" >&2
  usage
  exit 1
fi

if [[ "$MODE" != "dual" && "$MODE" != "https-only" ]]; then
  echo "--mode must be dual or https-only" >&2
  usage
  exit 1
fi

apt-get update
apt-get install -y certbot python3-certbot-nginx

# Keep nginx on HTTP while ACME challenge runs.
bash "$(dirname "$0")/configure_nginx_mode.sh" --domain "$DOMAIN" --mode http

certbot certonly --nginx \
  --non-interactive \
  --agree-tos \
  --email "$EMAIL" \
  -d "$DOMAIN"

bash "$(dirname "$0")/configure_nginx_mode.sh" --domain "$DOMAIN" --mode "$MODE"

echo "HTTPS enabled for ${DOMAIN} with mode=${MODE}."
echo "Certbot renewal timer is managed by systemd (certbot.timer)."
