#!/usr/bin/env bash
# Align Cloudflare Tunnel with api.imagineer.joshwentworth.com
#
# This script reconfigures the production Cloudflare Tunnel so the dedicated API
# subdomain `api.imagineer.joshwentworth.com` proxies requests to the local
# Flask service on port 10050. The Firebase-hosted SPA continues to serve the
# root domain (`imagineer.joshwentworth.com`) via Cloudflare without using this tunnel.
#
# PREREQUISITES:
# 1. SSH access to the production server
# 2. Cloudflare tunnel already created with ID db1a99dd-3d12-4315-b241-da2a55a5c30f
# 3. Sudo access for systemctl commands
# 4. DNS (Cloudflare) record for api.imagineer.joshwentworth.com pointing at the tunnel
#
# USAGE:
#   ssh jdubz@<server-ip>
#   cd /home/jdubz/Development/imagineer
#   bash scripts/deploy/fix-api-routing.sh

set -euo pipefail

APP_DIR="/home/jdubz/Development/imagineer"
TUNNEL_CONFIG="${HOME}/.cloudflared/config.yml"
TUNNEL_SERVICE="cloudflared-imagineer-api"
API_SERVICE="imagineer-api"
API_HOSTNAME="api.imagineer.joshwentworth.com"
CREDENTIALS_FILE="${HOME}/.cloudflared/db1a99dd-3d12-4315-b241-da2a55a5c30f.json"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

error() {
  echo "[ERROR] $*" >&2
  exit 1
}

log "Starting Cloudflare Tunnel alignment..."

# Ensure we are on the production host
if [[ "$(hostname)" != "imagineer.joshwentworth.com" ]] && [[ "$(hostname)" != "imagineer" ]]; then
  error "This script must run on the production server"
fi

if [[ ! -f "${TUNNEL_CONFIG}" ]]; then
  error "Cloudflare tunnel config not found at ${TUNNEL_CONFIG}"
fi

detected_credentials=$(awk '/^credentials-file:/ {print $2}' "${TUNNEL_CONFIG}" | head -n1 || true)
if [[ -n "${detected_credentials}" ]]; then
  CREDENTIALS_FILE="${detected_credentials}"
fi

log "Current tunnel configuration:"
cat "${TUNNEL_CONFIG}"
log ""
log "Updating tunnel so ${API_HOSTNAME} maps to the Flask API..."

# Backup existing config
sudo cp "${TUNNEL_CONFIG}" "${TUNNEL_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"

# Write updated configuration
cat > /tmp/cloudflared-config.yml <<EOF
tunnel: db1a99dd-3d12-4315-b241-da2a55a5c30f
credentials-file: ${CREDENTIALS_FILE}

ingress:
  # API endpoints go to Flask backend
  - hostname: ${API_HOSTNAME}
    service: http://localhost:10050

  # Fallback
  - service: http_status:404
EOF

sudo cp /tmp/cloudflared-config.yml "${TUNNEL_CONFIG}"
sudo chown jdubz:jdubz "${TUNNEL_CONFIG}"
sudo chmod 600 "${TUNNEL_CONFIG}"

log "New tunnel configuration:"
cat "${TUNNEL_CONFIG}"

# Sanity checks for services
if ! systemctl list-unit-files | grep -q "${API_SERVICE}"; then
  error "Service ${API_SERVICE} not found. Run setup-backend.sh first."
fi

if ! systemctl list-unit-files | grep -q "${TUNNEL_SERVICE}"; then
  error "Service ${TUNNEL_SERVICE} not found. Run setup-cloudflare-tunnel-custom.sh first."
fi

log "Restarting Flask API service..."
sudo systemctl restart "${API_SERVICE}"
sleep 2

log "Verifying Flask API health..."
if ! curl -sf http://localhost:10050/api/health >/dev/null; then
  error "Flask API is not responding on http://localhost:10050/api/health"
fi

log "Flask API is healthy."

log "Restarting Cloudflare Tunnel service..."
sudo systemctl restart "${TUNNEL_SERVICE}"
sleep 3

log "Tunnel service status:"
sudo systemctl status "${TUNNEL_SERVICE}" --no-pager || true

if command -v cloudflared &> /dev/null; then
  log "Cloudflared tunnel info:"
  cloudflared tunnel info db1a99dd-3d12-4315-b241-da2a55a5c30f || true
fi

log ""
log "============================================"
log "Cloudflare Tunnel aligned with ${API_HOSTNAME}"
log "============================================"
log ""
log "Next steps:"
log "1. Ensure Cloudflare DNS CNAME for ${API_HOSTNAME} points to the tunnel ID."
log "2. Test external health check:"
log "   curl https://${API_HOSTNAME}/api/health"
log ""
log "3. Redeploy the frontend so builds target https://${API_HOSTNAME}:"
log "   cd ${APP_DIR}/web"
log "   npm run deploy:build"
log "   firebase deploy --only hosting --project static-sites-257923"
log ""
log "4. Verify the SPA at https://imagineer.joshwentworth.com makes successful API calls to https://${API_HOSTNAME}"
log ""
log "For troubleshooting, check logs:"
log "  sudo journalctl -u ${TUNNEL_SERVICE} -f"
log "  sudo journalctl -u ${API_SERVICE} -f"
log ""
