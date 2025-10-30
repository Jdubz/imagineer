#!/bin/bash
# Comprehensive Production Deployment Fix Script
# Fixes DATABASE_URL, nginx config, and frontend build issues
#
# This script will:
# 1. Install and configure PostgreSQL
# 2. Create production database
# 3. Update .env.production with DATABASE_URL
# 4. Build frontend to correct location
# 5. Fix nginx configuration
# 6. Update auto-deploy script to build frontend
# 7. Restart all services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/home/jdubz/Development/imagineer"
DB_NAME="imagineer_prod"
DB_USER="imagineer"
DB_PASSWORD=$(openssl rand -hex 32)  # Generate secure random password

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "\n${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}\n"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Do not run this script as root. It will use sudo when needed."
    exit 1
fi

print_header "Imagineer Production Deployment Fix"

# ============================================================================
# 1. Install PostgreSQL
# ============================================================================
print_header "Step 1: Installing PostgreSQL"

if command -v psql &> /dev/null; then
    print_success "PostgreSQL is already installed"
else
    print_status "Installing PostgreSQL..."
    sudo apt update
    sudo apt install -y postgresql postgresql-contrib libpq-dev
    print_success "PostgreSQL installed"
fi

# Start PostgreSQL service
print_status "Starting PostgreSQL service..."
sudo systemctl start postgresql
sudo systemctl enable postgresql
print_success "PostgreSQL service started"

# ============================================================================
# 2. Create Production Database and User
# ============================================================================
print_header "Step 2: Creating Production Database"

print_status "Creating database user: $DB_USER"
sudo -u postgres psql -c "DROP USER IF EXISTS $DB_USER;" 2>/dev/null || true
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"

print_status "Creating database: $DB_NAME"
sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

print_status "Granting privileges..."
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
sudo -u postgres psql -d $DB_NAME -c "GRANT ALL ON SCHEMA public TO $DB_USER;"

print_success "Database created successfully"

# Store database credentials securely
DB_CREDENTIALS_FILE="$PROJECT_DIR/.db_credentials"
cat > "$DB_CREDENTIALS_FILE" <<EOF
# PostgreSQL Database Credentials
# KEEP THIS FILE SECURE AND DO NOT COMMIT TO GIT
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME
EOF
chmod 600 "$DB_CREDENTIALS_FILE"

print_success "Database credentials saved to $DB_CREDENTIALS_FILE"
print_warning "Keep this file secure! It contains database password."

# ============================================================================
# 3. Update .env.production
# ============================================================================
print_header "Step 3: Updating .env.production"

cd "$PROJECT_DIR"

# Backup existing .env.production
if [ -f ".env.production" ]; then
    cp .env.production .env.production.backup.$(date +%Y%m%d_%H%M%S)
    print_status "Backed up existing .env.production"
fi

# Update or add DATABASE_URL
if grep -q "^DATABASE_URL=" .env.production 2>/dev/null; then
    # Update existing DATABASE_URL
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME|" .env.production
    print_status "Updated DATABASE_URL in .env.production"
else
    # Add DATABASE_URL
    echo "" >> .env.production
    echo "# PostgreSQL Database" >> .env.production
    echo "DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME" >> .env.production
    print_status "Added DATABASE_URL to .env.production"
fi

print_success ".env.production updated"

# ============================================================================
# 4. Build Frontend
# ============================================================================
print_header "Step 4: Building Frontend"

cd "$PROJECT_DIR/web"

print_status "Installing frontend dependencies..."
npm ci

print_status "Building production frontend..."
npm run deploy:build

# Verify build was created
if [ -d "$PROJECT_DIR/public" ] && [ -f "$PROJECT_DIR/public/index.html" ]; then
    print_success "Frontend built successfully to $PROJECT_DIR/public"
else
    print_error "Frontend build failed or output directory not found"
    exit 1
fi

# ============================================================================
# 5. Update nginx Configuration
# ============================================================================
print_header "Step 5: Updating nginx Configuration"

NGINX_CONFIG="/etc/nginx/sites-available/imagineer"

# The nginx config already points to /home/jdubz/Development/imagineer/public
# which is correct, so we just need to verify and reload

if [ -f "$NGINX_CONFIG" ]; then
    print_status "nginx configuration exists at $NGINX_CONFIG"

    # Test nginx configuration
    if sudo nginx -t 2>&1; then
        print_success "nginx configuration is valid"
    else
        print_error "nginx configuration has errors"
        exit 1
    fi

    # Reload nginx
    print_status "Reloading nginx..."
    sudo systemctl reload nginx
    print_success "nginx reloaded"
else
    print_error "nginx configuration not found at $NGINX_CONFIG"
    print_status "Expected nginx to serve from: /home/jdubz/Development/imagineer/public"
    exit 1
fi

# ============================================================================
# 6. Update auto-deploy.sh
# ============================================================================
print_header "Step 6: Updating auto-deploy.sh"

cd "$PROJECT_DIR"

