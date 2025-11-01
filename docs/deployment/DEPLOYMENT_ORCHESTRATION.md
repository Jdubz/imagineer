# Deployment Orchestration Guide

Quick reference for using the comprehensive deployment orchestration script.

## Overview

The `deploy-all.sh` script provides a single entry point for deploying the entire Imagineer application stack. It orchestrates all deployment components with prerequisite checks, health validation, and smart error handling.

## Quick Start

### Full Deployment

Deploy everything in the correct order:

```bash
# Using the script directly
bash scripts/deploy/deploy-all.sh

# Or using Make
make deploy-all
```

This will:
1. Check all prerequisites (Python, Docker, Terraform, Firebase CLI, etc.)
2. Validate configuration files (.env, terraform.tfvars, etc.)
3. Deploy backend production server
4. Setup Cloudflare Tunnel
5. Deploy Cloudflare infrastructure (DNS, WAF, rate limiting)
6. Build and deploy frontend to Firebase
7. Run health checks
8. Display deployment summary

### Dry Run (Preview Only)

See what would be deployed without making any changes:

```bash
# Preview deployment
bash scripts/deploy/deploy-all.sh --dry-run

# Or using Make
make deploy-all-dry-run
```

## Selective Deployment

### Deploy Specific Components

**Backend Only:**
```bash
bash scripts/deploy/deploy-all.sh --backend-only
```

**Cloudflare Tunnel Only:**
```bash
bash scripts/deploy/deploy-all.sh --tunnel-only
```

**Infrastructure Only (Terraform):**
```bash
bash scripts/deploy/deploy-all.sh --infra-only
```

**Frontend Only:**
```bash
bash scripts/deploy/deploy-all.sh --frontend-only

# Or using Make (skips checks for speed)
make deploy-frontend-only
```

**Backend + Tunnel (no infrastructure or frontend):**
```bash
bash scripts/deploy/deploy-all.sh --backend-only --tunnel-only

# Or using Make
make deploy-backend-stack
```

### Skip Specific Components

Deploy everything **except** certain components:

```bash
# Deploy everything except frontend
bash scripts/deploy/deploy-all.sh --no-frontend

# Deploy everything except infrastructure
bash scripts/deploy/deploy-all.sh --no-infra

# Deploy everything except tunnel
bash scripts/deploy/deploy-all.sh --no-tunnel
```

## Advanced Options

### Skip Prerequisite Checks

For faster redeployment when you know everything is installed:

```bash
bash scripts/deploy/deploy-all.sh --skip-checks
```

**Warning:** Only use this if you're certain all prerequisites are met.

### Combining Options

You can combine multiple options:

```bash
# Frontend only, skip checks (fastest frontend redeploy)
bash scripts/deploy/deploy-all.sh --frontend-only --skip-checks

# Dry run of backend only
bash scripts/deploy/deploy-all.sh --backend-only --dry-run

# Everything except frontend, skip checks
bash scripts/deploy/deploy-all.sh --no-frontend --skip-checks
```

## Prerequisites

The script automatically checks for these before deployment:

**Required:**
- Python 3.8+ (3.12 recommended)
- Node.js 18+
- npm
- git
- Firebase CLI (`npm install -g firebase-tools`)
- Terraform (if deploying infrastructure)

**Optional (for production server):**
- Docker + Docker Compose (recommended)
- systemd (alternative to Docker)

**Optional (for Cloudflare Tunnel):**
- cloudflared (will be installed during tunnel setup if missing)

### Installing Prerequisites

**Python & Node:**
```bash
# Most systems
sudo apt install python3 python3-venv nodejs npm

# Or use nvm for Node
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 20
```

**Firebase CLI:**
```bash
npm install -g firebase-tools
firebase login
```

**Terraform:**
```bash
# Linux
wget https://releases.hashicorp.com/terraform/1.7.0/terraform_1.7.0_linux_amd64.zip
unzip terraform_1.7.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/
```

**Docker:**
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose plugin
sudo apt install docker-compose-plugin
```

## Configuration Files

Before running deployment, ensure these files are configured:

### 1. Backend Environment (`.env.production`)

Copy from example and configure:
```bash
cp .env.production.example .env.production
nano .env.production
```

Required settings:
- `FLASK_ENV=production`
- `WEBHOOK_SECRET` (for auto-deployment)
- `ALLOWED_ORIGINS` (Firebase URLs)

### 2. Frontend Environment (`web/.env.production`)

Copy from example and configure:
```bash
cp web/.env.production.example web/.env.production
nano web/.env.production
```

Required settings:
- `VITE_API_BASE_URL=https://api.imagineer.joshwentworth.com/api`
- `VITE_APP_PASSWORD` (should be in GitHub Secrets, not committed)

