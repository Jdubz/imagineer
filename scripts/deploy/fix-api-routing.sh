#!/usr/bin/env bash
# Fix API routing issue - Option 1 (Use main domain for API)
#
# This script fixes the API routing problem where imagineer.joshwentworth.com
# is pointing to Firebase instead of the Cloudflare Tunnel.
#
# PREREQUISITES:
# 1. SSH access to production server
# 2. Cloudflare tunnel already configured
# 3. Sudo access for systemctl commands
# 4. Remove imagineer.joshwentworth.com from Firebase Custom Domains first!
#
# USAGE:
#   ssh jdubz@imagineer.joshwentworth.com
#   cd /home/jdubz/Development/imagineer
#   bash scripts/deploy/fix-api-routing.sh

set -euo pipefail

APP_DIR="/home/jdubz/Development/imagineer"
TUNNEL_CONFIG="${HOME}/.cloudflared/config.yml"
TUNNEL_SERVICE="cloudflared-imagineer-api"
API_SERVICE="imagineer-api"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

error() {
  echo "[ERROR] $*" >&2
  exit 1
}

log "Starting API routing fix..."

# Check we're on the right server
if [[ "$(hostname)" != "imagineer.joshwentworth.com" ]] && [[ "$(hostname)" != "imagineer" ]]; then
  error "This script must run on the production server"
fi

# Check tunnel config exists
if [[ ! -f "${TUNNEL_CONFIG}" ]]; then
  error "Cloudflare tunnel config not found at ${TUNNEL_CONFIG}"
fi

log "Checking current tunnel configuration..."
cat "${TUNNEL_CONFIG}"

log ""
log "Current configuration shown above."
log "We need to ensure it routes /api/* to Flask backend."
log ""

# Backup current config
log "Backing up current tunnel configuration..."
sudo cp "${TUNNEL_CONFIG}" "${TUNNEL_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"

# Create correct tunnel configuration
log "Creating correct tunnel configuration..."
cat > /tmp/cloudflared-config.yml << 'EOF'
tunnel: db1a99dd-3d12-4315-b241-da2a55a5c30f
credentials-file: /home/jdubz/.cloudflared/db1a99dd-3d12-4315-b241-da2a55a5c30f.json

ingress:
  # API endpoints go to Flask backend
  - hostname: imagineer.joshwentworth.com
    path: /api/*
    service: http://localhost:10050

  # Everything else returns 404 (API-only domain)
  - hostname: imagineer.joshwentworth.com
    service: http_status:404

  # Fallback
  - service: http_status:404
EOF

# Install new config
log "Installing new tunnel configuration..."
sudo cp /tmp/cloudflared-config.yml "${TUNNEL_CONFIG}"
sudo chown jdubz:jdubz "${TUNNEL_CONFIG}"
sudo chmod 600 "${TUNNEL_CONFIG}"

log "New tunnel configuration:"
cat "${TUNNEL_CONFIG}"

# Check if services exist
if ! systemctl list-unit-files | grep -q "${API_SERVICE}"; then
  error "Service ${API_SERVICE} not found. Run setup-backend.sh first."
fi

if ! systemctl list-unit-files | grep -q "${TUNNEL_SERVICE}"; then
  error "Service ${TUNNEL_SERVICE} not found. Run setup-cloudflare-tunnel-custom.sh first."
fi

# Restart services
log "Restarting Flask API service..."
sudo systemctl restart "${API_SERVICE}"
sleep 2

log "Checking Flask API health..."
if ! curl -sf http://localhost:10050/api/health >/dev/null; then
  error "Flask API is not responding on http://localhost:10050/api/health"
fi

log "Flask API is healthy!"

log "Restarting Cloudflare Tunnel service..."
sudo systemctl restart "${TUNNEL_SERVICE}"
sleep 3

# Check tunnel status
log "Checking tunnel status..."
sudo systemctl status "${TUNNEL_SERVICE}" --no-pager || true

# Get tunnel info
log ""
log "Checking tunnel routing..."
if command -v cloudflared &> /dev/null; then
  cloudflared tunnel info db1a99dd-3d12-4315-b241-da2a55a5c30f || true
fi

log ""
log "============================================"
log "API routing fix completed!"
log "============================================"
log ""
log "Next steps:"
log "1. Wait 1-2 minutes for DNS propagation"
log "2. Test API endpoint:"
log "   curl https://imagineer.joshwentworth.com/api/health"
log ""
log "3. If that works, update frontend configuration:"
log "   Edit: ${APP_DIR}/web/.env.production"
log "   Change: VITE_API_BASE_URL=https://imagineer.joshwentworth.com/api"
log ""
log "4. Redeploy frontend:"
log "   cd ${APP_DIR}/web"
log "   npm run deploy:build"
log "   firebase deploy --only hosting --project static-sites-257923"
log ""
log "5. Test end-to-end at https://imagineer-generator.web.app"
log ""
log "For troubleshooting, check logs:"
log "  sudo journalctl -u ${TUNNEL_SERVICE} -f"
log "  sudo journalctl -u ${API_SERVICE} -f"
log ""
