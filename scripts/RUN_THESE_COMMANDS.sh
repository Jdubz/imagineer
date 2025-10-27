#!/bin/bash
# Run these commands to complete the deployment setup
# You'll need to enter your sudo password when prompted

set -e

cd /home/jdubz/Development/imagineer

echo "Installing nginx..."
sudo apt update
sudo apt install -y nginx

echo "Updating cloudflared config..."
sudo cp config/deployment/cloudflared-config.yml /etc/cloudflared/config.yml

echo "Installing nginx site configuration..."
sudo cp config/deployment/nginx-imagineer.conf /etc/nginx/sites-available/imagineer
sudo ln -sf /etc/nginx/sites-available/imagineer /etc/nginx/sites-enabled/imagineer
sudo rm -f /etc/nginx/sites-enabled/default

echo "Testing nginx configuration..."
sudo nginx -t

echo "Installing systemd services..."
sudo cp config/deployment/imagineer-api.service /etc/systemd/system/
sudo cp config/deployment/cloudflared-imagineer-api.service /etc/systemd/system/
sudo systemctl daemon-reload

echo "Enabling services..."
sudo systemctl enable nginx
sudo systemctl enable imagineer-api
sudo systemctl enable cloudflared-imagineer-api

echo "Restarting services..."
sudo systemctl restart nginx
sudo systemctl restart imagineer-api

echo "Stopping old cloudflared processes..."
sudo pkill -f "cloudflared tunnel.*imagineer-api" || true
sleep 2

echo "Starting new cloudflared service..."
sudo systemctl restart cloudflared-imagineer-api
sleep 5

echo ""
echo "✅ Setup complete! Testing endpoints..."
echo ""

curl http://localhost:8080/health
echo ""
curl http://localhost:10050/api/health
echo ""
sleep 5
curl -I https://imagineer.joshwentworth.com/health

echo ""
echo "Done! Check the output above to verify everything is working."
