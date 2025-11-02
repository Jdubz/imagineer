# 🚀 Production Server - Auto-Deploy Setup

**Complete production setup with auto-deployment from GitHub main branch**

> **2025-10 Update**
>
> - Frontend builds now deploy from GitHub Actions directly to Firebase Hosting (`static-sites-257923`), so the production workstation no longer needs Node.js for releases.
> - Backend promotion runs via `scripts/deploy/backend-release.sh`, invoked over SSH from CI. Docker remains optional; the default path is the systemd service configured by `scripts/deploy/setup-backend.sh`.
> - Grant your CI user passwordless sudo for `systemctl restart imagineer-api`, `systemctl status imagineer-api`, and `journalctl -u imagineer-api` (e.g., `/etc/sudoers.d/imagineer-ci`) or the release script will abort.

## ✅ What's Been Created

### 🐳 Docker Configuration

**Files:**
- `Dockerfile` - Multi-stage production image (Python 3.12, gunicorn, non-root user)
- `docker-compose.yml` - Complete service orchestration (API + webhook listener)
- `Dockerfile.webhook` - Webhook listener container

**Features:**
- GPU passthrough (NVIDIA runtime)
- Health checks every 30s
- Auto-restart on failure
- Log rotation (10MB, 3 files)
- Non-root execution (security)
- Volume mounts for models/outputs

### 🤖 Auto-Deployment System

**Files:**
- `scripts/deploy/webhook-listener.py` - GitHub webhook receiver
- `scripts/deploy/auto-deploy.sh` - Deployment automation script

**Features:**
- Validates GitHub webhook signatures
- Pulls latest code from main branch
- Smart restart (Docker or systemd)
- Health check verification
- Automatic rollback on failure
- Manual deployment trigger

### 🔧 Production Scripts

**Files:**
- `scripts/deploy/setup-production.sh` - Interactive setup wizard
- `scripts/deploy/setup-nginx.sh` - Nginx reverse proxy setup

**Capabilities:**
- Choose deployment method (Docker/systemd)
- Configure webhook listener
- Setup Nginx (optional)
- One-command production setup

### 📁 Configuration

**Files:**
- `.env.production.example` - Production environment template
- `nginx/nginx.conf` - Nginx reverse proxy with rate limiting

**Settings:**
- Flask production mode
- Gunicorn with 2 workers
- Rate limiting configuration
- Webhook secret
- GitHub repository settings

### 🎮 Makefile Commands

**New targets:**
```makefile
make prod-setup      # Interactive setup wizard
make prod-start      # Start services
make prod-stop       # Stop services
make prod-restart    # Restart services
make prod-logs       # View logs (real-time)
make prod-status     # Show status & health
make prod-deploy     # Manual deployment
```

### 📚 Documentation

**Files:**
- `docs/PRODUCTION_SETUP.md` - Complete production guide (10,000+ words)

**Covers:**
- Both Docker and systemd approaches
- Auto-deployment setup
- GitHub webhook configuration
- Nginx reverse proxy
- Security best practices
- Troubleshooting guide

---

## 🚀 Quick Start Guide

### 1. One-Command Setup

```bash
cd /home/jdubz/Development/imagineer
make prod-setup
```

This will:
1. Create `.env.production` (if needed)
2. Ask for deployment method (Docker recommended)
3. Ask for webhook setup (for auto-deploy)
4. Ask for Nginx setup (optional)
5. Build and start services
6. Verify everything is running

### 2. Configure GitHub Webhook

```bash
# Generate webhook secret
openssl rand -hex 32

# Add to .env.production
WEBHOOK_SECRET=your-generated-secret

# In GitHub:
# Settings → Webhooks → Add webhook
# URL: http://your-server-ip:9000/webhook
# Secret: (paste your secret)
# Events: Just push event
```

### 3. Test Auto-Deployment

