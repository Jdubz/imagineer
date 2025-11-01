#!/bin/bash
# Deploy frontend to Firebase Hosting
# Usage: ./scripts/deploy/deploy-frontend.sh [environment]
# Environment: dev, staging, prod (default: dev)

set -e

ENVIRONMENT=${1:-dev}

echo "🚀 Deploying frontend to Firebase ($ENVIRONMENT)..."

# Configuration
PROJECT_DIR="/home/jdubz/Development/imagineer"
WEB_DIR="${PROJECT_DIR}/web"

# Check if Firebase CLI is installed
if ! command -v firebase &> /dev/null; then
  echo "❌ Firebase CLI not found. Installing..."
  npm install -g firebase-tools
  echo "✅ Firebase CLI installed"
fi

# Check if logged in to Firebase
if ! firebase projects:list &> /dev/null; then
  echo "🔐 Not logged in to Firebase. Running authentication..."
  firebase login
  echo "✅ Authentication complete"
fi

# Navigate to web directory
cd "$WEB_DIR"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
  echo "📦 Installing dependencies..."
  npm install
fi

# Set environment variables based on target
case $ENVIRONMENT in
  dev)
    echo "🔧 Building for development..."
    export VITE_API_BASE_URL="${VITE_API_BASE_URL_DEV:-http://localhost:10050/api}"
    FIREBASE_TARGET="dev"
    ;;
  staging)
    echo "🔧 Building for staging..."
    export VITE_API_BASE_URL="${VITE_API_BASE_URL_STAGING:-https://api-staging.your-domain.com/api}"
    FIREBASE_TARGET="staging"
    ;;
  prod)
    echo "🔧 Building for production..."
    export VITE_API_BASE_URL="${VITE_API_BASE_URL_PROD:-https://api.imagineer.joshwentworth.com/api}"
    FIREBASE_TARGET="prod"
    ;;
  *)
    echo "❌ Invalid environment: $ENVIRONMENT"
    echo "   Valid options: dev, staging, prod"
    exit 1
    ;;
esac

# Build frontend with versioning
echo "🏗️  Building frontend..."
npm run deploy:build

# Deploy to Firebase
echo "🚀 Deploying to Firebase..."
# Deploy to imagineer-generator site (specified in firebase.json)
firebase deploy --only hosting --project static-sites-257923

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Your app is live at:"
echo "  https://imagineer-generator.web.app"
echo "  https://imagineer-generator.firebaseapp.com"
echo ""
echo "Firebase Console:"
echo "  https://console.firebase.google.com/project/static-sites-257923/hosting"

echo ""
echo "Useful commands:"
echo "  View logs:    firebase hosting:channel:list"
echo "  Rollback:     firebase hosting:rollback"
echo "  Open console: firebase open hosting"
