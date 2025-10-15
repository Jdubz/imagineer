#!/bin/bash
# Complete production setup script
# Sets up Docker, webhook listener, and optionally Nginx

set -e

echo "=========================================="
echo "Imagineer Production Setup"
echo "=========================================="
echo ""

# Configuration
PROJECT_DIR="/home/jdubz/Development/imagineer"
USE_DOCKER=true
USE_NGINX=false
SETUP_WEBHOOK=true

cd "$PROJECT_DIR"

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo "⚠️  No .env.production found. Creating from example..."
    cp .env.production.example .env.production
    echo "✅ Created .env.production"
    echo "⚠️  Please edit .env.production with your configuration"
    echo ""
    read -p "Press Enter to continue after editing .env.production..."
fi

# Ask deployment method
echo "Choose deployment method:"
echo "  1) Docker (recommended)"
echo "  2) Systemd (traditional)"
read -p "Enter choice [1/2]: " choice

if [ "$choice" = "2" ]; then
    USE_DOCKER=false
fi

# Ask about Nginx
read -p "Setup Nginx reverse proxy? (recommended for production) [y/N]: " nginx_choice
if [ "$nginx_choice" = "y" ] || [ "$nginx_choice" = "Y" ]; then
    USE_NGINX=true
fi

# Ask about webhook
read -p "Setup auto-deploy webhook listener? [Y/n]: " webhook_choice
if [ "$webhook_choice" = "n" ] || [ "$webhook_choice" = "N" ]; then
    SETUP_WEBHOOK=false
fi

echo ""
echo "=========================================="
echo "Setup Configuration:"
echo "  Deployment: $([ "$USE_DOCKER" = true ] && echo "Docker" || echo "Systemd")"
echo "  Nginx: $([ "$USE_NGINX" = true ] && echo "Yes" || echo "No")"
echo "  Webhook: $([ "$SETUP_WEBHOOK" = true ] && echo "Yes" || echo "No")"
echo "=========================================="
echo ""
read -p "Proceed with setup? [Y/n]: " confirm
if [ "$confirm" = "n" ] || [ "$confirm" = "N" ]; then
    echo "Setup cancelled"
    exit 0
fi

# Docker setup
if [ "$USE_DOCKER" = true ]; then
    echo ""
    echo "🐳 Setting up Docker deployment..."

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker not found. Please install Docker first:"
        echo "   curl -fsSL https://get.docker.com | sh"
        exit 1
    fi

    # Check if docker-compose is installed
    if ! command -v docker-compose &> /dev/null; then
        echo "Installing docker-compose..."
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    fi

    # Check Docker daemon
    if ! docker ps &> /dev/null; then
        echo "❌ Docker daemon not running. Starting Docker..."
        sudo systemctl start docker
        sudo systemctl enable docker
    fi

    # Build and start containers
    echo "Building Docker images..."
    docker-compose build

    echo "Starting containers..."
    docker-compose up -d

    # Wait for health check
    echo "⏳ Waiting for service to be healthy..."
    for i in {1..30}; do
        if docker-compose ps | grep -q "healthy"; then
            echo "✅ Service is healthy"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "❌ Service did not become healthy in time"
            docker-compose logs
            exit 1
        fi
        sleep 2
    done

else
    echo ""
    echo "🔧 Setting up systemd deployment..."

    # Run backend setup script
    if [ -f "scripts/deploy/setup-backend.sh" ]; then
        bash scripts/deploy/setup-backend.sh
    else
        echo "❌ Backend setup script not found!"
        exit 1
    fi
fi

# Nginx setup
if [ "$USE_NGINX" = true ]; then
    echo ""
    if [ -f "scripts/deploy/setup-nginx.sh" ]; then
        sudo bash scripts/deploy/setup-nginx.sh
    else
        echo "❌ Nginx setup script not found!"
    fi
fi

# Webhook setup
if [ "$SETUP_WEBHOOK" = true ]; then
    echo ""
    echo "🔗 Setting up webhook listener..."

    if [ "$USE_DOCKER" = true ]; then
        # Webhook runs as Docker container
        if docker-compose ps | grep -q "imagineer-webhook"; then
            echo "✅ Webhook container running"
        else
            echo "⚠️  Webhook container not running. Check docker-compose.yml"
        fi
    else
        # Create systemd service for webhook
        cat > /tmp/imagineer-webhook.service <<EOF
[Unit]
Description=Imagineer Auto-Deploy Webhook Listener
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=${PROJECT_DIR}
Environment="WEBHOOK_SECRET=changeme"
Environment="GITHUB_REPO=yourusername/imagineer"
Environment="BRANCH=main"
Environment="APP_DIR=${PROJECT_DIR}"
ExecStart=/usr/bin/python3 ${PROJECT_DIR}/scripts/deploy/webhook-listener.py

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

        sudo cp /tmp/imagineer-webhook.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable imagineer-webhook
        sudo systemctl start imagineer-webhook

        echo "✅ Webhook systemd service created"
    fi

    echo ""
    echo "⚠️  Webhook Secret Configuration:"
    echo "   Current secret: changeme"
    echo "   Update in .env.production: WEBHOOK_SECRET=your-secret-here"
    echo ""
    echo "GitHub Webhook Setup:"
    echo "   1. Go to: https://github.com/yourusername/imagineer/settings/hooks"
    echo "   2. Click 'Add webhook'"
    echo "   3. Payload URL: http://your-server-ip:9000/webhook"
    echo "   4. Content type: application/json"
    echo "   5. Secret: (use value from .env.production)"
    echo "   6. Events: Just the push event"
    echo ""
fi

echo ""
echo "=========================================="
echo "✅ Production Setup Complete!"
echo "=========================================="
echo ""
echo "Service Status:"

if [ "$USE_DOCKER" = true ]; then
    echo ""
    docker-compose ps
else
    echo ""
    sudo systemctl status imagineer-api --no-pager | head -10
fi

echo ""
echo "Test API:"
echo "  curl http://localhost:10050/api/health"

if [ "$USE_NGINX" = true ]; then
    echo "  curl http://your-domain/api/health"
fi

echo ""
echo "Useful Commands:"
if [ "$USE_DOCKER" = true ]; then
    echo "  Status:  docker-compose ps"
    echo "  Logs:    docker-compose logs -f"
    echo "  Restart: docker-compose restart"
    echo "  Stop:    docker-compose down"
else
    echo "  Status:  sudo systemctl status imagineer-api"
    echo "  Logs:    sudo journalctl -u imagineer-api -f"
    echo "  Restart: sudo systemctl restart imagineer-api"
fi

echo ""
echo "Manual Deployment:"
echo "  bash scripts/deploy/auto-deploy.sh"

echo ""
echo "Next Steps:"
echo "  1. Test the API endpoints"
echo "  2. Configure GitHub webhook (if enabled)"
echo "  3. Setup SSL certificate (if using Nginx)"
echo "  4. Configure monitoring"
echo "  5. Test auto-deployment by pushing to main branch"
