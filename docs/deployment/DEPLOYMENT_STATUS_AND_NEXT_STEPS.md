# Imagineer Deployment Status & Next Steps

**Generated:** 2025-10-26
**Current Branch:** develop
**Goal:** Complete production deployment pipeline setup

---

## 🎯 Current Status Assessment

### ✅ Already Completed

1. **Cloudflare Tunnel Created**
   - Tunnel: `imagineer-api` (ID: db1a99dd-3d12-4315-b241-da2a55a5c30f)
   - Status: Active with 4 connections
   - Version: cloudflared 2025.9.1 ⚠️ (update recommended to 2025.10.0)

2. **Firebase Project Configured**
   - Project: `static-sites-257923`
   - Hosting target: `imagineer-generator`
   - Config files: `.firebaserc`, `firebase.json` ✅
   - Security headers configured ✅

3. **Environment Files Created**
   - `.env.production` exists
   - `web/.env.production` exists
   - Needs: Review and populate with actual values

4. **Deployment Scripts Ready**
   - `scripts/deploy/deploy-all.sh` - Main orchestration
   - `scripts/deploy/deploy-frontend.sh` - Frontend deployment
   - `scripts/deploy/setup-production.sh` - Backend setup
   - `scripts/deploy/setup-cloudflare-tunnel-custom.sh` - Tunnel setup
   - Makefile targets configured

5. **GitHub Actions Workflows**
   - `.github/workflows/deploy-frontend.yml` exists
   - `.github/workflows/terraform.yml` exists
   - `.github/workflows/test-backend.yml` exists
   - Needs: GitHub secrets configuration

6. **Documentation Complete**
   - Extensive deployment guides in `docs/deployment/`
   - Cheat sheets and quick references ready
   - Terraform configuration documented

### ✅ Recently Completed

1. **Backend API Service**
   - Systemd unit installed and controlled by `scripts/deploy/backend-release.sh`
   - GitHub Actions SSH deploy configured (`deploy-backend` job)

2. **Production Environment Variables**
   - `.env.production` populated with real values (Google OAuth, Flask secret, etc.)

3. **GitHub Secrets**
   - `FIREBASE_SERVICE_ACCOUNT`, `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY` configured for workflows

4. **Frontend Deployment**
   - Firebase Hosting deploy now happens from GitHub Actions (`deploy-frontend` job)

### ⏳ Still Outstanding

1. **Cloudflare DNS & Tunnel Update**
   - Add the Firebase-provided TXT verification record for `imagineer.joshwentworth.com`, then point it at Firebase Hosting once verification succeeds (TXT step still pending)
   - Keep the API served via Cloudflare Tunnel (`api.imagineer.joshwentworth.com`)
   - After propagation, verify HTTPS endpoints and update Terraform state/docs if needed

---

## 📋 Deployment Completion Checklist

### Phase 1: Environment Configuration (30 minutes)

**Step 1.1: Generate Secrets**

```bash
# Navigate to project
cd /home/jdubz/Development/imagineer

# Generate Flask secret key
python -c "import secrets; print('FLASK_SECRET_KEY=' + secrets.token_hex(32))"

# Add to .env.production
nano .env.production
```

Required secrets in `.env.production`:
```bash
# Flask
FLASK_SECRET_KEY=<generate with command above>
FLASK_ENV=production
FLASK_RUN_PORT=10050

# Google OAuth (already configured?)
GOOGLE_CLIENT_ID=<from Google Cloud Console>
GOOGLE_CLIENT_SECRET=<from Google Cloud Console>

# Anthropic (for AI labeling - Phase 3 feature)
ANTHROPIC_API_KEY=<optional for now, needed later>

# Hugging Face (optional, for gated models)
HF_TOKEN=<optional>
```

**Step 1.2: Frontend Environment**

```bash
# Edit web/.env.production
nano web/.env.production
```

Required values:
```bash
# API endpoint (via Cloudflare Tunnel)
VITE_API_BASE_URL=https://api.imagineer.joshwentworth.com/api

# Google OAuth Client ID (same as backend)
VITE_GOOGLE_CLIENT_ID=<from Google Cloud Console>

# Remove this - will be deleted in security updates
VITE_APP_PASSWORD=[REDACTED]
```

