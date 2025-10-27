#!/bin/bash
# Enhanced deployment script with versioning and cache busting
# Usage: ./scripts/deploy/deploy-with-versioning.sh [environment] [version-bump]

set -e

ENVIRONMENT=${1:-dev}
VERSION_BUMP=${2:-patch}

echo "🚀 Deploying Imagineer with versioning ($ENVIRONMENT, $VERSION_BUMP bump)..."

# Configuration
PROJECT_DIR="/home/jdubz/Development/imagineer"
WEB_DIR="${PROJECT_DIR}/web"

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

# Get current version
CURRENT_VERSION=$(python scripts/version.py current)
print_info "Current version: $CURRENT_VERSION"

# Bump version if requested
if [ "$VERSION_BUMP" != "none" ]; then
    print_info "Bumping version ($VERSION_BUMP)..."
    NEW_VERSION=$(python scripts/version.py bump --part $VERSION_BUMP)
    print_status "Version bumped to: $NEW_VERSION"
else
    NEW_VERSION=$CURRENT_VERSION
    print_info "Keeping current version: $NEW_VERSION"
fi

# Check if Firebase CLI is installed
if ! command -v firebase &> /dev/null; then
    print_warning "Firebase CLI not found. Installing..."
    npm install -g firebase-tools
    print_status "Firebase CLI installed"
fi

# Check if logged in to Firebase
if ! firebase projects:list &> /dev/null; then
    print_warning "Not logged in to Firebase. Running authentication..."
    firebase login
    print_status "Authentication complete"
fi

# Navigate to web directory
cd "$WEB_DIR"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    print_info "Installing dependencies..."
    npm install
fi

# Set environment variables based on target
case $ENVIRONMENT in
    dev)
        print_info "Building for development..."
        export VITE_API_BASE_URL="${VITE_API_BASE_URL_DEV:-http://localhost:10050/api}"
        FIREBASE_TARGET="dev"
        ;;
    staging)
        print_info "Building for staging..."
        export VITE_API_BASE_URL="${VITE_API_BASE_URL_STAGING:-https://api-staging.your-domain.com/api}"
        FIREBASE_TARGET="staging"
        ;;
    prod)
        print_info "Building for production..."
        export VITE_API_BASE_URL="${VITE_API_BASE_URL_PROD:-https://api.your-domain.com/api}"
        FIREBASE_TARGET="prod"
        ;;
    *)
        print_error "Invalid environment: $ENVIRONMENT"
        echo "   Valid options: dev, staging, prod"
        exit 1
        ;;
esac

# Build frontend with versioning
print_info "Building frontend with version $NEW_VERSION..."
npm run build:prod

# Verify build output
if [ ! -f "../public/index.html" ]; then
    print_error "Build failed - index.html not found"
    exit 1
fi

# Check for versioned assets
ASSET_COUNT=$(find ../public/assets -name "*.js" -o -name "*.css" | wc -l)
print_status "Generated $ASSET_COUNT versioned assets"

# Show build info
print_info "Build information:"
python ../scripts/version.py build-info

# Deploy to Firebase
print_info "Deploying to Firebase..."
firebase deploy --only hosting:imagineer

# Create git tag if this is a production deployment
if [ "$ENVIRONMENT" = "prod" ] && [ "$VERSION_BUMP" != "none" ]; then
    print_info "Creating git tag for production release..."
    cd "$PROJECT_DIR"
    python scripts/version.py tag --message "Production release v$NEW_VERSION"
    print_status "Git tag v$NEW_VERSION created"
fi

print_status "Deployment complete! 🎉"
echo ""
echo "📊 Deployment Summary:"
echo "  Environment: $ENVIRONMENT"
echo "  Version: $NEW_VERSION"
echo "  Assets: $ASSET_COUNT versioned files"
echo ""
echo "🌐 Your app is live at:"
echo "  https://imagineer-generator.web.app"
echo "  https://imagineer-generator.firebaseapp.com"
echo ""
echo "🔧 Useful commands:"
echo "  View logs:    firebase hosting:channel:list"
echo "  Rollback:     firebase hosting:rollback"
echo "  Open console: firebase open hosting"
echo "  Check version: python scripts/version.py current"