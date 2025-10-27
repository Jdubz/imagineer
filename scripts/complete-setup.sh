#!/bin/bash
# Complete the deployment setup
# This script requires sudo access to:
# 1. Install/configure nginx
# 2. Update cloudflared config
# 3. Restart services

set -e

echo "🚀 Completing Imagineer Deployment Setup"
echo "=========================================="
echo ""

cd /home/jdubz/Development/imagineer

# Check if nginx is installed
if ! command -v nginx &> /dev/null; then
    echo "📦 Installing nginx..."
    sudo apt update
    sudo apt install -y nginx
    echo "✅ nginx installed"
else
    echo "✅ nginx already installed"
fi

echo ""
echo "📝 Updating cloudflared config..."
sudo cp config/deployment/cloudflared-config.yml /etc/cloudflared/config.yml
echo "✅ Cloudflared config updated"

echo ""
echo "📝 Installing nginx site configuration..."
sudo cp config/deployment/nginx-imagineer.conf /etc/nginx/sites-available/imagineer
sudo ln -sf /etc/nginx/sites-available/imagineer /etc/nginx/sites-enabled/imagineer
sudo rm -f /etc/nginx/sites-enabled/default
echo "✅ nginx site config installed"

echo ""
echo "📝 Testing nginx configuration..."
sudo nginx -t
echo "✅ nginx config valid"

echo ""
echo "📝 Installing systemd services..."
sudo cp config/deployment/imagineer-api.service /etc/systemd/system/
sudo cp config/deployment/cloudflared-imagineer-api.service /etc/systemd/system/
sudo systemctl daemon-reload
echo "✅ systemd services installed"

echo ""
echo "📝 Enabling services..."
sudo systemctl enable nginx
sudo systemctl enable imagineer-api
sudo systemctl enable cloudflared-imagineer-api
echo "✅ Services enabled"

echo ""
echo "📝 Restarting services..."
sudo systemctl restart nginx
sudo systemctl restart imagineer-api

# Need to restart the cloudflared process running the imagineer-api tunnel
echo "Stopping old cloudflared processes..."
sudo pkill -f "cloudflared tunnel.*imagineer-api" || true
sleep 2

echo "Starting new cloudflared service..."
sudo systemctl restart cloudflared-imagineer-api
sleep 3
echo "✅ Services restarted"

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""

echo "📊 Service Status:"
sudo systemctl status nginx --no-pager -l | head -10
echo ""
sudo systemctl status imagineer-api --no-pager -l | head -10
echo ""
sudo systemctl status cloudflared-imagineer-api --no-pager -l | head -10

echo ""
echo "🧪 Testing Endpoints:"
echo ""
echo "Local nginx (port 8080):"
curl -s http://localhost:8080/health || echo "⚠️  nginx not responding"
echo ""
echo ""
echo "Local API (port 10050):"
curl -s http://localhost:10050/api/health | jq -r '.status' || echo "⚠️  API not responding"
echo ""
echo ""
echo "Public endpoint (wait 10 seconds for tunnel to connect)..."
sleep 10
curl -I https://imagineer.joshwentworth.com/health 2>&1 | grep -E "HTTP|Server" || echo "⚠️  Public endpoint not responding yet (DNS may need time to propagate)"

echo ""
echo ""
echo "✅ Deployment infrastructure is ready!"
echo ""
echo "📝 Next Steps:"
echo "1. Add GitHub Secrets (see instructions below)"
echo "2. Test auto-deployment by pushing to main"
echo "3. Visit https://imagineer.joshwentworth.com"
