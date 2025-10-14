# Deployment Guide - Infrastructure as Code

**Last Updated:** 2025-10-14

This guide covers deploying Imagineer using an Infrastructure as Code (IaC) approach with maximum CLI control.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
  - [1. Backend API Setup](#1-backend-api-setup)
  - [2. Cloudflare Tunnel Setup](#2-cloudflare-tunnel-setup)
  - [3. Cloudflare Infrastructure (Terraform)](#3-cloudflare-infrastructure-terraform)
  - [4. Firebase Hosting Setup](#4-firebase-hosting-setup)
  - [5. GitHub Actions CI/CD](#5-github-actions-cicd)
- [Deployment Workflows](#deployment-workflows)
- [Troubleshooting](#troubleshooting)
- [Rollback Procedures](#rollback-procedures)

---

## Overview

**Architecture:**
```
┌──────────────────┐
│   GitHub Repo    │
│   (Your Code)    │
└────────┬─────────┘
         │
         │ Push to main/develop
         │
         ▼
┌──────────────────────────────────────────────┐
│          GitHub Actions CI/CD                 │
│  ┌──────────────┐  ┌────────────────────┐   │
│  │   Frontend   │  │   Infrastructure   │   │
│  │   Build &    │  │   Terraform        │   │
│  │   Deploy     │  │   Apply            │   │
│  └──────┬───────┘  └────────┬───────────┘   │
└─────────┼────────────────────┼───────────────┘
          │                    │
          ▼                    ▼
┌─────────────────┐  ┌──────────────────────┐
│  Firebase       │  │   Cloudflare Edge    │
│  Hosting        │  │   (DNS, WAF, Rate    │
│  (Global CDN)   │  │    Limiting)         │
└─────────────────┘  └──────────┬───────────┘
                                │
                                │ Encrypted Tunnel
                                ▼
                     ┌─────────────────────────┐
                     │  Your Server            │
                     │  (localhost:10050)      │
                     │                         │
                     │  • Flask API (systemd)  │
                     │  • Cloudflare Tunnel    │
                     │  • GPU Processing       │
                     └─────────────────────────┘
```

**Components:**
- **Frontend:** React SPA → Firebase Hosting (CDN)
- **API:** Flask → Cloudflare Tunnel → Your Server
- **Infrastructure:** Terraform → Cloudflare (DNS, Firewall, WAF)
- **CI/CD:** GitHub Actions → Automated Deployments

---

## Prerequisites

### Required Software

```bash
# Check if installed
terraform --version   # Need >= 1.0
firebase --version    # Need firebase-tools
cloudflared --version # Need cloudflared
node --version        # Need >= 18
python3 --version     # Need >= 3.8
```

### Installation Commands

```bash
# Terraform
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform

# Firebase CLI
npm install -g firebase-tools

# Cloudflare Tunnel (cloudflared)
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

### Required Accounts & Credentials

1. **Cloudflare Account**
   - Domain added to Cloudflare
   - API Token with permissions:
     - Zone.DNS (Edit)
     - Zone.Firewall Services (Edit)
   - Create at: https://dash.cloudflare.com/profile/api-tokens

2. **Firebase Project**
   - Create at: https://console.firebase.google.com
   - Enable Hosting
   - Download service account JSON

3. **GitHub Repository**
   - Repository with code
   - Access to Settings → Secrets

---

## Quick Start

For experienced users who want to deploy everything at once:

```bash
# 1. Clone and setup
git clone https://github.com/yourusername/imagineer.git
cd imagineer
make install
make install-web

# 2. Configure environment
cp web/.env.example web/.env.development
cp web/.env.example web/.env.production
# Edit both files with your configuration

# 3. Deploy backend
make deploy-backend

# 4. Deploy Cloudflare Tunnel
make deploy-tunnel

# 5. Configure Terraform
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Edit with your values

# 6. Deploy infrastructure
make deploy-infra

# 7. Configure Firebase
cp .firebaserc.example .firebaserc
# Edit with your Firebase project ID
firebase login

# 8. Deploy frontend
make deploy-frontend-prod

# 9. Check status
make deploy-status
```

---

## Detailed Setup

### 1. Backend API Setup

The backend runs as a systemd service with gunicorn.

#### Configuration

Create `.env` file in project root:

```bash
# Environment
FLASK_ENV=production
FLASK_DEBUG=False

# API Configuration
FLASK_RUN_PORT=10050

# Security
ALLOWED_ORIGINS=https://your-app.web.app,https://your-app.firebaseapp.com
CLOUDFLARE_VERIFY=true

# Rate Limiting
RATELIMIT_ENABLED=true

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/imagineer/api.log
```

#### Deploy

```bash
# Automated deployment
make deploy-backend
```

**What this does:**
1. Checks for virtual environment
2. Creates log directory
3. Generates systemd service file
4. Installs and enables service
5. Starts the API server

#### Manual Verification

```bash
# Check service status
sudo systemctl status imagineer-api

# View logs
sudo journalctl -u imagineer-api -f

# Test endpoint
curl http://localhost:10050/api/health
```

#### Service Management

```bash
# Start/Stop/Restart
sudo systemctl start imagineer-api
sudo systemctl stop imagineer-api
sudo systemctl restart imagineer-api

# View logs
sudo journalctl -u imagineer-api -n 100
sudo tail -f /var/log/imagineer/api.log
```

---

### 2. Cloudflare Tunnel Setup

Cloudflare Tunnel creates a secure connection from your server to Cloudflare's edge without opening firewall ports.

#### Authenticate

```bash
cloudflared tunnel login
```

This opens a browser to authenticate with Cloudflare.

#### Deploy

```bash
# Automated deployment
make deploy-tunnel
```

**What this does:**
1. Installs cloudflared (if needed)
2. Creates tunnel (if doesn't exist)
3. Generates configuration file
4. Creates systemd service
5. Starts the tunnel

#### Configuration

The tunnel config is created at `terraform/cloudflare-tunnel.yml`:

```yaml
tunnel: imagineer-api
credentials-file: /home/user/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: api.your-domain.com
    service: http://127.0.0.1:10050
    originRequest:
      noTLSVerify: true
      connectTimeout: 30s
  - service: http_status:404
```

#### Get Tunnel ID

```bash
# List tunnels
cloudflared tunnel list

# Or extract from deployment script output
# The tunnel ID will be shown after creation
```

#### Service Management

```bash
# Start/Stop/Restart
sudo systemctl start cloudflared-imagineer-api
sudo systemctl stop cloudflared-imagineer-api
sudo systemctl restart cloudflared-imagineer-api

# View logs
sudo journalctl -u cloudflared-imagineer-api -f
```

---

### 3. Cloudflare Infrastructure (Terraform)

Terraform manages DNS records, firewall rules, rate limiting, and WAF configuration.

#### Configuration

Create `terraform/terraform.tfvars`:

```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
```

Edit with your values:

```hcl
# Cloudflare API Token
cloudflare_api_token = "your-api-token"

# Domain
domain = "your-domain.com"

# Tunnel ID (from step 2)
tunnel_id = "your-tunnel-id"

# Optional features
enable_geo_blocking = false
enable_cloudflare_access = false
```

#### Deploy

```bash
# Initialize Terraform
cd terraform
terraform init

# Preview changes
terraform plan

# Apply (via Makefile)
cd ..
make deploy-infra
```

#### What Gets Created

- **DNS Record:** `api.your-domain.com` → Tunnel
- **Rate Limits:**
  - 10 requests/minute for `/api/generate*`
  - 5 requests/minute for `/api/auth/login`
- **WAF Rules:**
  - Challenge bots with score < 30
  - Optional geo-blocking
- **Page Rules:**
  - SSL enforcement
  - Security headers

#### Verify Deployment

```bash
# Check Terraform state
cd terraform
terraform show

# Check outputs
terraform output

# Test DNS
dig api.your-domain.com
```

---

### 4. Firebase Hosting Setup

Firebase Hosting serves the React frontend globally via CDN.

#### Initialize Firebase

```bash
# Login
firebase login

# List projects
firebase projects:list
```

#### Configuration

Create `.firebaserc`:

```bash
cp .firebaserc.example .firebaserc
```

Edit with your Firebase project ID:

```json
{
  "projects": {
    "default": "your-firebase-project-id"
  },
  "targets": {
    "your-firebase-project-id": {
      "hosting": {
        "prod": ["your-project-prod"]
      }
    }
  }
}
```

#### Deploy

```bash
# Development
make deploy-frontend-dev

# Production
make deploy-frontend-prod
```

**What this does:**
1. Installs npm dependencies
2. Builds frontend with environment-specific API URL
3. Deploys to Firebase Hosting

#### Environment Variables

Set in `.env.production`:

```bash
VITE_API_BASE_URL=https://api.your-domain.com/api
VITE_APP_PASSWORD=carnuvian
```

#### Verify Deployment

```bash
# List deployments
firebase hosting:channel:list

# View URL
firebase hosting:sites:get
```

---

### 5. GitHub Actions CI/CD

Automate deployments on git push.

#### GitHub Secrets

Add these secrets in GitHub: **Settings → Secrets → Actions**

**Firebase:**
- `FIREBASE_SERVICE_ACCOUNT` - Service account JSON
- `FIREBASE_PROJECT_ID` - Project ID

**Cloudflare:**
- `CLOUDFLARE_API_TOKEN` - API token
- `CLOUDFLARE_DOMAIN` - Your domain
- `CLOUDFLARE_TUNNEL_ID` - Tunnel ID

**Frontend:**
- `VITE_APP_PASSWORD` - Application password
- `VITE_API_BASE_URL_DEV` - Dev API URL
- `VITE_API_BASE_URL_PROD` - Prod API URL

#### Workflows

Three workflows are configured:

**1. `deploy-frontend.yml`**
- **Triggers:** Push to `main` or `develop`, changes to `web/**`
- **Actions:**
  - Builds frontend with environment-specific config
  - Deploys to Firebase Hosting

**2. `terraform.yml`**
- **Triggers:** Push to `main`, changes to `terraform/**`
- **Actions:**
  - Validates Terraform code
  - Plans changes (on PR)
  - Applies changes (on push to main)

**3. `test-backend.yml`**
- **Triggers:** Push or PR with backend changes
- **Actions:**
  - Runs linters (black, flake8, isort)
  - Runs tests with pytest

#### Manual Trigger

All workflows support manual triggers:

1. Go to **Actions** tab in GitHub
2. Select workflow
3. Click **Run workflow**
4. Choose branch and environment

#### Monitor Deployments

```bash
# View workflow runs
https://github.com/yourusername/imagineer/actions

# View deployment logs in Firebase
firebase hosting:channel:list
```

---

## Deployment Workflows

### Initial Deployment

Complete first-time setup:

```bash
# 1. Backend and infrastructure
make deploy-backend
make deploy-tunnel
make deploy-infra

# 2. Frontend
make deploy-frontend-prod

# 3. Verify
make deploy-status
curl https://api.your-domain.com/api/health
```

### Development Workflow

Day-to-day changes:

```bash
# 1. Make changes to code
vim web/src/components/MyComponent.jsx

# 2. Test locally
make dev

# 3. Commit and push
git add .
git commit -m "Add new feature"
git push origin develop

# 4. GitHub Actions automatically deploys to dev environment

# 5. Promote to production (when ready)
git checkout main
git merge develop
git push origin main
# GitHub Actions automatically deploys to production
```

### Infrastructure Changes

Updating Cloudflare configuration:

```bash
# 1. Edit Terraform files
vim terraform/main.tf

# 2. Preview changes
cd terraform
terraform plan

# 3. Apply via Makefile
cd ..
make deploy-infra

# Or push to trigger CI/CD
git add terraform/
git commit -m "Update firewall rules"
git push origin main
```

### Hotfix Workflow

Emergency fixes:

```bash
# 1. Create hotfix branch
git checkout -b hotfix/critical-bug

# 2. Fix issue
vim server/api.py

# 3. Test locally
make api

# 4. Deploy backend immediately (skip CI/CD)
make deploy-restart

# 5. Commit and push for CI/CD
git add .
git commit -m "Hotfix: Fix critical bug"
git push origin hotfix/critical-bug

# 6. Create PR and merge to main
```

---

## Troubleshooting

### Backend Issues

**Service won't start:**
```bash
# Check logs
sudo journalctl -u imagineer-api -n 100

# Common issues:
# - Port 10050 in use: lsof -i :10050
# - Missing dependencies: source venv/bin/activate && pip install -r requirements.txt
# - Permission issues: check /var/log/imagineer/ ownership
```

**502 Bad Gateway:**
```bash
# Check if backend is running
curl http://localhost:10050/api/health

# Check tunnel status
sudo systemctl status cloudflared-imagineer-api

# Restart services
make deploy-restart
```

### Tunnel Issues

**Tunnel won't connect:**
```bash
# Check tunnel status
cloudflared tunnel list
cloudflared tunnel info imagineer-api

# Validate configuration
cd terraform
cloudflared tunnel ingress validate --config cloudflare-tunnel.yml

# Check logs
sudo journalctl -u cloudflared-imagineer-api -f
```

**DNS not resolving:**
```bash
# Check DNS record
dig api.your-domain.com

# Verify in Cloudflare dashboard
# DNS → Records → Look for api subdomain

# Reapply Terraform
make deploy-infra
```

### Terraform Issues

**State lock errors:**
```bash
# Force unlock (use with caution)
cd terraform
terraform force-unlock <lock-id>
```

**Resource already exists:**
```bash
# Import existing resource
terraform import cloudflare_record.api <record-id>
```

### Firebase Issues

**Deployment fails:**
```bash
# Check authentication
firebase login --reauth

# Check project
firebase use --add

# Manual deployment
cd web
npm run build
firebase deploy --only hosting
```

### GitHub Actions Issues

**Workflow fails:**
```bash
# Check secrets are set
# GitHub → Settings → Secrets → Actions

# Test locally
cd web
VITE_API_BASE_URL=https://api.your-domain.com/api npm run build
```

---

## Rollback Procedures

### Frontend Rollback

Firebase keeps deployment history:

```bash
# View deployments
firebase hosting:channel:list

# Rollback to previous version
firebase hosting:rollback

# Or specify version
firebase hosting:clone <source-site> <target-site>
```

### Backend Rollback

Use git to revert:

```bash
# Stop service
sudo systemctl stop imagineer-api

# Checkout previous version
git checkout <previous-commit> server/

# Restart service
sudo systemctl start imagineer-api
```

### Infrastructure Rollback

Terraform state allows rollback:

```bash
# Revert Terraform files
cd terraform
git checkout <previous-commit> .

# Review changes
terraform plan

# Apply
terraform apply
```

### Emergency Rollback (Everything)

Complete system rollback:

```bash
# 1. Stop services
sudo systemctl stop imagineer-api
sudo systemctl stop cloudflared-imagineer-api

# 2. Revert code
git checkout <stable-tag>

# 3. Restart services
sudo systemctl start imagineer-api
sudo systemctl start cloudflared-imagineer-api

# 4. Rollback frontend
firebase hosting:rollback
```

---

## Monitoring & Maintenance

### Health Checks

```bash
# All services status
make deploy-status

# Individual checks
curl https://api.your-domain.com/api/health
curl https://your-domain.com

# System resources
nvidia-smi          # GPU usage
df -h               # Disk space
free -h             # Memory
```

### Log Locations

```bash
# Backend API
/var/log/imagineer/api.log
/var/log/imagineer/access.log
/var/log/imagineer/error.log

# Systemd services
journalctl -u imagineer-api
journalctl -u cloudflared-imagineer-api

# Cloudflare (via dashboard)
https://dash.cloudflare.com → Analytics → Logs
```

### Automated Monitoring

Consider setting up:
- **UptimeRobot** - Free uptime monitoring
- **Sentry** - Error tracking
- **Datadog** - Infrastructure monitoring

### Regular Maintenance

**Weekly:**
- Check error logs
- Review Cloudflare analytics
- Verify backups

**Monthly:**
- Update dependencies
- Review and rotate logs
- Check disk space

**Quarterly:**
- Security audit
- Update Terraform providers
- Review and update documentation

---

## CLI Reference

```bash
# Development
make dev                    # Start local development
make api                    # Start API only
make web-dev                # Start frontend only

# Deployment
make deploy-backend         # Deploy backend service
make deploy-tunnel          # Deploy Cloudflare Tunnel
make deploy-infra           # Deploy infrastructure (Terraform)
make deploy-frontend-dev    # Deploy frontend (dev)
make deploy-frontend-prod   # Deploy frontend (prod)
make deploy-all             # Deploy everything

# Management
make deploy-status          # Show deployment status
make deploy-restart         # Restart all services
make destroy-infra          # Destroy infrastructure

# Infrastructure
cd terraform
terraform init              # Initialize Terraform
terraform plan              # Preview changes
terraform apply             # Apply changes
terraform destroy           # Destroy all resources
terraform output            # Show outputs

# Firebase
firebase login              # Authenticate
firebase deploy             # Deploy hosting
firebase hosting:rollback   # Rollback deployment

# Cloudflare Tunnel
cloudflared tunnel list     # List tunnels
cloudflared tunnel info     # Show tunnel info
cloudflared tunnel run      # Run tunnel (manual)
```

---

## Next Steps

1. **Test your deployment end-to-end**
2. **Set up monitoring and alerting**
3. **Configure backups**
4. **Review security settings**
5. **Document any custom configurations**

---

**For questions or issues, see:**
- [Architecture Documentation](ARCHITECTURE.md)
- [Security Plan](SECURE_AUTHENTICATION_PLAN.md)
- [Firebase + Cloudflare Deployment](FIREBASE_CLOUDFLARE_DEPLOYMENT.md)
- [GitHub Issues](https://github.com/yourusername/imagineer/issues)

**Document Version:** 1.0
**Author:** Claude Code
**Last Review:** 2025-10-14
