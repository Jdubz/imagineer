# CLI Quick Reference

One-page reference for all deployment commands.

## Quick Deploy (First Time)

```bash
# Complete setup in order
make deploy-backend         # 1. Setup API service
make deploy-tunnel          # 2. Setup Cloudflare Tunnel
make deploy-infra           # 3. Deploy DNS/Firewall
make deploy-frontend-prod   # 4. Deploy frontend

# Check everything
make deploy-status
```

## Daily Commands

```bash
# Development
make dev                    # Start local dev environment
make api                    # API only (port 10050)
make web-dev                # Frontend only (port 10051)
make kill                   # Stop all dev services

# Quick image generation
make generate PROMPT="a cat"

# LoRA management
make lora-organize-fast     # Organize new LoRAs
make lora-previews-queue    # Generate previews
```

## Deployment Commands

### Backend (Your Server)

```bash
# Deploy/Update
make deploy-backend         # Setup systemd service
make deploy-restart         # Restart all services

# Management
sudo systemctl status imagineer-api
sudo systemctl restart imagineer-api
sudo journalctl -u imagineer-api -f

# Test
curl http://localhost:10050/api/health
```

### Cloudflare Tunnel

```bash
# Deploy/Update
make deploy-tunnel          # Setup tunnel + systemd

# Management
cloudflared tunnel list
cloudflared tunnel info imagineer-api
sudo systemctl status cloudflared-imagineer-api
sudo journalctl -u cloudflared-imagineer-api -f

# Configuration
vim terraform/cloudflare-tunnel.yml
sudo systemctl restart cloudflared-imagineer-api
```

### Infrastructure (Terraform)

```bash
# Deploy/Update
make deploy-infra           # Interactive apply
make destroy-infra          # Destroy all resources

# Manual control
cd terraform
terraform init              # First time only
terraform plan              # Preview changes
terraform apply             # Apply changes
terraform destroy           # Destroy resources
terraform output            # Show outputs
terraform show              # Show state

# Configuration
vim terraform/terraform.tfvars
```

### Frontend (Firebase)

```bash
# Deploy
make deploy-frontend-dev    # Deploy to dev
make deploy-frontend-prod   # Deploy to production

# Manual control
cd web
npm run build
firebase deploy --only hosting
firebase hosting:rollback

# Authentication
firebase login
firebase logout
firebase projects:list

# Configuration
vim web/.env.production
vim .firebaserc
```

## Status & Monitoring

```bash
# Overall status
make deploy-status

# Service status
sudo systemctl status imagineer-api
sudo systemctl status cloudflared-imagineer-api

# Logs
sudo journalctl -u imagineer-api -f
sudo journalctl -u cloudflared-imagineer-api -f
tail -f /var/log/imagineer/api.log

# Terraform state
cd terraform && terraform show

# Firebase deployments
firebase hosting:channel:list

# Test endpoints
curl http://localhost:10050/api/health
curl https://api.your-domain.com/api/health
```

## Troubleshooting

```bash
# Backend not starting
sudo journalctl -u imagineer-api -n 100
lsof -i :10050
sudo systemctl restart imagineer-api

# Tunnel not connecting
cloudflared tunnel info imagineer-api
sudo systemctl restart cloudflared-imagineer-api
dig api.your-domain.com

# Terraform errors
cd terraform
terraform plan
terraform apply -auto-approve

# Frontend build errors
cd web
npm install
npm run build

# Port conflicts
lsof -i :10050
lsof -i :10051
make kill
```

## Git Workflows

```bash
# Feature development
git checkout -b feature/new-thing
# ... make changes ...
git add .
git commit -m "Add new feature"
git push origin feature/new-thing
# Create PR → Merge to develop

# Deploy to dev
git checkout develop
git pull
git push origin develop      # Triggers CI/CD

# Deploy to production
git checkout main
git merge develop
git push origin main         # Triggers CI/CD

# Hotfix
git checkout -b hotfix/urgent
# ... fix issue ...
make deploy-restart          # Immediate deploy
git push origin hotfix/urgent
# Create PR → Merge to main
```

## GitHub Actions

