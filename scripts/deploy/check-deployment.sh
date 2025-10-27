#!/bin/bash
# Check deployment status for both frontend and backend
# Usage: ./scripts/deploy/check-deployment.sh

set -e

echo "🔍 Checking Imagineer deployment status..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if we're in the right directory
if [ ! -f "VERSION" ] || [ ! -f "web/package.json" ]; then
    print_error "Not in project root directory. Please run from the project root."
    exit 1
fi

echo ""
print_info "=== VERSION INFORMATION ==="
VERSION=$(python scripts/version.py current)
BUILD_INFO=$(python scripts/version.py build-info)
echo "Current Version: $VERSION"
echo "$BUILD_INFO"

echo ""
print_info "=== FRONTEND STATUS ==="

# Check if public directory exists and has content
if [ -d "public" ] && [ -f "public/index.html" ]; then
    print_status "Public directory exists with index.html"
    
    # Check for versioned assets
    ASSET_COUNT=$(find public/assets \( -name "*.js" -o -name "*.css" \) 2>/dev/null | wc -l)
    if [ $ASSET_COUNT -gt 0 ]; then
        print_status "Found $ASSET_COUNT versioned assets"
        
        # Check if assets have version numbers
        VERSIONED_ASSETS=$(find public/assets -name "*$VERSION*" 2>/dev/null | wc -l)
        if [ $VERSIONED_ASSETS -gt 0 ]; then
            print_status "Assets are properly versioned ($VERSIONED_ASSETS files)"
        else
            print_warning "Assets may not be properly versioned"
        fi
    else
        print_warning "No assets found in public/assets/"
    fi
else
    print_error "Public directory missing or empty. Run: cd web && npm run build"
fi

# Check if Firebase CLI is available
if command -v firebase &> /dev/null; then
    print_status "Firebase CLI is installed"
    
    # Check if logged in
    if firebase projects:list &> /dev/null; then
        print_status "Firebase authentication is working"
    else
        print_warning "Not logged in to Firebase. Run: firebase login"
    fi
else
    print_warning "Firebase CLI not installed. Run: npm install -g firebase-tools"
fi

echo ""
print_info "=== BACKEND STATUS ==="

# Check if virtual environment exists
if [ -d "venv" ]; then
    print_status "Virtual environment exists"
    
    # Check if gunicorn is installed
    if venv/bin/python -c "import gunicorn" 2>/dev/null; then
        print_status "Gunicorn is installed"
    else
        print_warning "Gunicorn not installed. Run: pip install gunicorn"
    fi
else
    print_error "Virtual environment not found. Run: python3 -m venv venv"
fi

# Check if .env file exists
if [ -f ".env" ]; then
    print_status ".env file exists"
else
    print_warning ".env file missing. Create from .env.example"
fi

# Check if systemd service exists
if systemctl list-unit-files | grep -q "imagineer-api"; then
    print_status "Systemd service exists"
    
    # Check service status
    if systemctl is-active --quiet imagineer-api; then
        print_status "Backend service is running"
        
        # Test health endpoint
        if curl -s http://localhost:10050/api/health > /dev/null; then
            print_status "Backend API is responding"
        else
            print_warning "Backend API not responding on localhost:10050"
        fi
    else
        print_warning "Backend service is not running. Run: sudo systemctl start imagineer-api"
    fi
else
    print_warning "Systemd service not found. Run: ./scripts/deploy/setup-backend.sh"
fi

# Check database
if [ -f "instance/imagineer.db" ]; then
    print_status "Database file exists"
else
    print_warning "Database file not found. May need to initialize database"
fi

echo ""
print_info "=== DEPLOYMENT RECOMMENDATIONS ==="

# Check for common issues
ISSUES=0

if [ ! -d "public" ] || [ ! -f "public/index.html" ]; then
    echo "  • Build frontend: cd web && npm run build:prod"
    ISSUES=$((ISSUES + 1))
fi

if ! command -v firebase &> /dev/null; then
    echo "  • Install Firebase CLI: npm install -g firebase-tools"
    ISSUES=$((ISSUES + 1))
fi

if [ ! -d "venv" ]; then
    echo "  • Create virtual environment: python3 -m venv venv"
    ISSUES=$((ISSUES + 1))
fi

if ! systemctl list-unit-files | grep -q "imagineer-api"; then
    echo "  • Setup backend service: ./scripts/deploy/setup-backend.sh"
    ISSUES=$((ISSUES + 1))
fi

if [ $ISSUES -eq 0 ]; then
    print_status "No major issues found! Deployment should be working."
    echo ""
    print_info "Quick deployment commands:"
    echo "  Frontend: ./scripts/deploy/deploy-with-versioning.sh prod patch"
    echo "  Backend:  ./scripts/deploy/setup-backend.sh"
    echo "  Status:   ./scripts/deploy/check-deployment.sh"
else
    print_warning "Found $ISSUES potential issues. Address them before deploying."
fi

echo ""