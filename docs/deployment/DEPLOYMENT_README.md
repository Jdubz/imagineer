# 🚀 Imagineer - IaC Deployment

**Infrastructure as Code setup with maximum CLI control**

This project uses a complete IaC approach for deploying to production with:
- **Terraform** for Cloudflare infrastructure
- **Bash scripts** for service deployment
- **Makefile** for workflow automation
- **GitHub Actions** for CI/CD

## 🎯 Quick Start

```bash
# 1. One-command backend deployment
make deploy-backend

# 2. One-command tunnel deployment
make deploy-tunnel

# 3. One-command infrastructure deployment
make deploy-infra

# 4. One-command frontend deployment
make deploy-frontend-prod

# 5. Check everything is running
make deploy-status
```

## 📁 Project Structure

```
imagineer/
├── terraform/                          # Infrastructure as Code
│   ├── main.tf                        # Cloudflare resources (DNS, WAF, rate limits)
│   ├── variables.tf                   # Input variables
│   ├── outputs.tf                     # Output values
│   ├── terraform.tfvars.example       # Configuration template
│   └── cloudflare-tunnel.yml.example  # Tunnel config template
│
├── scripts/deploy/                    # Deployment automation
│   ├── setup-backend.sh              # Backend systemd service setup
│   ├── setup-cloudflare-tunnel.sh    # Tunnel systemd service setup
│   └── deploy-frontend.sh            # Firebase deployment script
│
├── .github/workflows/                 # CI/CD pipelines
│   ├── deploy-frontend.yml           # Frontend deployment on push
│   ├── terraform.yml                 # Infrastructure changes
│   └── test-backend.yml              # Backend tests
│
├── docs/
│   ├── DEPLOYMENT_GUIDE.md           # Complete deployment documentation
│   ├── CLI_QUICK_REFERENCE.md        # One-page command reference
│   ├── SECURE_AUTHENTICATION_PLAN.md # Authentication upgrade path
│   └── FIREBASE_CLOUDFLARE_DEPLOYMENT.md # Original plan
│
├── web/
│   ├── .env.development              # Dev environment config
│   ├── .env.production               # Prod environment config
│   └── src/components/
│       └── PasswordGate.jsx          # Authentication component
│
├── firebase.json                      # Firebase Hosting config
├── .firebaserc.example                # Firebase project config template
└── Makefile                           # All CLI commands
```

## 🛠️ What Was Created

### 1. Password Gate ✅
- **Component:** `web/src/components/PasswordGate.jsx`
- **Features:** 24-hour localStorage sessions, logout functionality
- **Password:** Stored as `VITE_APP_PASSWORD` environment variable
- **Upgrade Path:** `docs/SECURE_AUTHENTICATION_PLAN.md`

### 2. Terraform Configuration ✅
- **Files:** `terraform/*.tf`
- **Manages:**
  - DNS records for API subdomain
  - Rate limiting (10/min for generation, 5/min for auth)
  - WAF rules (bot protection, optional geo-blocking)
  - Page rules (SSL, security headers)
- **Provider:** Cloudflare

### 3. Deployment Scripts ✅
- **Backend:** `scripts/deploy/setup-backend.sh`
  - Creates systemd service for Flask API
  - Sets up logging directory
  - Configures gunicorn with 2 workers

- **Tunnel:** `scripts/deploy/setup-cloudflare-tunnel.sh`
  - Installs cloudflared
  - Creates and configures tunnel
  - Sets up systemd service

- **Frontend:** `scripts/deploy/deploy-frontend.sh`
  - Builds React app with environment config
  - Deploys to Firebase Hosting
  - Supports dev/staging/prod environments

### 4. Makefile Automation ✅
- **Deployment Commands:**
  - `make deploy-backend` - Deploy API service
  - `make deploy-tunnel` - Deploy Cloudflare Tunnel
  - `make deploy-infra` - Deploy infrastructure (Terraform)
  - `make deploy-frontend-dev` - Deploy frontend (dev)
  - `make deploy-frontend-prod` - Deploy frontend (prod)
  - `make deploy-all` - Deploy everything
  - `make deploy-status` - Show deployment status
  - `make deploy-restart` - Restart all services
  - `make destroy-infra` - Destroy infrastructure