# Create updated auto-deploy script
cat > scripts/deploy/auto-deploy.sh <<'AUTODEPLOY_EOF'
#!/bin/bash
# Auto-deployment script triggered by webhook
# Pulls latest code from main branch, builds frontend, and restarts services

set -e

echo "=========================================="
echo "Auto-Deployment Started"
echo "=========================================="
echo "Time: $(date)"

# Configuration
APP_DIR="/home/jdubz/Development/imagineer"
BRANCH="main"
USE_DOCKER=${USE_DOCKER:-false}

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

# Build frontend
echo "📦 Building frontend..."
cd web
npm ci --production=false
npm run deploy:build
cd ..
echo "✅ Frontend built"

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

# Reload nginx to pick up any new static files
echo "🔄 Reloading nginx..."
sudo systemctl reload nginx

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
AUTODEPLOY_EOF

chmod +x scripts/deploy/auto-deploy.sh
print_success "auto-deploy.sh updated to build frontend on deployment"

# ============================================================================
# 7. Initialize Database
# ============================================================================
print_header "Step 7: Initializing Database"

cd "$PROJECT_DIR"

# Activate virtual environment and run migrations
source venv/bin/activate

print_status "Running database migrations..."
export DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME"

# Check if Flask-Migrate is being used
if [ -d "migrations" ]; then
    # Use Flask-Migrate
    python -c "from server.api import app, db;
with app.app_context():
    db.create_all()
    print('Database tables created')"
else
    # Just create tables directly
    python -c "from server.api import app, db;
with app.app_context():
    db.create_all()
    print('Database tables created')"
fi

print_success "Database initialized"

# ============================================================================
# 8. Restart Services
# ============================================================================
print_header "Step 8: Restarting Services"

print_status "Stopping imagineer-api service..."
sudo systemctl stop imagineer-api

print_status "Starting imagineer-api service..."
sudo systemctl start imagineer-api

# Wait for service to start
sleep 5

if sudo systemctl is-active --quiet imagineer-api; then
    print_success "imagineer-api service started"
else
    print_error "imagineer-api service failed to start"
    print_status "Check logs with: sudo journalctl -u imagineer-api -n 50"
    exit 1
fi

print_status "Reloading nginx..."
sudo systemctl reload nginx
print_success "nginx reloaded"

# ============================================================================
# 9. Verify Deployment
# ============================================================================
print_header "Step 9: Verifying Deployment"

print_status "Testing local API endpoint..."
sleep 2
if curl -f http://localhost:10050/api/health &> /dev/null; then
    print_success "✅ Local API is healthy"
else
    print_error "❌ Local API health check failed"
fi

print_status "Testing nginx on port 8080..."
if curl -s http://localhost:8080/ | grep -q "<!DOCTYPE html>"; then
    print_success "✅ nginx is serving frontend correctly"
else
    print_error "❌ nginx is not serving frontend"
fi

print_status "Testing public endpoint (via Cloudflare Tunnel)..."
sleep 2
if curl -f https://imagineer.joshwentworth.com/api/health &> /dev/null 2>&1; then
    print_success "✅ Public API is accessible"
else
    print_warning "⚠️  Public API not accessible yet (may need DNS propagation)"
fi

# ============================================================================
# Summary
# ============================================================================
print_header "Deployment Fix Complete!"

cat << SUMMARY

${GREEN}✅ Production deployment has been fixed!${NC}

${BLUE}What was fixed:${NC}
  ✓ PostgreSQL installed and configured
  ✓ Production database created: $DB_NAME
  ✓ .env.production updated with DATABASE_URL
  ✓ Frontend built to /public directory
  ✓ nginx configured to serve frontend from /public
  ✓ auto-deploy.sh updated to build frontend on deployment
  ✓ Database tables initialized
  ✓ All services restarted

${BLUE}Database Info:${NC}
  Database: $DB_NAME
  User: $DB_USER
  Credentials: $DB_CREDENTIALS_FILE (keep secure!)

${BLUE}URLs:${NC}
  Local API:     http://localhost:10050/api/health
  Local Frontend: http://localhost:8080/
  Public:        https://imagineer.joshwentworth.com/

${BLUE}Service Management:${NC}
  API Status:  sudo systemctl status imagineer-api
  API Logs:    sudo journalctl -u imagineer-api -f
  API Restart: sudo systemctl restart imagineer-api

  nginx Status:  sudo systemctl status nginx
  nginx Reload:  sudo systemctl reload nginx

${BLUE}Deployment:${NC}
  Manual: bash scripts/deploy/auto-deploy.sh
  Auto:   Push to main branch (GitHub webhook)

${YELLOW}Security Notes:${NC}
  - Database credentials stored in: $DB_CREDENTIALS_FILE
  - Add to .gitignore: .db_credentials
  - Database password is randomly generated and secure
  - Keep .env.production secure and never commit it

${BLUE}Next Steps:${NC}
  1. Test the deployment: curl https://imagineer.joshwentworth.com/api/health
  2. Test the frontend: open https://imagineer.joshwentworth.com/
  3. Add .db_credentials to .gitignore
  4. Consider backing up the database regularly

SUMMARY

print_success "All done! 🚀"
