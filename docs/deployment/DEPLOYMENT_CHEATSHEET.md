# Imagineer Deployment Cheat Sheet

Quick reference for deploying Imagineer to production.

## 🚀 Quick Deploy

```bash
# Complete deployment (all components)
make deploy-all

# Preview without changes
make deploy-all-dry-run

# Frontend only (fast)
make deploy-frontend-only
```

## 📦 Component Deployment

```bash
# Backend + Tunnel
make deploy-backend-stack

# Individual components
bash scripts/deploy/deploy-all.sh --backend-only
bash scripts/deploy/deploy-all.sh --tunnel-only
bash scripts/deploy/deploy-all.sh --infra-only
bash scripts/deploy/deploy-all.sh --frontend-only
```

## 🔧 Production Management

```bash
# Status and logs
make prod-status              # Check service status
make prod-logs                # View live logs
make deploy-status            # Full deployment status

# Control services
make prod-start               # Start services
make prod-stop                # Stop services
make prod-restart             # Restart services
make prod-deploy              # Manual deployment

# Tunnel management
sudo systemctl status cloudflared-imagineer-api
sudo systemctl restart cloudflared-imagineer-api
sudo journalctl -u cloudflared-imagineer-api -f
```

## 🔑 Configuration Files

```bash
# Backend
.env.production                    # Flask configuration

# Frontend
web/.env.production                # React environment

# Infrastructure
terraform/terraform.tfvars         # Cloudflare settings
.firebaserc                        # Firebase project

# Tunnel
terraform/cloudflare-tunnel.yml    # Tunnel routing
```

## 🧪 Health Checks

```bash
# Local
curl http://localhost:10050/api/health

# Public
curl https://api.imagineer.joshwentworth.com/api/health

# Frontend
curl -I https://imagineer-generator.web.app
```

## 📍 URLs

**Frontend:**
- https://imagineer-generator.web.app
- https://imagineer-generator.firebaseapp.com

**API:**
- https://api.imagineer.joshwentworth.com/api

**Dashboards:**
- https://dash.cloudflare.com
- https://console.firebase.google.com/project/static-sites-257923

## 🆘 Troubleshooting

```bash
# Port conflict (10050)
sudo lsof -i :10050
sudo kill -9 $(sudo lsof -t -i :10050)

# Restart everything
make prod-restart
sudo systemctl restart cloudflared-imagineer-api

# Check logs
make prod-logs
sudo journalctl -u imagineer-api -n 50
sudo journalctl -u cloudflared-imagineer-api -n 50

# DNS check
dig imagineer.joshwentworth.com

# Cloudflare Tunnel
cloudflared tunnel list
cloudflared tunnel info imagineer-api
```

## 📚 Full Documentation

- **Orchestration Guide**: [docs/DEPLOYMENT_ORCHESTRATION.md](docs/DEPLOYMENT_ORCHESTRATION.md)
- **Complete Guide**: [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)
- **Cloudflare Tunnel**: [CLOUDFLARE_TUNNEL_SETUP.md](CLOUDFLARE_TUNNEL_SETUP.md)
- **Production Setup**: [PRODUCTION_README.md](PRODUCTION_README.md)
- **Firebase Setup**: [FIREBASE_QUICKSTART.md](FIREBASE_QUICKSTART.md)

## 🎯 Common Scenarios

### First Deploy
```bash
# 1. Configure files
cp .env.production.example .env.production
cp web/.env.production.example web/.env.production
cp terraform/terraform.tfvars.example terraform/terraform.tfvars

# 2. Edit configurations
nano .env.production
nano web/.env.production
nano terraform/terraform.tfvars

# 3. Deploy
make deploy-all
```

### Quick Frontend Update
```bash
# After editing React code
make deploy-frontend-only
```

### Backend Update
```bash
# After editing Flask code
make prod-deploy
```

### Infrastructure Update
```bash
# After editing terraform/*.tf
make deploy-infra
```

## 🔐 Secrets

**GitHub Secrets to Configure:**
- `FIREBASE_SERVICE_ACCOUNT` - For CI/CD
- `VITE_APP_PASSWORD` - App password ([REDACTED])
- `CLOUDFLARE_API_TOKEN` - For Terraform
- `CLOUDFLARE_TUNNEL_ID` - From tunnel setup

**Get Cloudflare API Token:**
https://dash.cloudflare.com/profile/api-tokens
