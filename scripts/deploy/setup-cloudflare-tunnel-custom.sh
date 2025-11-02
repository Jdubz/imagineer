#!/bin/bash
# Setup Cloudflare Tunnel for imagineer-api.joshwentworth.com
# Custom setup script for this specific domain

set -e

echo "🌐 Setting up Cloudflare Tunnel for imagineer-api.joshwentworth.com..."
echo ""

# Configuration
PROJECT_DIR="/home/jdubz/Development/imagineer"
TUNNEL_NAME="imagineer-api"
DOMAIN="imagineer-api.joshwentworth.com"
TUNNEL_CONFIG="${PROJECT_DIR}/terraform/cloudflare-tunnel.yml"
CLOUDFLARED_DIR="$HOME/.cloudflared"
SERVICE_NAME="cloudflared-${TUNNEL_NAME}"

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
  echo "❌ cloudflared not found. Installing..."

  # Download and install cloudflared
  wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
  sudo dpkg -i cloudflared-linux-amd64.deb
  rm cloudflared-linux-amd64.deb

  echo "✅ cloudflared installed"
fi

echo "cloudflared version: $(cloudflared --version)"
echo ""

# Check if authenticated
if [ ! -d "$CLOUDFLARED_DIR" ] || [ ! -f "$CLOUDFLARED_DIR/cert.pem" ]; then
  echo "🔐 Not authenticated with Cloudflare."
  echo "Opening browser for authentication..."
  cloudflared tunnel login
  echo "✅ Authentication complete"
  echo ""
fi

# Check if tunnel exists
if cloudflared tunnel list | grep -q "$TUNNEL_NAME"; then
  echo "✅ Tunnel already exists: $TUNNEL_NAME"
  TUNNEL_EXISTS=true
else
  echo "🔧 Creating Cloudflare Tunnel: $TUNNEL_NAME"
  cloudflared tunnel create $TUNNEL_NAME
  echo "✅ Tunnel created"
  TUNNEL_EXISTS=false
fi

# Get tunnel ID
TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
echo ""
echo "📝 Tunnel ID: $TUNNEL_ID"
echo "📝 Domain: $DOMAIN"

# Update tunnel config with actual tunnel ID
echo ""
echo "📝 Updating tunnel configuration..."
sed -i "s/TUNNEL_ID/$TUNNEL_ID/g" "$TUNNEL_CONFIG"

# Validate config
echo "🔍 Validating tunnel configuration..."
if cloudflared tunnel ingress validate --config "$TUNNEL_CONFIG"; then
  echo "✅ Tunnel configuration is valid"
else
  echo "❌ Tunnel configuration is invalid. Please fix $TUNNEL_CONFIG"
  exit 1
fi

# Show config
echo ""
echo "Tunnel configuration:"
echo "-------------------"
cat "$TUNNEL_CONFIG"
echo "-------------------"
echo ""

# Create systemd service
echo "📝 Creating systemd service..."
cat > /tmp/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Cloudflare Tunnel for Imagineer API
After=network.target

[Service]
Type=simple
User=$USER
ExecStart=/usr/local/bin/cloudflared tunnel --config ${TUNNEL_CONFIG} run ${TUNNEL_NAME}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Install service
echo "📦 Installing systemd service..."
sudo cp /tmp/${SERVICE_NAME}.service /etc/systemd/system/${SERVICE_NAME}.service
sudo systemctl daemon-reload

# Enable service
echo "✅ Enabling service..."
sudo systemctl enable ${SERVICE_NAME}

# Start service
echo "🚀 Starting service..."
sudo systemctl start ${SERVICE_NAME}

# Check status
sleep 2
if sudo systemctl is-active --quiet ${SERVICE_NAME}; then
  echo "✅ Service started successfully!"
  sudo systemctl status ${SERVICE_NAME} --no-pager
else
  echo "❌ Service failed to start. Check logs:"
  echo "   sudo journalctl -u ${SERVICE_NAME} -n 50"
  exit 1
fi

echo ""
echo "=========================================="
echo "✅ Cloudflare Tunnel Setup Complete!"
echo "=========================================="
echo ""
echo "Tunnel Details:"
echo "  Name:   $TUNNEL_NAME"
echo "  ID:     $TUNNEL_ID"
echo "  Domain: $DOMAIN"
echo ""
echo "Next Steps:"
echo ""
echo "1. Update Terraform configuration:"
echo "   Edit terraform/terraform.tfvars"
echo "   Set: tunnel_id = \"$TUNNEL_ID\""
echo ""
echo "2. Add Cloudflare API Token to terraform.tfvars"
echo "   Get from: https://dash.cloudflare.com/profile/api-tokens"
echo ""
echo "3. Deploy Cloudflare infrastructure:"
echo "   make deploy-infra"
echo ""
echo "4. Test the tunnel:"
echo "   curl http://localhost:10050/api/health"
echo "   # Should work locally"
echo ""
echo "5. After DNS is configured via Terraform:"
echo "   curl https://imagineer-api.joshwentworth.com/api/health"
echo "   # Should work publicly"
echo ""
echo "Useful Commands:"
echo "  Status:  sudo systemctl status ${SERVICE_NAME}"
echo "  Logs:    sudo journalctl -u ${SERVICE_NAME} -f"
echo "  Restart: sudo systemctl restart ${SERVICE_NAME}"
echo "  Stop:    sudo systemctl stop ${SERVICE_NAME}"
echo ""
echo "Cloudflare Dashboard:"
echo "  https://dash.cloudflare.com/"
echo ""
