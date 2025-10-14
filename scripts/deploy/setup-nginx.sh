#!/bin/bash
# Setup Nginx reverse proxy for Imagineer API
# Optional but recommended for production

set -e

echo "📦 Setting up Nginx reverse proxy..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root or with sudo"
    exit 1
fi

# Install Nginx if not present
if ! command -v nginx &> /dev/null; then
    echo "Installing Nginx..."
    apt-get update
    apt-get install -y nginx
fi

# Configuration
PROJECT_DIR="/home/jdubz/Development/imagineer"
NGINX_CONF="${PROJECT_DIR}/nginx/nginx.conf"
NGINX_SITE="/etc/nginx/sites-available/imagineer"
NGINX_ENABLED="/etc/nginx/sites-enabled/imagineer"

# Copy configuration
echo "📝 Installing Nginx configuration..."
cp "$NGINX_CONF" "$NGINX_SITE"

# Prompt for domain
read -p "Enter your API domain (e.g., api.example.com) or press Enter for localhost: " DOMAIN
if [ -z "$DOMAIN" ]; then
    DOMAIN="localhost"
fi

# Update domain in config
sed -i "s/api.your-domain.com/$DOMAIN/g" "$NGINX_SITE"

# Enable site
ln -sf "$NGINX_SITE" "$NGINX_ENABLED"

# Remove default site if exists
if [ -f "/etc/nginx/sites-enabled/default" ]; then
    rm /etc/nginx/sites-enabled/default
fi

# Test configuration
echo "🧪 Testing Nginx configuration..."
if nginx -t; then
    echo "✅ Configuration is valid"
else
    echo "❌ Configuration test failed!"
    exit 1
fi

# Restart Nginx
echo "🔄 Restarting Nginx..."
systemctl restart nginx
systemctl enable nginx

echo ""
echo "✅ Nginx setup complete!"
echo ""
echo "Configuration:"
echo "  Domain: $DOMAIN"
echo "  Upstream: localhost:10050"
echo ""
echo "Next steps:"
echo "  1. Ensure Imagineer API is running on localhost:10050"
echo "  2. Test: curl http://$DOMAIN/api/health"
echo "  3. For SSL: Run 'sudo certbot --nginx -d $DOMAIN'"
echo ""
echo "Useful commands:"
echo "  Status:  sudo systemctl status nginx"
echo "  Restart: sudo systemctl restart nginx"
echo "  Logs:    sudo tail -f /var/log/nginx/imagineer-error.log"
