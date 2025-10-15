#!/bin/bash
# Auto-deployment script triggered by webhook
# Pulls latest code from main branch and restarts services

set -e

echo "=========================================="
echo "Auto-Deployment Started"
echo "=========================================="
echo "Time: $(date)"

# Configuration
APP_DIR="/home/jdubz/Development/imagineer"
BRANCH="main"
USE_DOCKER=${USE_DOCKER:-true}

cd "$APP_DIR"

echo ""
echo "📥 Pulling latest code from $BRANCH..."

# Stash any local changes (shouldn't be any in production)
git stash

# Fetch latest changes
git fetch origin

# Check if there are updates
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/$BRANCH)

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "✅ Already up to date"
    exit 0
fi

echo "📦 Updates found!"
echo "   Local:  $LOCAL"
echo "   Remote: $REMOTE"

# Checkout and pull
git checkout $BRANCH
git pull origin $BRANCH

echo ""
echo "🔧 Deploying updates..."

if [ "$USE_DOCKER" = "true" ]; then
    echo "Using Docker deployment..."

    # Rebuild and restart containers
    docker-compose build --no-cache
    docker-compose up -d

    # Wait for health check
    echo "⏳ Waiting for service to be healthy..."
    sleep 10

    # Check health
    if docker-compose ps | grep -q "unhealthy"; then
        echo "❌ Service unhealthy after deployment!"
        # Rollback
        git checkout -
        docker-compose up -d
        exit 1
    fi

    echo "✅ Service is healthy"

else
    echo "Using systemd deployment..."

    # Restart systemd service
    sudo systemctl restart imagineer-api

    # Wait for service to start
    sleep 5

    # Check if service is running
    if ! sudo systemctl is-active --quiet imagineer-api; then
        echo "❌ Service failed to start!"
        # Rollback
        git checkout -
        sudo systemctl restart imagineer-api
        exit 1
    fi

    echo "✅ Service restarted successfully"
fi

echo ""
echo "🧪 Testing deployment..."

# Test API health endpoint
for i in {1..5}; do
    if curl -f http://localhost:10050/api/health &> /dev/null; then
        echo "✅ Health check passed"
        break
    else
        if [ $i -eq 5 ]; then
            echo "❌ Health check failed after 5 attempts!"
            exit 1
        fi
        echo "⏳ Health check attempt $i failed, retrying..."
        sleep 2
    fi
done

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo "Deployed commit: $(git rev-parse --short HEAD)"
echo "Time: $(date)"

# Optional: Send notification (uncomment if you want)
# curl -X POST https://your-webhook-url.com/notify \
#   -H "Content-Type: application/json" \
#   -d "{\"message\":\"Imagineer deployed successfully\"}"