### 3. Terraform Variables (`terraform/terraform.tfvars`)

Copy from example and configure:
```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
nano terraform/terraform.tfvars
```

Required settings:
- `cloudflare_api_token` - Get from https://dash.cloudflare.com/profile/api-tokens
- `tunnel_id` - Obtained during tunnel setup
- `domain` - Your domain (e.g., "joshwentworth.com")
- `api_subdomain` - Subdomain for API (e.g., "imagineer")

### 4. Firebase Configuration (`.firebaserc`)

Should already be configured for project `static-sites-257923`:
```json
{
  "projects": {
    "default": "static-sites-257923"
  },
  "targets": {
    "static-sites-257923": {
      "hosting": {
        "imagineer": ["imagineer-generator"]
      }
    }
  }
}
```

## Deployment Flow

The orchestration script follows this order:

1. **Prerequisite Check** ✓
   - Verifies all required tools are installed
   - Checks versions
   - Warns about optional tools

2. **Configuration Check** ✓
   - Validates .env files exist
   - Checks terraform.tfvars is configured
   - Verifies Firebase project setup

3. **Backend Deployment** 🚀
   - Runs `setup-production.sh` (Docker or systemd)
   - Starts production server
   - Validates health endpoint

4. **Cloudflare Tunnel Setup** 🌐
   - Installs cloudflared (if needed)
   - Creates tunnel "imagineer-api"
   - Configures systemd service
   - Extracts tunnel ID
   - Updates terraform.tfvars with tunnel ID

5. **Infrastructure Deployment** ⚙️
   - Initializes Terraform
   - Validates configuration
   - Shows plan
   - Asks for confirmation
   - Applies changes (DNS, WAF, rate limiting)

6. **Frontend Deployment** 📦
   - Installs npm dependencies
   - Builds React app with Vite
   - Deploys to Firebase Hosting
   - Targets: imagineer-generator

7. **Health Checks** 🏥
   - Local backend: `http://localhost:10050/api/health`
   - Tunnel service: systemd status
   - Public API: `https://api.imagineer.joshwentworth.com/api/health`
   - Frontend: `https://imagineer-generator.web.app`

8. **Summary** 📊
   - Shows all URLs
   - Lists management commands
   - Points to troubleshooting docs

## Output and Logs

All deployment activity is logged to:
```
logs/deployment-YYYYMMDD-HHMMSS.log
```

The script uses color-coded output:
- 🔵 **Blue** - Info/status messages
- 🟢 **Green** - Success messages
- 🟡 **Yellow** - Warnings (non-fatal)
- 🔴 **Red** - Errors (fatal)

## Common Scenarios

### First-Time Deployment

```bash
# 1. Check prerequisites
bash scripts/deploy/deploy-all.sh --dry-run

# 2. Configure all files
# Edit .env.production, web/.env.production, terraform/terraform.tfvars

# 3. Deploy everything
bash scripts/deploy/deploy-all.sh
```

### Frontend Update

After making changes to the React app:

```bash
# Fast redeploy (skips checks and other components)
make deploy-frontend-only

# Or with full checks
bash scripts/deploy/deploy-all.sh --frontend-only
```

### Backend Update

After making changes to Flask API:

```bash
# Just redeploy backend
bash scripts/deploy/deploy-all.sh --backend-only

# Or use prod-deploy for running system
make prod-deploy
```

### Infrastructure Changes

After modifying Terraform configuration:

```bash
# Just redeploy infrastructure
bash scripts/deploy/deploy-all.sh --infra-only

# Or using Makefile
make deploy-infra
```

### Complete Redeployment

To redeploy everything from scratch:

```bash
# Preview what will happen
bash scripts/deploy/deploy-all.sh --dry-run

# Deploy everything
bash scripts/deploy/deploy-all.sh

# Or skip checks if you know prerequisites are met
bash scripts/deploy/deploy-all.sh --skip-checks
```

## Troubleshooting

### Prerequisite Check Fails

If missing tools:
```bash
# Install missing tools (see Prerequisites section)
# Then retry with skip-checks if partially complete
bash scripts/deploy/deploy-all.sh --skip-checks
```

### Configuration Check Fails

If configuration files are missing:
```bash
# Copy from examples
cp .env.production.example .env.production
cp web/.env.production.example web/.env.production
cp terraform/terraform.tfvars.example terraform/terraform.tfvars

# Edit and configure
nano .env.production
nano web/.env.production
nano terraform/terraform.tfvars
```

### Backend Deployment Fails

Check if port 10050 is already in use:
```bash
# Check what's using the port
sudo lsof -i :10050

# Kill if needed
sudo kill -9 $(sudo lsof -t -i :10050)

# Retry deployment
bash scripts/deploy/deploy-all.sh --backend-only
```