### 5. GitHub Actions CI/CD ✅
- **Workflows:**
  - `deploy-frontend.yml` - Auto-deploy frontend on push
  - `terraform.yml` - Plan/apply infrastructure changes
  - `test-backend.yml` - Run backend tests and linting

### 6. Firebase Configuration ✅
- **Files:**
  - `firebase.json` - Hosting config with security headers
  - `.firebaserc.example` - Project configuration template
- **Features:**
  - SPA routing
  - Asset caching (1 year for static, no-cache for HTML)
  - Security headers (CSP, XSS, frame options)

## 📚 Documentation

### Primary Docs
1. **[DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)** - Complete step-by-step guide
   - Prerequisites and installation
   - Detailed setup for each component
   - Troubleshooting and rollback procedures

2. **[CLI_QUICK_REFERENCE.md](docs/CLI_QUICK_REFERENCE.md)** - One-page command reference
   - Quick deploy commands
   - Daily workflows
   - Emergency procedures

3. **[SECURE_AUTHENTICATION_PLAN.md](docs/SECURE_AUTHENTICATION_PLAN.md)** - Auth upgrade path
   - Current v1.0 password gate
   - Phase 2: Backend session authentication (recommended)
   - Phase 3: OAuth/OpenID Connect
   - Phase 4: JWT tokens

### Supporting Docs
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture
- **[FIREBASE_CLOUDFLARE_DEPLOYMENT.md](docs/FIREBASE_CLOUDFLARE_DEPLOYMENT.md)** - Original detailed plan

## 🔑 Configuration Required

Before deploying, you need to configure:

### 1. Terraform Variables
```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
```
Edit with:
- Cloudflare API token
- Your domain name
- Tunnel ID (after creating tunnel)

### 2. Firebase Config
```bash
cp .firebaserc.example .firebaserc
```
Edit with your Firebase project ID

### 3. Environment Variables

**Backend (.env):**
```bash
FLASK_ENV=production
FLASK_RUN_PORT=10050
ALLOWED_ORIGINS=https://your-app.web.app
VITE_APP_PASSWORD=carnuvian
```

**Frontend (web/.env.production):**
```bash
VITE_API_BASE_URL=https://api.your-domain.com/api
VITE_APP_PASSWORD=carnuvian
```

### 4. GitHub Secrets

Add in **Settings → Secrets → Actions:**
- `FIREBASE_SERVICE_ACCOUNT`
- `FIREBASE_PROJECT_ID`
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_DOMAIN`
- `CLOUDFLARE_TUNNEL_ID`
- `VITE_APP_PASSWORD`
- `VITE_API_BASE_URL_DEV`
- `VITE_API_BASE_URL_PROD`

## 🚦 Deployment Workflow

### First Time Deployment

```bash
# 1. Install prerequisites
sudo apt install terraform
npm install -g firebase-tools
# Install cloudflared (see DEPLOYMENT_GUIDE.md)

# 2. Configure environment
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
cp .firebaserc.example .firebaserc
cp web/.env.example web/.env.production
# Edit all files with your values

# 3. Deploy in order
make deploy-backend         # Sets up systemd service for API
make deploy-tunnel          # Creates Cloudflare Tunnel
make deploy-infra           # Deploys DNS, WAF, rate limits
make deploy-frontend-prod   # Deploys React app to Firebase

# 4. Verify
make deploy-status
curl https://api.your-domain.com/api/health
```

### Ongoing Development

```bash
# Local development
make dev

# Deploy changes
git push origin develop     # Auto-deploys to dev via GitHub Actions
git push origin main        # Auto-deploys to prod via GitHub Actions

# Manual deployment (if needed)
make deploy-frontend-prod
```

### Infrastructure Updates

```bash
# Edit Terraform files
vim terraform/main.tf

# Preview changes
cd terraform && terraform plan

# Apply via Makefile
make deploy-infra

