#!/bin/bash
# Add DNS record for imagineer.joshwentworth.com to Cloudflare Tunnel
# Requires: Cloudflare API token with DNS edit permissions

set -e

echo "Adding DNS record for imagineer.joshwentworth.com"
echo ""

# Tunnel details
TUNNEL_ID="db1a99dd-3d12-4315-b241-da2a55a5c30f"
TUNNEL_NAME="imagineer-api"
DOMAIN="joshwentworth.com"
SUBDOMAIN="imagineer"

# Check if cloudflared is authenticated
if ! cloudflared tunnel list &>/dev/null; then
    echo "❌ Error: cloudflared not authenticated"
    echo "Run: cloudflared tunnel login"
    exit 1
fi

echo "📝 Creating DNS record..."
echo "Domain: ${SUBDOMAIN}.${DOMAIN}"
echo "Target: ${TUNNEL_ID}.cfargotunnel.com"
echo ""

# Add DNS route
cloudflared tunnel route dns ${TUNNEL_NAME} ${SUBDOMAIN}.${DOMAIN}

echo ""
echo "✅ DNS record added!"
echo ""
echo "Wait 1-2 minutes for DNS propagation, then test:"
echo "  curl https://${SUBDOMAIN}.${DOMAIN}/health"
echo "  curl https://${SUBDOMAIN}.${DOMAIN}/api/health"