```bash
# Trigger manual deploy
# GitHub → Actions → deploy-frontend → Run workflow

# View workflow runs
# GitHub → Actions → Select workflow → View logs

# Required secrets (Settings → Secrets → Actions)
FIREBASE_SERVICE_ACCOUNT
FIREBASE_PROJECT_ID
CLOUDFLARE_API_TOKEN
CLOUDFLARE_DOMAIN
CLOUDFLARE_TUNNEL_ID
VITE_APP_PASSWORD
VITE_API_BASE_URL_DEV
VITE_API_BASE_URL_PROD
```

## Emergency Procedures

```bash
# Full restart
make deploy-restart

# Backend rollback
sudo systemctl stop imagineer-api
git checkout <previous-commit> server/
sudo systemctl start imagineer-api

# Frontend rollback
firebase hosting:rollback

# Infrastructure rollback
cd terraform
git checkout <previous-commit> .
terraform plan
terraform apply

# Nuclear option (stop everything)
sudo systemctl stop imagineer-api
sudo systemctl stop cloudflared-imagineer-api
make kill
```

## File Locations

```bash
# Configuration
/home/jdubz/Development/imagineer/.env
/home/jdubz/Development/imagineer/web/.env.production
/home/jdubz/Development/imagineer/terraform/terraform.tfvars
/home/jdubz/Development/imagineer/terraform/cloudflare-tunnel.yml
/home/jdubz/Development/imagineer/.firebaserc

# Logs
/var/log/imagineer/api.log
/var/log/imagineer/access.log
/var/log/imagineer/error.log
journalctl -u imagineer-api
journalctl -u cloudflared-imagineer-api

# Systemd services
/etc/systemd/system/imagineer-api.service
/etc/systemd/system/cloudflared-imagineer-api.service

# Tunnel credentials
~/.cloudflared/cert.pem
~/.cloudflared/<tunnel-id>.json

# Terraform state
terraform/terraform.tfstate
```

## Environment Variables

### Backend (.env)
```bash
FLASK_ENV=production
FLASK_RUN_PORT=10050
ALLOWED_ORIGINS=https://your-app.web.app
CLOUDFLARE_VERIFY=true
RATELIMIT_ENABLED=true
LOG_LEVEL=INFO
```

### Frontend (web/.env.production)
```bash
VITE_API_BASE_URL=https://api.your-domain.com/api
VITE_APP_PASSWORD=[REDACTED]
```

### Terraform (terraform/terraform.tfvars)
```bash
cloudflare_api_token = "your-token"
domain = "your-domain.com"
tunnel_id = "your-tunnel-id"
enable_geo_blocking = false
```

## Common Tasks

```bash
# Update backend code
git pull
sudo systemctl restart imagineer-api

# Update frontend
git pull
make deploy-frontend-prod

# Update infrastructure
vim terraform/main.tf
make deploy-infra

# Add new Cloudflare rule
vim terraform/main.tf       # Add rule
cd terraform
terraform plan              # Review
cd .. && make deploy-infra  # Apply

# Change API URL
vim web/.env.production
make deploy-frontend-prod

# Update password
# GitHub → Settings → Secrets → VITE_APP_PASSWORD
# Then push to trigger rebuild

# Check GPU usage
nvidia-smi

# Check disk space
df -h

# View active jobs
curl http://localhost:10050/api/jobs
```

## Performance Monitoring

```bash
# Backend performance
curl http://localhost:10050/api/health
tail -f /var/log/imagineer/access.log

# Cloudflare analytics
# Dashboard → Analytics → Traffic

# Firebase analytics
firebase hosting:channel:list

# System resources
htop
nvidia-smi
df -h
free -h
```

## Useful Aliases (Optional)

Add to `~/.bashrc`:

```bash
# Imagineer shortcuts
alias imgapi='sudo systemctl status imagineer-api'
alias imglog='sudo journalctl -u imagineer-api -f'
alias imgrestart='sudo systemctl restart imagineer-api'
alias tunnellog='sudo journalctl -u cloudflared-imagineer-api -f'
alias imghealth='curl http://localhost:10050/api/health'
```

---

**Quick Links:**
- [Full Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Architecture Docs](ARCHITECTURE.md)
- [Security Plan](SECURE_AUTHENTICATION_PLAN.md)