# Or push to trigger CI/CD
git push origin main
```

## 🔧 Management Commands

```bash
# Status checks
make deploy-status                        # Overall status
sudo systemctl status imagineer-api       # Backend status
sudo systemctl status cloudflared-*       # Tunnel status

# Service management
make deploy-restart                       # Restart all services
sudo systemctl restart imagineer-api      # Restart backend only

# Logs
sudo journalctl -u imagineer-api -f       # Backend logs
sudo journalctl -u cloudflared-* -f       # Tunnel logs
tail -f /var/log/imagineer/api.log        # Application logs

# Testing
curl http://localhost:10050/api/health    # Local API
curl https://api.your-domain.com/api/health  # Public API
```

## 🐛 Troubleshooting

```bash
# Backend won't start
sudo journalctl -u imagineer-api -n 100
lsof -i :10050

# Tunnel not connecting
cloudflared tunnel info imagineer-api
dig api.your-domain.com

# Frontend build fails
cd web && npm install && npm run build

# Terraform errors
cd terraform && terraform plan
```

See [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md#troubleshooting) for detailed troubleshooting.

## 📊 Architecture

```
┌──────────────┐
│   GitHub     │
│   (Code)     │
└──────┬───────┘
       │ Push
       ▼
┌─────────────────────────────────┐
│      GitHub Actions             │
│  • Build frontend               │
│  • Run tests                    │
│  • Apply Terraform              │
└───────┬──────────────┬──────────┘
        │              │
        ▼              ▼
┌───────────────┐  ┌──────────────────┐
│   Firebase    │  │   Cloudflare     │
│   Hosting     │  │   Edge           │
│   (CDN)       │  │  • DNS           │
│               │  │  • WAF           │
│               │  │  • Rate Limit    │
└───────────────┘  └────────┬─────────┘
                            │ Tunnel
                            ▼
                   ┌──────────────────┐
                   │  Your Server     │
                   │  • Flask API     │
                   │  • GPU           │
                   │  • systemd       │
                   └──────────────────┘
```

## 🔐 Security Features

- ✅ Password gate on frontend (24h sessions)
- ✅ Cloudflare rate limiting (10/min generation, 5/min auth)
- ✅ WAF bot protection
- ✅ Security headers (XSS, CSP, frame options)
- ✅ HTTPS enforced
- ✅ Backend not publicly accessible (Cloudflare Tunnel only)
- ✅ Secrets managed via environment variables
- ✅ Optional geo-blocking

**Upgrade Path:** See [SECURE_AUTHENTICATION_PLAN.md](docs/SECURE_AUTHENTICATION_PLAN.md) for Phase 2 backend authentication.

## 🎓 Learning Resources

- **Terraform:** https://www.terraform.io/docs
- **Cloudflare Tunnel:** https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
- **Firebase Hosting:** https://firebase.google.com/docs/hosting
- **GitHub Actions:** https://docs.github.com/en/actions
- **systemd:** https://www.freedesktop.org/software/systemd/man/systemd.service.html

## 📞 Support

- **Documentation:** `docs/` folder
- **Issues:** GitHub Issues
- **Quick Reference:** [CLI_QUICK_REFERENCE.md](docs/CLI_QUICK_REFERENCE.md)
- **Full Guide:** [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)

## ✅ Deployment Checklist

Before going live:

- [ ] Configure all environment files
- [ ] Set up GitHub secrets
- [ ] Deploy backend: `make deploy-backend`
- [ ] Deploy tunnel: `make deploy-tunnel`
- [ ] Configure Terraform variables
- [ ] Deploy infrastructure: `make deploy-infra`
- [ ] Configure Firebase
- [ ] Deploy frontend: `make deploy-frontend-prod`
- [ ] Test all endpoints
- [ ] Verify DNS propagation
- [ ] Check systemd services
- [ ] Review logs for errors
- [ ] Set up monitoring
- [ ] Change default password

## 🚀 You're Ready!

Everything is now configured for Infrastructure as Code deployment with maximum CLI control.

**Next Steps:**
1. Review [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)
2. Configure your environment files
3. Run `make deploy-backend`
4. Continue with the deployment workflow above

---

**Version:** 1.0.0
**Last Updated:** 2025-10-14
**License:** MIT
