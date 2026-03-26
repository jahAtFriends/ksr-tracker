# Ubuntu Deployment Scripts

These scripts keep deployment simple (no Docker) and support three nginx modes:

- `http`: HTTP only (development)
- `dual`: HTTP and HTTPS both available (transition/testing)
- `https-only`: HTTP redirects to HTTPS (production/race day)

## 1) Install/Update App and Service

```bash
sudo bash ops/scripts/install_or_update_app.sh --repo-dir "$(pwd)"
```

What this does:
- Installs system packages (`python3-venv`, `nginx`, `certbot`, etc.)
- Syncs repo into `/opt/ksr-tracker`
- Creates/updates virtualenv and installs `server/requirements.txt`
- Installs/updates systemd service `tracker-api.service`
- Starts/restarts the API service

## 2) Configure Nginx Mode

```bash
sudo bash ops/scripts/configure_nginx_mode.sh --domain tracker.example.org --mode http
```

Switch modes at any time:

```bash
sudo bash ops/scripts/configure_nginx_mode.sh --domain tracker.example.org --mode dual
sudo bash ops/scripts/configure_nginx_mode.sh --domain tracker.example.org --mode https-only
```

## 3) Enable Let's Encrypt HTTPS

```bash
sudo bash ops/scripts/enable_https_letsencrypt.sh --domain tracker.example.org --email you@example.org --mode dual
```

Then when ready for deployment:

```bash
sudo bash ops/scripts/configure_nginx_mode.sh --domain tracker.example.org --mode https-only
```

## Notes

- Ensure DNS A/AAAA records point to your Ubuntu server before requesting certificates.
- Uvicorn binds to `127.0.0.1:8000`; nginx handles public traffic.
- Keep secrets in `/opt/ksr-tracker/.env` and lock down permissions.
