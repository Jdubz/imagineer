#!/bin/bash
# Reorganize Imagineer project structure
# Moves documentation to proper locations and removes duplicates

set -e

PROJECT_ROOT="/home/jdubz/Development/imagineer"
cd "$PROJECT_ROOT"

echo "🧹 Reorganizing Imagineer Project Structure"
echo "============================================="
echo ""

# Create docs subdirectories
echo "📁 Creating documentation structure..."
mkdir -p docs/deployment
mkdir -p docs/lora
mkdir -p docs/guides

# Move deployment documentation from root to docs/deployment/
echo "📦 Moving deployment documentation..."
mv CLOUDFLARE_TUNNEL_SETUP.md docs/deployment/ 2>/dev/null || true
mv CREDENTIALS_QUICK_REFERENCE.md docs/deployment/ 2>/dev/null || true
mv DEPLOYMENT_CHEATSHEET.md docs/deployment/ 2>/dev/null || true
mv DEPLOYMENT_ORCHESTRATION_COMPLETE.md docs/deployment/ 2>/dev/null || true
mv DEPLOYMENT_README.md docs/deployment/ 2>/dev/null || true
mv FIREBASE_QUICKSTART.md docs/deployment/ 2>/dev/null || true
mv PRODUCTION_README.md docs/deployment/ 2>/dev/null || true

# Move existing deployment docs from docs/ to docs/deployment/
mv docs/DEPLOYMENT_GUIDE.md docs/deployment/ 2>/dev/null || true
mv docs/DEPLOYMENT_ORCHESTRATION.md docs/deployment/ 2>/dev/null || true
mv docs/DEPLOYMENT_ORCHESTRATION_SUMMARY.md docs/deployment/ 2>/dev/null || true
mv docs/FIREBASE_CLOUDFLARE_DEPLOYMENT.md docs/deployment/ 2>/dev/null || true
mv docs/FIREBASE_SETUP.md docs/deployment/ 2>/dev/null || true
mv docs/PRODUCTION_SETUP.md docs/deployment/ 2>/dev/null || true
mv docs/REQUIRED_CREDENTIALS.md docs/deployment/ 2>/dev/null || true
mv docs/SECURE_AUTHENTICATION_PLAN.md docs/deployment/ 2>/dev/null || true
mv docs/CLI_QUICK_REFERENCE.md docs/deployment/ 2>/dev/null || true

# Move LoRA documentation from root to docs/lora/
echo "📦 Moving LoRA documentation..."
mv LORA_SETUP.md docs/lora/ 2>/dev/null || true
mv docs/LORA_ORGANIZATION.md docs/lora/ 2>/dev/null || true
mv docs/LORA_PREVIEW_GENERATION.md docs/lora/ 2>/dev/null || true

# Move general guides to docs/guides/
echo "📦 Organizing general guides..."
mv docs/SETUP.md docs/guides/ 2>/dev/null || true
mv docs/TESTING.md docs/guides/ 2>/dev/null || true
mv docs/LINTING.md docs/guides/ 2>/dev/null || true
mv docs/CONTRIBUTING.md docs/guides/ 2>/dev/null || true
mv docs/MAKEFILE_REFERENCE.md docs/guides/ 2>/dev/null || true
mv docs/NEXT_STEPS.md docs/guides/ 2>/dev/null || true

# Keep core architecture and API docs in root docs/
echo "📦 Core documentation remains in docs/..."
# docs/ARCHITECTURE.md - stays
# docs/API.md - stays

# Remove redundant scripts (replaced by Makefile targets)
echo "🗑️  Removing redundant scripts..."
rm -f scripts/start_api.sh
rm -f scripts/start_server.sh
rm -f scripts/start_dev.sh
rm -f scripts/generate.sh

# Remove duplicate tunnel setup script (keep custom one)
rm -f scripts/deploy/setup-cloudflare-tunnel.sh

echo ""
echo "✅ Reorganization complete!"
echo ""
echo "New structure:"
echo "  docs/"
echo "    ├── ARCHITECTURE.md           (core architecture)"
echo "    ├── API.md                    (API reference)"
echo "    ├── deployment/               (all deployment docs)"
echo "    ├── lora/                     (LoRA management docs)"
echo "    └── guides/                   (setup, testing, contributing)"
echo ""
echo "Removed redundant scripts:"
echo "  - scripts/start_api.sh          (use: make api)"
echo "  - scripts/start_server.sh       (use: make api)"
echo "  - scripts/start_dev.sh          (use: make dev)"
echo "  - scripts/generate.sh           (use: make generate)"
echo "  - scripts/deploy/setup-cloudflare-tunnel.sh (use: custom version)"
echo ""
echo "Root directory now contains only:"
echo "  - README.md, CLAUDE.md, LICENSE"
echo "  - Configuration files (.env, config.yaml, etc.)"
echo "  - Build files (Dockerfile, docker-compose.yml, etc.)"
echo "  - Makefile, test_all_loras.sh"
echo ""
