#!/bin/bash
# Restart production services after configuration changes
# Run this after updating .env.production or rebuilding frontend

set -e

echo "=========================================="
echo "Restarting Production Services"
echo "=========================================="
echo ""

# Restart API service
echo "🔄 Restarting imagineer-api service..."
sudo systemctl restart imagineer-api

# Wait for service to start
sleep 5

# Check service status
if sudo systemctl is-active --quiet imagineer-api; then
    echo "✅ imagineer-api service is running"
else
    echo "❌ imagineer-api service failed to start"
    echo ""
    echo "Check logs:"
    echo "  sudo journalctl -u imagineer-api -n 50"
    exit 1
fi

# Reload nginx
echo "🔄 Reloading nginx..."
sudo systemctl reload nginx
echo "✅ nginx reloaded"

echo ""
echo "=========================================="
echo "Testing Services"
echo "=========================================="
echo ""

# Test local API
echo "Testing local API..."
if curl -f http://localhost:10050/api/health 2>&1 | grep -q "healthy"; then
    echo "✅ Local API is healthy"
else
    echo "❌ Local API health check failed"
    echo "Response:"
    curl -s http://localhost:10050/api/health || echo "(no response)"
fi

# Test nginx serving frontend
echo ""
echo "Testing nginx (port 8080)..."
if curl -s http://localhost:8080/ | grep -q "<!DOCTYPE html>"; then
    echo "✅ nginx is serving the frontend"
else
    echo "❌ nginx is not serving the frontend correctly"
fi

# Test public endpoint
echo ""
echo "Testing public endpoint (via Cloudflare)..."
if curl -f https://imagineer-api.joshwentworth.com/api/health 2>&1 | grep -q "healthy"; then
    echo "✅ Public API is accessible"
else
    echo "⚠️  Public API not accessible (may need a moment for tunnel to update)"
fi

echo ""
echo "Testing public frontend..."
if curl -s https://imagineer.joshwentworth.com/ | grep -q "<!DOCTYPE html>"; then
    echo "✅ Public frontend is accessible"
else
    echo "⚠️  Public frontend not accessible yet"
fi

echo ""
echo "=========================================="
echo "✅ Restart Complete!"
echo "=========================================="
echo ""
echo "URLs:"
echo "  Frontend: https://imagineer.joshwentworth.com/"
echo "  API:      https://imagineer-api.joshwentworth.com/api/health"
echo ""
echo "Service logs:"
echo "  sudo journalctl -u imagineer-api -f"
echo "  sudo journalctl -u cloudflared -f"
echo ""