### Tunnel Setup Fails

Authentication issues:
```bash
# Manually authenticate
cloudflared tunnel login

# Retry tunnel setup
bash scripts/deploy/deploy-all.sh --tunnel-only
```

### Infrastructure Deployment Fails

Terraform errors:
```bash
# Check Terraform state
cd terraform
terraform show

# Validate configuration
terraform validate

# Manual plan to see detailed errors
terraform plan

# Fix issues and retry
cd ..
bash scripts/deploy/deploy-all.sh --infra-only
```

### Frontend Deployment Fails

Firebase authentication:
```bash
# Re-authenticate
firebase login

# Check project
firebase projects:list

# Check .firebaserc
cat .firebaserc

# Retry deployment
bash scripts/deploy/deploy-all.sh --frontend-only
```

### Health Checks Fail

If health checks report failures after successful deployment:

**Local backend fails:**
```bash
# Check if running
make prod-status

# Check logs
make prod-logs

# Restart if needed
make prod-restart
```

**Public API fails:**
```bash
# DNS may still be propagating (wait 1-2 minutes)
watch -n 10 curl -s https://api.imagineer.joshwentworth.com/api/health

# Check tunnel status
sudo systemctl status cloudflared-imagineer-api

# Check Cloudflare DNS
dig imagineer.joshwentworth.com
```

## Manual Rollback

If deployment causes issues:

### Backend Rollback

```bash
# Docker deployment
cd /home/jdubz/Development/imagineer
git log -n 5  # Find previous good commit
git checkout <commit-hash>
docker-compose restart

# systemd deployment
git checkout <commit-hash>
sudo systemctl restart imagineer-api
```

### Frontend Rollback

```bash
# Firebase keeps previous versions
firebase hosting:channel:list

# Rollback in Firebase Console
# https://console.firebase.google.com/project/static-sites-257923/hosting
```

### Infrastructure Rollback

```bash
# Revert Terraform changes
cd terraform
git log terraform/  # Find previous state
git checkout <commit-hash> -- .
terraform plan  # Verify revert
terraform apply
```

## Post-Deployment Verification

After deployment, verify everything works:

```bash
# 1. Check local backend
curl http://localhost:10050/api/health

# 2. Check tunnel service
sudo systemctl status cloudflared-imagineer-api

# 3. Check public API (may need DNS propagation time)
curl https://api.imagineer.joshwentworth.com/api/health

# 4. Check frontend
curl -I https://imagineer-generator.web.app

# 5. Test end-to-end
# Visit https://imagineer-generator.web.app in browser
# Enter password: [REDACTED]
# Try generating an image
```

## Related Documentation

- **Complete Deployment Guide**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Cloudflare Tunnel Setup**: [CLOUDFLARE_TUNNEL_SETUP.md](../CLOUDFLARE_TUNNEL_SETUP.md)
- **Production Server**: [PRODUCTION_README.md](../PRODUCTION_README.md)
- **Firebase Setup**: [FIREBASE_QUICKSTART.md](../FIREBASE_QUICKSTART.md)
- **CLI Reference**: [CLI_QUICK_REFERENCE.md](CLI_QUICK_REFERENCE.md)

## Quick Command Reference

```bash
# Full deployment
make deploy-all                    # Complete orchestrated deployment
make deploy-all-dry-run           # Preview without changes

# Selective deployment
make deploy-backend-stack         # Backend + tunnel only
make deploy-frontend-only         # Frontend only (fast)
bash scripts/deploy/deploy-all.sh --backend-only
bash scripts/deploy/deploy-all.sh --tunnel-only
bash scripts/deploy/deploy-all.sh --infra-only

# Production management
make prod-status                  # Check status
make prod-logs                    # View logs
make prod-restart                 # Restart services
make prod-deploy                  # Manual redeploy

# Individual components
make deploy-backend               # Backend setup
make deploy-tunnel                # Tunnel setup
make deploy-infra                 # Terraform apply
make deploy-frontend-prod         # Firebase deploy

# Status and diagnostics
make deploy-status                # Deployment status
make deploy-restart               # Restart all services
```

## URLs After Deployment

**Frontend:**
- Production: https://imagineer-generator.web.app
- Alternative: https://imagineer-generator.firebaseapp.com

**API:**
- Public: https://api.imagineer.joshwentworth.com/api
- Health: https://api.imagineer.joshwentworth.com/api/health
- Local: http://localhost:10050/api

**Dashboards:**
- Cloudflare: https://dash.cloudflare.com
- Firebase: https://console.firebase.google.com/project/static-sites-257923