```bash
# Push to main branch
git checkout main
git push origin main

# Watch deployment
make prod-logs

# Verify
make prod-status
# Confirm deployed version & commit
curl -s https://imagineer-api.joshwentworth.com/api/health | jq '{status,version,git_commit,started_at}'
```

---

## 📊 Architecture

### Production Stack

```
┌─────────────────────────────────────┐
│     GitHub Repository (main)         │
└───────────────┬─────────────────────┘
                │ Push
                ▼
┌─────────────────────────────────────┐
│        GitHub Webhook                │
│   http://server:9000/webhook        │
└───────────────┬─────────────────────┘
                │ Validates signature
                ▼
┌─────────────────────────────────────┐
│    Webhook Listener (Python/Flask)  │
│    Port 9000 (Docker/systemd)       │
└───────────────┬─────────────────────┘
                │ Triggers
                ▼
┌─────────────────────────────────────┐
│   Auto-Deploy Script (Bash)         │
│   • git pull origin main             │
│   • docker-compose restart           │
│   • Health check validation          │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│    Production API (Gunicorn)        │
│    Port 10050                        │
│    • 2 workers                       │
│    • 300s timeout                    │
│    • GPU access                      │
│    • Auto-restart                    │
└─────────────────────────────────────┘
```

### With Nginx (Optional)

```
Internet → Nginx :80/443
    │ (SSL termination, rate limiting)
    ▼
Docker/systemd API :10050
    │ (Application logic)
    ▼
GPU (Image generation)
```

---

## 🎛️ Deployment Options

### Option 1: Docker (Recommended)

**Benefits:**
- ✅ Isolated environment
- ✅ Easy updates
- ✅ GPU passthrough
- ✅ Consistent deployment
- ✅ Easy rollback

**Commands:**
```bash
# Start
make prod-start
# Or: docker-compose up -d

# Status
make prod-status
# Or: docker-compose ps

# Logs
make prod-logs
# Or: docker-compose logs -f

# Restart
make prod-restart
# Or: docker-compose restart
```

### Option 2: Systemd

**Benefits:**
- ✅ Native Linux integration
- ✅ Journald logging
- ✅ System-wide service
- ✅ Lower overhead

**Commands:**
```bash
# Start
sudo systemctl start imagineer-api

# Status
sudo systemctl status imagineer-api

# Logs
sudo journalctl -u imagineer-api -f

# Restart
sudo systemctl restart imagineer-api
```

---

## 🔐 Security Features

### 1. Webhook Security

- **Signature validation** (HMAC-SHA256)
- **Secret-based authentication**
- **IP filtering** (optional via Nginx)
- **HTTPS support** (via Nginx + certbot)

### 2. Application Security

- **Non-root execution**
- **Environment-based secrets**
- **Rate limiting** (Nginx or application)
- **Security headers** (XSS, CSP, DENY frames)
- **Isolated Docker containers**

### 3. Network Security

- **Firewall configuration**
- **Port restrictions**
- **Nginx reverse proxy**
- **SSL/TLS termination**

---

## 📈 Monitoring & Logs

### Health Checks

```bash
# Quick check
curl http://localhost:10050/api/health

# Pretty print
curl -s http://localhost:10050/api/health | python3 -m json.tool

# Expected:
{
    "status": "healthy",
    "version": "1.0.0"
}
```

### Logs

**Docker:**
```bash
# All logs
docker-compose logs

# Follow logs
docker-compose logs -f

# API only
docker-compose logs api

# Webhook only
docker-compose logs webhook
```

**Systemd:**
```bash
# Application logs
tail -f /var/log/imagineer/api.log

# System logs
sudo journalctl -u imagineer-api -f

# Errors only
sudo journalctl -u imagineer-api | grep ERROR
```

### Monitoring

```bash
# Service status
make prod-status

# GPU usage
nvidia-smi

# Disk space
df -h

# Memory
free -h
```

---

## 🔧 Common Tasks

### Deploy New Code

