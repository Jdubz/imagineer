# Production Server Setup Guide

**Last Updated:** 2025-10-14

Complete guide for setting up Imagineer in production on your local server with auto-deployment from GitHub.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Deployment Options](#deployment-options)
  - [Option 1: Docker (Recommended)](#option-1-docker-recommended)
  - [Option 2: Systemd (Traditional)](#option-2-systemd-traditional)
- [Auto-Deployment Setup](#auto-deployment-setup)
- [Management Commands](#management-commands)
- [Monitoring & Logs](#monitoring--logs)
- [Troubleshooting](#troubleshooting)

---

## Overview

This setup provides:
- **Production-ready** backend API with gunicorn
- **Auto-deployment** from main branch via GitHub webhooks
- **Always-on** services with systemd or Docker
- **Security** features (rate limiting, logging, health checks)
- **Optional** Nginx reverse proxy

### Architecture

```
GitHub (main branch)
      │
      │ Push/Merge
      ▼
[GitHub Webhook]
      │
      ▼
[Webhook Listener] :9000
      │
      │ Triggers
      ▼
[Auto-Deploy Script]
      │
      ├─> git pull
      ├─> docker-compose restart  OR  systemctl restart
      └─> health check
      │
      ▼
[Production API] :10050
      │
      └─> Serves requests
```

---

## Features

### ✅ Production-Ready

- **Gunicorn WSGI server** (2 workers, 300s timeout)
- **Health checks** (Docker & systemd)
- **Auto-restart** on failure
- **Log rotation** (10MB files, 3 backups)
- **Non-root user** (Docker security)

### ✅ Auto-Deployment

- **Webhook listener** (validates GitHub signatures)
- **Automatic pull** from main branch
- **Smart restart** (Docker or systemd)
- **Health validation** after deployment
- **Rollback** on failure

### ✅ Security

- **Webhook signature validation**
- **Rate limiting** (via Nginx or application)
- **Non-root execution**
- **Isolated environment** (Docker/venv)
- **Comprehensive logging**

### ✅ Monitoring

- **Health check endpoint** (/api/health)
- **Structured logging**
- **Service status** checks
- **Docker/systemd integration**

---

## Prerequisites

### Required

- **Python 3.12+**
- **Git**
- **Docker** (for Docker deployment) or **systemd** (for traditional deployment)
- **NVIDIA GPU** with CUDA support (recommended)
- **8GB+ RAM**
- **20GB+ disk space**

### Optional

- **Nginx** (reverse proxy, SSL termination)
- **certbot** (SSL certificates)

### Installation

```bash
# Docker (if not installed)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Logout and login for group changes

# Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify
docker --version
docker-compose --version
```

---

## Quick Start

### One-Command Setup

```bash
cd /home/jdubz/Development/imagineer
make prod-setup
```

This interactive script will:
1. Create `.env.production` (if needed)
2. Ask for deployment method (Docker/systemd)
3. Ask for Nginx setup
4. Ask for webhook setup
5. Deploy everything
6. Verify services

### Manual Commands

```bash
# 1. Create production config
cp .env.production.example .env.production
# Edit with your values

# 2. Setup production
make prod-setup

# 3. Check status
make prod-status

# 4. View logs
make prod-logs

# 5. Test API
curl http://localhost:10050/api/health
```

---

## Deployment Options

### Option 1: Docker (Recommended)

#### Benefits

- ✅ Isolated environment
- ✅ Easy updates (rebuild image)
- ✅ GPU passthrough support
- ✅ Consistent across environments
- ✅ Easy rollback

#### Setup

```bash
# Create environment file
cp .env.production.example .env.production

# Edit configuration
vim .env.production
```

**.env.production:**
```bash
FLASK_ENV=production
FLASK_DEBUG=false
ALLOWED_ORIGINS=https://your-app.web.app
CLOUDFLARE_VERIFY=false
RATELIMIT_ENABLED=true
WEBHOOK_SECRET=your-secret-here
GITHUB_REPO=yourusername/imagineer
DEPLOY_BRANCH=main
USE_DOCKER=true
```

#### Build and Start

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

#### Services Started

1. **imagineer-api** (port 10050)
   - Flask API with gunicorn
   - GPU access (NVIDIA runtime)
   - Auto-restart on failure
   - Health checks every 30s

2. **imagineer-webhook** (port 9000)
   - Listens for GitHub webhooks
   - Triggers auto-deployment
   - Validates signatures

#### Docker Commands

```bash
# Start
make prod-start
# Or: docker-compose up -d

# Stop
make prod-stop
# Or: docker-compose down

# Restart
make prod-restart
# Or: docker-compose restart

# Logs
make prod-logs
# Or: docker-compose logs -f

# Status
make prod-status
# Or: docker-compose ps

# Rebuild
docker-compose build --no-cache
docker-compose up -d
```

---

### Option 2: Systemd (Traditional)

#### Benefits

- ✅ Native Linux integration
- ✅ Journald logging
- ✅ System-wide service management
- ✅ Lower resource overhead

#### Setup

```bash
# Run setup script
bash scripts/deploy/setup-backend.sh

# This creates:
# - /etc/systemd/system/imagineer-api.service
# - /var/log/imagineer/
# - Enables and starts service
```

#### Service File

Located at `/etc/systemd/system/imagineer-api.service`:

```ini
[Unit]
Description=Imagineer API Server
After=network.target

[Service]
Type=simple
User=jdubz
WorkingDirectory=/home/jdubz/Development/imagineer
Environment="PATH=/home/jdubz/Development/imagineer/venv/bin"
EnvironmentFile=/home/jdubz/Development/imagineer/.env.production
ExecStart=/home/jdubz/Development/imagineer/venv/bin/gunicorn \
    --bind 127.0.0.1:10050 \
    --workers 2 \
    --timeout 300 \
    --access-logfile /var/log/imagineer/access.log \
    --error-logfile /var/log/imagineer/error.log \
    --log-level info \
    server.api:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Systemd Commands

```bash
# Start
sudo systemctl start imagineer-api

# Stop
sudo systemctl stop imagineer-api

# Restart
sudo systemctl restart imagineer-api

# Status
sudo systemctl status imagineer-api

# Enable (start on boot)
sudo systemctl enable imagineer-api

# Disable (don't start on boot)
sudo systemctl disable imagineer-api

# Logs
sudo journalctl -u imagineer-api -f

# Recent errors
sudo journalctl -u imagineer-api --since "1 hour ago" | grep ERROR
```

---

## Auto-Deployment Setup

### Step 1: Generate Webhook Secret

```bash
# Generate a random secret
openssl rand -hex 32

# Add to .env.production
WEBHOOK_SECRET=your-generated-secret-here
```

### Step 2: Configure GitHub Webhook

1. Go to your GitHub repository
2. Navigate to **Settings → Webhooks → Add webhook**
3. Configure:

```
Payload URL: http://your-server-ip:9000/webhook
Content type: application/json
Secret: (paste your WEBHOOK_SECRET)
Which events: Just the push event
Active: ✓ (checked)
```

4. Click **Add webhook**

### Step 3: Test Webhook

```bash
# Make a test commit to main branch
git checkout main
echo "test" >> test.txt
git add test.txt
git commit -m "Test auto-deployment"
git push origin main

# Watch webhook logs
make prod-logs

# Or for systemd:
sudo journalctl -u imagineer-webhook -f

# Check GitHub webhook deliveries
# Settings → Webhooks → Recent Deliveries
```

### Step 4: Verify Deployment

```bash
# Check status
make prod-status

# Test API
curl http://localhost:10050/api/health

# View logs
make prod-logs
```

### Manual Deployment

If you need to deploy without pushing:

```bash
# Trigger deployment manually
make prod-deploy

# Or run script directly
bash scripts/deploy/auto-deploy.sh
```

---

## Management Commands

All production commands use the `make prod-*` prefix:

```bash
# Setup (one-time)
make prod-setup              # Interactive production setup

# Service Management
make prod-start              # Start services
make prod-stop               # Stop services
make prod-restart            # Restart services

# Monitoring
make prod-status             # Show status and health
make prod-logs               # Tail logs (Ctrl+C to exit)

# Deployment
make prod-deploy             # Manual deployment trigger
```

### Equivalent Docker Commands

```bash
docker-compose up -d         # Start
docker-compose down          # Stop
docker-compose restart       # Restart
docker-compose ps            # Status
docker-compose logs -f       # Logs
docker-compose build         # Rebuild
```

### Equivalent Systemd Commands

```bash
sudo systemctl start imagineer-api    # Start
sudo systemctl stop imagineer-api     # Stop
sudo systemctl restart imagineer-api  # Restart
sudo systemctl status imagineer-api   # Status
sudo journalctl -u imagineer-api -f   # Logs
```

---

## Monitoring & Logs

### Health Check

```bash
# Quick health check
curl http://localhost:10050/api/health

# Pretty print
curl -s http://localhost:10050/api/health | python3 -m json.tool

# Expected output:
{
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": "2025-10-14T..."
}
```

### Logs

**Docker:**
```bash
# All logs
docker-compose logs

# Follow logs (real-time)
docker-compose logs -f

# Specific service
docker-compose logs api
docker-compose logs webhook

# Last 100 lines
docker-compose logs --tail=100
```

**Systemd:**
```bash
# Application logs
tail -f /var/log/imagineer/api.log
tail -f /var/log/imagineer/access.log
tail -f /var/log/imagineer/error.log

# Systemd logs
sudo journalctl -u imagineer-api -f

# Last hour
sudo journalctl -u imagineer-api --since "1 hour ago"

# Errors only
sudo journalctl -u imagineer-api | grep ERROR
```

### Monitoring Dashboard

Optional: Set up monitoring tools

```bash
# Simple log monitoring
watch -n 5 'curl -s http://localhost:10050/api/health'

# GPU monitoring
watch -n 1 nvidia-smi

# Disk space
df -h

# Memory usage
free -h

# Process monitoring
htop
```

---

## Nginx Reverse Proxy (Optional)

Nginx provides SSL termination, rate limiting, and better security.

### Setup

```bash
# Run Nginx setup script
sudo bash scripts/deploy/setup-nginx.sh

# Enter your domain when prompted
# Or leave blank for localhost
```

### Features

- **SSL/TLS termination** (when configured with certbot)
- **Rate limiting**:
  - Auth endpoints: 5/minute
  - Generation: 10/second
  - General: 100/minute
- **Connection limits**: 10 per IP
- **Security headers** (XSS, CORS, CSP)
- **Custom error pages**

### SSL Setup

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d api.your-domain.com

# Auto-renewal (certbot sets this up automatically)
sudo certbot renew --dry-run
```

### Nginx Commands

```bash
# Test configuration
sudo nginx -t

# Reload
sudo systemctl reload nginx

# Restart
sudo systemctl restart nginx

# Status
sudo systemctl status nginx

# Logs
sudo tail -f /var/log/nginx/imagineer-access.log
sudo tail -f /var/log/nginx/imagineer-error.log
```

---

## Troubleshooting

### Service Won't Start

**Docker:**
```bash
# Check logs
docker-compose logs

# Check if container exists
docker ps -a

# Remove and rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

**Systemd:**
```bash
# Check status
sudo systemctl status imagineer-api

# Check logs
sudo journalctl -u imagineer-api -n 100

# Check if port is in use
lsof -i :10050

# Kill process on port
sudo lsof -ti:10050 | xargs kill -9
```

### Auto-Deployment Not Working

```bash
# Check webhook service
make prod-status

# Check webhook logs
docker-compose logs webhook
# Or: sudo journalctl -u imagineer-webhook -f

# Test webhook manually
curl -X POST http://localhost:9000/deploy

# Check GitHub webhook deliveries
# Go to: Settings → Webhooks → Recent Deliveries
# Look for error messages
```

### Health Check Failing

```bash
# Check if service is running
make prod-status

# Check if port is accessible
curl http://localhost:10050/api/health

# Check firewall
sudo ufw status
sudo ufw allow 10050/tcp

# Check logs for errors
make prod-logs
```

### GPU Not Detected

**Docker:**
```bash
# Check NVIDIA Docker runtime
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# Install nvidia-docker2 if needed
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

**Systemd:**
```bash
# Check CUDA
nvidia-smi

# Check Python can access CUDA
source venv/bin/activate
python -c "import torch; print(torch.cuda.is_available())"
```

### Out of Disk Space

```bash
# Check disk usage
df -h

# Clean Docker
docker system prune -a

# Clean logs
sudo journalctl --vacuum-time=7d
find /var/log/imagineer -name "*.log.*" -delete

# Clean old outputs
du -h /mnt/speedy/imagineer/outputs | sort -rh | head -20
# Delete old batches as needed
```

---

## Security Checklist

Before going to production:

- [ ] Change default `WEBHOOK_SECRET`
- [ ] Set proper `ALLOWED_ORIGINS`
- [ ] Enable `CLOUDFLARE_VERIFY` (if using Cloudflare)
- [ ] Set up SSL with certbot
- [ ] Configure firewall rules
- [ ] Enable rate limiting
- [ ] Set up log rotation
- [ ] Regular security updates
- [ ] Monitor logs for suspicious activity

### Firewall Configuration

```bash
# Allow SSH (if needed)
sudo ufw allow 22/tcp

# Allow API (if not using Nginx)
sudo ufw allow 10050/tcp

# Allow Nginx (if using)
sudo ufw allow 'Nginx Full'

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

---

## Best Practices

### Regular Maintenance

**Daily:**
- Check service status
- Review error logs
- Monitor disk space

**Weekly:**
- Update dependencies (security patches)
- Review access logs
- Test backup/restore

**Monthly:**
- Full system update
- Security audit
- Performance review

### Backup Strategy

```bash
# Backup configuration
tar -czf config-backup-$(date +%Y%m%d).tar.gz \
    .env.production \
    docker-compose.yml \
    terraform/terraform.tfvars

# Backup application data
tar -czf data-backup-$(date +%Y%m%d).tar.gz \
    /mnt/speedy/imagineer/sets \
    /mnt/speedy/imagineer/models/lora

# Store backups securely offsite
```

### Update Strategy

1. **Test in development first**
2. **Backup current state**
3. **Deploy to production**
4. **Monitor for issues**
5. **Rollback if needed**

---

## Performance Tuning

### Gunicorn Workers

Adjust in `docker-compose.yml` or systemd service:

```bash
# Formula: (2 × CPU cores) + 1
# For 4 cores: 9 workers

--workers 9
```

### Docker Resources

```yaml
# docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
```

### Database Connection Pool

If using a database, configure connection pooling:

```python
# server/api.py
SQLALCHEMY_POOL_SIZE = 10
SQLALCHEMY_MAX_OVERFLOW = 20
```

---

## Next Steps

1. **Run prod-setup**: `make prod-setup`
2. **Configure GitHub webhook**
3. **Test auto-deployment**
4. **Set up monitoring**
5. **Configure SSL** (if using Nginx)
6. **Deploy frontend**: Follow [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

---

## Quick Reference

```bash
# Setup
make prod-setup

# Management
make prod-start
make prod-stop
make prod-restart
make prod-status
make prod-logs

# Deployment
make prod-deploy

# Health check
curl http://localhost:10050/api/health

# Docker
docker-compose ps
docker-compose logs -f
docker-compose restart

# Systemd
sudo systemctl status imagineer-api
sudo journalctl -u imagineer-api -f
```

---

**For more information:**
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Complete IaC deployment
- [CLI_QUICK_REFERENCE.md](CLI_QUICK_REFERENCE.md) - Command reference
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture

**Document Version:** 1.0
**Author:** Claude Code
**Last Review:** 2025-10-14