**Step 1.3: Terraform Configuration** (if using Terraform)

```bash
# Create terraform.tfvars from example
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
nano terraform/terraform.tfvars
```

### Phase 2: Backend Deployment (45 minutes)

**Step 2.1: Create Systemd Service**

```bash
# Create service file
sudo nano /etc/systemd/system/imagineer-api.service
```

Service configuration:
```ini
[Unit]
Description=Imagineer AI Image Generation API
After=network.target

[Service]
Type=simple
User=jdubz
Group=jdubz
WorkingDirectory=/home/jdubz/Development/imagineer
Environment="PATH=/home/jdubz/Development/imagineer/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/home/jdubz/Development/imagineer/.env.production
ExecStart=/home/jdubz/Development/imagineer/venv/bin/python server/api.py
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=imagineer-api

[Install]
WantedBy=multi-user.target
```

**Step 2.2: Enable and Start Service**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable imagineer-api

# Start service
sudo systemctl start imagineer-api

# Check status
sudo systemctl status imagineer-api

# View logs
sudo journalctl -u imagineer-api -f
```

**Step 2.3: Test Local API**

```bash
# Test health endpoint
curl http://localhost:10050/api/health

# Expected response:
# {"status":"ok","queue_size":0,"current_job":false,...}
```

### Phase 3: Cloudflare Tunnel Service (20 minutes)

**Step 3.1: Create Tunnel Config**

```bash
# Create config directory
sudo mkdir -p /etc/cloudflared

# Create tunnel config
sudo nano /etc/cloudflared/config.yml
```

Config content:
```yaml
tunnel: db1a99dd-3d12-4315-b241-da2a55a5c30f
credentials-file: /home/jdubz/.cloudflared/db1a99dd-3d12-4315-b241-da2a55a5c30f.json

ingress:
  - hostname: imagineer.joshwentworth.com
    service: http://localhost:10050
  - service: http_status:404
```

**Step 3.2: Create Systemd Service**

```bash
# Create service file
sudo nano /etc/systemd/system/cloudflared-imagineer-api.service
```

Service configuration:
```ini
[Unit]
Description=Cloudflare Tunnel for Imagineer API
After=network.target

[Service]
Type=simple
User=jdubz
ExecStart=/usr/local/bin/cloudflared tunnel --config /etc/cloudflared/config.yml run
Restart=always
RestartSec=5

StandardOutput=journal
StandardError=journal
SyslogIdentifier=cloudflared-imagineer

[Install]
WantedBy=multi-user.target
```

**Step 3.3: Enable and Start**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable cloudflared-imagineer-api

# Start service
sudo systemctl start cloudflared-imagineer-api

# Check status
sudo systemctl status cloudflared-imagineer-api

# View logs
sudo journalctl -u cloudflared-imagineer-api -f
```

**Step 3.4: Update Cloudflared**

```bash
# Update to latest version
sudo cloudflared update
cloudflared --version  # Should show 2025.10.0 or newer
```

**Step 3.5: Test Public API**

```bash
# Test via Cloudflare Tunnel
curl https://api.imagineer.joshwentworth.com/api/health

# Should return same response as localhost
```

### Phase 4: Frontend Deployment (15 minutes)

**Step 4.1: Build Frontend**

```bash
cd /home/jdubz/Development/imagineer

# Install dependencies (if needed)
cd web && npm install

# Build for production
npm run build

# Copy build to public directory (for Firebase)
cd ..
rm -rf public
cp -r web/dist public
```

**Step 4.2: Deploy to Firebase**

```bash
# Login to Firebase (if not already)
firebase login

# Deploy
firebase deploy --only hosting:imagineer

# Or use make target
make deploy-frontend-only
```

**Step 4.3: Test Frontend**

Open in browser:
- https://imagineer-generator.web.app
- Should show Imagineer UI
- Test login with Google OAuth
- Verify API calls work (check browser console)

### Phase 5: GitHub Actions Setup (30 minutes)

**Step 5.1: Configure GitHub Secrets**

Go to: https://github.com/<your-username>/imagineer/settings/secrets/actions

Add these secrets:

1. **FIREBASE_SERVICE_ACCOUNT**
```bash
# Get service account JSON
cat ~/.config/firebase/static-sites-257923-*.json

# Copy entire JSON content to GitHub secret
```