```bash
# Automatic (push to main)
git push origin main
# Webhook triggers deployment

# Manual
make prod-deploy
```

### Update Dependencies

```bash
# Docker
vim requirements.txt
docker-compose build --no-cache
docker-compose up -d

# Systemd
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart imagineer-api
```

### Rollback Deployment

```bash
# Automatic (if health check fails)
# Script automatically reverts to previous commit

# Manual
cd /home/jdubz/Development/imagineer
git checkout HEAD~1
make prod-restart
```

### Scale Workers

```bash
# Edit docker-compose.yml
services:
  api:
    command: ["gunicorn", "--workers", "4", ...]

# Restart
docker-compose restart
```

---

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check logs
make prod-logs

# Docker: Check container status
docker-compose ps

# Systemd: Check service status
sudo systemctl status imagineer-api

# Check port availability
lsof -i :10050
```

### Webhook Not Triggering

```bash
# Check webhook service
make prod-status

# Test manual trigger
curl -X POST http://localhost:9000/deploy

# Check GitHub webhook deliveries
# GitHub → Settings → Webhooks → Recent Deliveries
```

### Health Check Failing

```bash
# Test endpoint
curl http://localhost:10050/api/health

# Check service
make prod-status

# View errors
make prod-logs | grep ERROR
```

### GPU Not Detected

```bash
# Docker: Test NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# Check CUDA
nvidia-smi

# Verify in Python
source venv/bin/activate
python -c "import torch; print(torch.cuda.is_available())"
```

---

## 📋 Checklist

### Initial Setup

- [ ] Run `make prod-setup`
- [ ] Create `.env.production`
- [ ] Generate webhook secret
- [ ] Configure GitHub webhook
- [ ] Test auto-deployment
- [ ] Verify health checks
- [ ] Setup monitoring

### Security (Before Production)

- [ ] Change default webhook secret
- [ ] Configure firewall rules
- [ ] Setup SSL with certbot (if using Nginx)
- [ ] Enable rate limiting
- [ ] Set proper ALLOWED_ORIGINS
- [ ] Review security headers
- [ ] Test rollback procedure

### Ongoing Maintenance

- [ ] Monitor logs daily
- [ ] Check disk space weekly
- [ ] Update dependencies monthly
- [ ] Test backups quarterly
- [ ] Security audit quarterly

---

## 🔗 Related Documentation

- **[PRODUCTION_SETUP.md](docs/PRODUCTION_SETUP.md)** - Complete production guide
- **[DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)** - Full IaC deployment
- **[CLI_QUICK_REFERENCE.md](docs/CLI_QUICK_REFERENCE.md)** - Command reference
- **[SECURE_AUTHENTICATION_PLAN.md](docs/SECURE_AUTHENTICATION_PLAN.md)** - Auth upgrades

---

## 📞 Quick Commands Reference

```bash
# Setup
make prod-setup           # One-time setup

# Management
make prod-start           # Start services
make prod-stop            # Stop services
make prod-restart         # Restart services
make prod-status          # Show status
make prod-logs            # View logs

# Deployment
make prod-deploy          # Manual deploy

# Health
curl http://localhost:10050/api/health

# Docker
docker-compose ps         # Status
docker-compose logs -f    # Logs
docker-compose restart    # Restart

# Systemd
sudo systemctl status imagineer-api
sudo journalctl -u imagineer-api -f
```

---

## 🎉 Ready to Deploy!

Your production server is now configured for:
- ✅ Always-on operation (Docker/systemd)
- ✅ Auto-deployment from main branch
- ✅ Secure webhook validation
- ✅ GPU acceleration
- ✅ Health monitoring
- ✅ Easy management commands
- ✅ Comprehensive logging

**Next Steps:**
1. Run `make prod-setup`
2. Configure GitHub webhook
3. Push to main and watch it auto-deploy!

---

**Version:** 1.0.0
**Last Updated:** 2025-10-14
**License:** MIT
