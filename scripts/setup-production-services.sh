#!/bin/bash
set -e

echo "🚀 Setting up Imagineer Production Services"
echo "============================================"
echo ""

# Check we're in the right directory
if [ ! -f "config/deployment/imagineer-api.service" ]; then
    echo "❌ Error: Run this script from /home/jdubz/Development/imagineer"
    exit 1
fi

# Check if nginx is installed
if ! command -v nginx &> /dev/null; then
    echo "📝 Step 0: Installing nginx..."
    sudo apt update
    sudo apt install -y nginx
    echo "✅ nginx installed"
    echo ""
else
    echo "✅ nginx already installed"
    echo ""
fi

echo "📝 Step 1: Installing nginx site configuration..."
sudo cp config/deployment/nginx-imagineer.conf /etc/nginx/sites-available/imagineer
sudo ln -sf /etc/nginx/sites-available/imagineer /etc/nginx/sites-enabled/imagineer
# Disable default site
sudo rm -f /etc/nginx/sites-enabled/default
echo "✅ nginx site config installed"
echo ""

echo "📝 Step 2: Testing nginx configuration..."
sudo nginx -t
echo "✅ nginx config valid"
echo ""

echo "📝 Step 3: Installing API systemd service..."
sudo cp config/deployment/imagineer-api.service /etc/systemd/system/
echo "✅ API service file installed"
echo ""

echo "📝 Step 4: Installing Cloudflare tunnel config..."
sudo mkdir -p /etc/cloudflared
sudo cp config/deployment/cloudflared-config.yml /etc/cloudflared/config.yml
echo "✅ Cloudflare config installed"
echo ""

echo "📝 Step 5: Installing Cloudflare tunnel systemd service..."
sudo cp config/deployment/cloudflared-imagineer-api.service /etc/systemd/system/
echo "✅ Cloudflare tunnel service file installed"
echo ""

echo "📝 Step 6: Reloading systemd daemon..."
sudo systemctl daemon-reload
echo "✅ Systemd reloaded"
echo ""

echo "📝 Step 7: Enabling services to start on boot..."
sudo systemctl enable nginx
sudo systemctl enable imagineer-api
sudo systemctl enable cloudflared-imagineer-api
echo "✅ Services enabled"
echo ""

echo "📝 Step 8: Starting/restarting nginx..."
sudo systemctl restart nginx
sleep 2
echo "✅ nginx started"
echo ""

echo "📝 Step 9: Starting API service..."
sudo systemctl restart imagineer-api
sleep 3
echo "✅ API service started"
echo ""

echo "📝 Step 10: Starting Cloudflare tunnel service..."
sudo systemctl restart cloudflared-imagineer-api
sleep 3
echo "✅ Cloudflare tunnel started"
echo ""

echo "🎉 Services Setup Complete!"
echo "=============================="
echo ""
echo "📊 Service Status:"
echo ""
echo "--- nginx ---"
sudo systemctl status nginx --no-pager | head -10
echo ""
echo "--- API ---"
sudo systemctl status imagineer-api --no-pager | head -10
echo ""
echo "--- Cloudflare Tunnel ---"
sudo systemctl status cloudflared-imagineer-api --no-pager | head -10
echo ""
echo "🧪 Testing Endpoints:"
echo ""
echo "Local nginx (should serve React):"
curl -s http://localhost:8080/health | head -5 || echo "⚠️  nginx not responding yet"
echo ""
echo ""
echo "Local API:"
curl -s http://localhost:10050/api/health | head -5 || echo "⚠️  API not responding yet (may need a moment to start)"
echo ""
echo ""
echo "Public endpoint (via tunnel):"
sleep 2
curl -s https://imagineer.joshwentworth.com/health | head -5 || echo "⚠️  Public endpoint not responding yet (tunnel may need a moment)"
echo ""
echo ""
echo "📝 Next Steps:"
echo "1. Check logs if needed:"
echo "   sudo journalctl -u nginx -f"
echo "   sudo journalctl -u imagineer-api -f"
echo "   sudo journalctl -u cloudflared-imagineer-api -f"
echo ""
echo "2. Deploy frontend (build and copy to public/):"
echo "   cd web && npm run build && cd .."
echo "   rm -rf public && cp -r web/dist public"
echo ""
echo "3. Test the full application:"
echo "   https://imagineer.joshwentworth.com"
echo ""