2. **CLOUDFLARE_API_TOKEN** (if using Terraform)
- Go to: https://dash.cloudflare.com/profile/api-tokens
- Create token with Zone:Read, DNS:Edit permissions
- Copy to GitHub secret

3. **GOOGLE_CLIENT_ID** & **GOOGLE_CLIENT_SECRET**
- Same values from .env.production
- Add as separate secrets

**Step 5.2: Test GitHub Actions**

```bash
# Push to main branch to trigger deployment
git checkout main
git merge develop
git push origin main

# Check Actions tab on GitHub
# https://github.com/<your-username>/imagineer/actions
```

**Step 5.3: Configure Branch Protection** (optional)

- Require PR reviews before merging to main
- Require status checks to pass
- Configure auto-deploy on merge to main

### Phase 6: Auto-Deploy Webhook (Optional, 20 minutes)

**Step 6.1: Configure Webhook Listener**

```bash
# Create systemd service for webhook listener
sudo nano /etc/systemd/system/imagineer-webhook.service
```

Service configuration:
```ini
[Unit]
Description=Imagineer GitHub Webhook Listener
After=network.target

[Service]
Type=simple
User=jdubz
WorkingDirectory=/home/jdubz/Development/imagineer
Environment="PATH=/home/jdubz/Development/imagineer/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/jdubz/Development/imagineer/venv/bin/python scripts/deploy/webhook-listener.py
Restart=always
RestartSec=10

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Step 6.2: Generate Webhook Secret**

```bash
# Generate secret
python -c "import secrets; print(secrets.token_hex(32))"

# Add to webhook-listener.py
nano scripts/deploy/webhook-listener.py
# Update GITHUB_WEBHOOK_SECRET variable
```

**Step 6.3: Configure GitHub Webhook**

1. Go to: https://github.com/<your-username>/imagineer/settings/hooks
2. Add webhook
3. Payload URL: `https://imagineer.joshwentworth.com/webhook` (needs tunnel route)
4. Content type: `application/json`
5. Secret: <generated secret from step 6.2>
6. Events: Just the push event

### Phase 7: Terraform Infrastructure (Optional, 30 minutes)

**Only if you want Cloudflare DNS/WAF/Rate Limiting managed by Terraform**

```bash
cd /home/jdubz/Development/imagineer/terraform

# Initialize
terraform init

# Review plan
terraform plan

# Apply (if plan looks good)
terraform apply

# Check status
terraform show
```

---

## 🧪 Verification Checklist

After completing deployment, verify all components:

### Backend Health
```bash
# Local
curl http://localhost:10050/api/health

# Public (via tunnel)
curl https://api.imagineer.joshwentworth.com/api/health

# Both should return:
# {"status":"ok",...}
```

### Services Running
```bash
# Check all services are active
sudo systemctl status imagineer-api
sudo systemctl status cloudflared-imagineer-api

# Both should show: Active: active (running)
```

### Frontend Accessible
```bash
# Test URLs
curl -I https://imagineer-generator.web.app
curl -I https://imagineer.joshwentworth.com

# Both should return: HTTP/2 200
```

### API Endpoints Working
```bash
# Test config endpoint
curl https://api.imagineer.joshwentworth.com/api/config

# Test sets endpoint
curl https://api.imagineer.joshwentworth.com/api/sets

# Test auth endpoint
curl https://api.imagineer.joshwentworth.com/api/auth/me
```

### Frontend Integration
Open browser to: https://imagineer-generator.web.app

Test:
- ✅ Page loads
- ✅ Can login with Google OAuth
- ✅ Can view LoRAs tab
- ✅ Can submit generation request
- ✅ Can view queue status
- ✅ Generated images appear

---

## 🔧 Useful Management Commands

### Service Management
```bash
# Restart everything
sudo systemctl restart imagineer-api
sudo systemctl restart cloudflared-imagineer-api

# View logs
sudo journalctl -u imagineer-api -f
sudo journalctl -u cloudflared-imagineer-api -f

# Stop services
sudo systemctl stop imagineer-api
sudo systemctl stop cloudflared-imagineer-api
```

### Deployment
```bash
# Full deployment
make deploy-all

# Frontend only (fast)
make deploy-frontend-only

# Backend only
sudo systemctl restart imagineer-api
```

### Monitoring
```bash
# Check service status
make prod-status

# View combined logs
make prod-logs

# Check tunnel status
cloudflared tunnel info imagineer-api

# Check port
lsof -i :10050
```

---

## 🆘 Troubleshooting

### Issue: API not accessible via tunnel

```bash
# Check tunnel is running
sudo systemctl status cloudflared-imagineer-api

# Check tunnel config
sudo cat /etc/cloudflared/config.yml

# Restart tunnel
sudo systemctl restart cloudflared-imagineer-api

# Check tunnel connections
cloudflared tunnel info imagineer-api
```

### Issue: Port 10050 already in use

```bash
# Find process using port
sudo lsof -i :10050

# Kill process
sudo kill -9 <PID>

# Restart service
sudo systemctl restart imagineer-api
```

### Issue: Frontend can't reach API

**Check CORS configuration:**
```python
# server/api.py - should include Firebase URL
ALLOWED_ORIGINS = [
    'https://imagineer.joshwentworth.com',
    'https://api.imagineer.joshwentworth.com',
    'https://imagineer-generator.web.app',
    'https://imagineer-generator.firebaseapp.com',
    'http://localhost:3000',
    'http://localhost:5173'
]
```

**Check frontend .env:**
```bash
# web/.env.production
VITE_API_BASE_URL=https://api.imagineer.joshwentworth.com/api
```

### Issue: OAuth not working

**Verify OAuth redirect URIs in Google Cloud Console:**
- https://api.imagineer.joshwentworth.com/api/auth/google/callback
- http://localhost:10050/api/auth/google/callback (development)
- http://localhost:5173/api/auth/google/callback (development Vite)

---

## 📊 Deployment Timeline Estimate

| Phase | Task | Time | Cumulative |
|-------|------|------|------------|
| 1 | Environment configuration | 30 min | 30 min |
| 2 | Backend service setup | 45 min | 1h 15min |
| 3 | Cloudflare tunnel service | 20 min | 1h 35min |
| 4 | Frontend deployment | 15 min | 1h 50min |
| 5 | GitHub Actions setup | 30 min | 2h 20min |
| 6 | Webhook (optional) | 20 min | 2h 40min |
| 7 | Terraform (optional) | 30 min | 3h 10min |

**Total: ~2-3 hours for core deployment**

---

## 🎯 Quick Start (Minimal Viable Deployment)

If you want to get deployed ASAP, do just these steps:

1. **Configure .env files** (15 min)
   - Generate FLASK_SECRET_KEY
   - Add Google OAuth credentials
   - Set VITE_API_BASE_URL in frontend

2. **Start backend service** (15 min)
   - Create systemd service
   - Start and enable
   - Test health endpoint

3. **Start tunnel service** (10 min)
   - Create systemd service
   - Start and enable
   - Test public endpoint

4. **Deploy frontend** (10 min)
   - Build with `npm run build`
   - Deploy with `firebase deploy`
   - Test in browser

**Total: ~50 minutes for basic working deployment**

---

## 🚀 Next Steps After Deployment

Once deployment is complete and verified:

1. **Monitor for a day** - Check logs, ensure stability
2. **Set up backups** - Regular backups of `/mnt/speedy/imagineer/`
3. **Begin improvement plan** - Start Phase 1 from REVISED_IMPROVEMENT_PLAN.md
4. **Add monitoring** - Consider adding uptime monitoring (UptimeRobot, etc.)

---

## 📚 Reference Documentation

- **Quick Reference:** `docs/deployment/DEPLOYMENT_CHEATSHEET.md`
- **Full Guide:** `docs/deployment/DEPLOYMENT_GUIDE.md`
- **Orchestration:** `docs/deployment/DEPLOYMENT_ORCHESTRATION.md`
- **Cloudflare Tunnel:** `docs/deployment/CLOUDFLARE_TUNNEL_SETUP.md`
- **Firebase Setup:** `docs/deployment/FIREBASE_SETUP.md`

---

**Ready to deploy? Start with Phase 1 above!** 🚀

If you run into issues, check the troubleshooting section or refer to the detailed deployment guides.
