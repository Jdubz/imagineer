# Production Deployment Guide

This guide walks through deploying Imagineer to production with:
- Single domain (imagineer.joshwentworth.com) for both frontend and API
- Automatic deployment from GitHub on push to main
- Cloudflare Tunnel for secure HTTPS access
- systemd services for process management

## Architecture Overview

```
User Request
    ↓
https://imagineer.joshwentworth.com
    ↓
Cloudflare Tunnel (db1a99dd-3d12-4315-b241-da2a55a5c30f)
    ↓
    ├─ /api/* → http://localhost:10050 (Flask API)
    └─ /*     → http://localhost:8080 (nginx serving React)
```

## Prerequisites

- Ubuntu/Debian Linux server
- Cloudflare Tunnel already configured (db1a99dd-3d12-4315-b241-da2a55a5c30f)
- Google OAuth credentials configured
- SSH access to server
- GitHub repository access

## Part 1: Server Setup

### Step 1: Run the Setup Script

This script installs nginx and configures all systemd services.

```bash
cd /home/jdubz/Development/imagineer
bash setup-production-services.sh
```

The script will:
1. Install nginx (if not already installed)
2. Configure nginx to serve React from `public/`
3. Install systemd service for Flask API
4. Install systemd service for Cloudflare Tunnel
5. Enable all services to start on boot
6. Start all services
7. Test endpoints

### Step 2: Verify Services

After the script completes, check service status:

```bash
# Check all services
sudo systemctl status nginx
sudo systemctl status imagineer-api
sudo systemctl status cloudflared-imagineer-api

# View logs
sudo journalctl -u nginx -f
sudo journalctl -u imagineer-api -f
sudo journalctl -u cloudflared-imagineer-api -f
```

### Step 3: Initial Frontend Build

Build and deploy the frontend for the first time:

```bash
cd /home/jdubz/Development/imagineer

# Build React app
cd web && npm install && npm run build && cd ..

# Copy to public directory
rm -rf public && cp -r web/dist public

# Verify files
ls -la public/
```

Test locally:
```bash
curl http://localhost:8080/health
curl http://localhost:10050/api/health
```

Test via tunnel:
```bash
curl https://imagineer.joshwentworth.com/health
curl https://imagineer.joshwentworth.com/api/health
```

## Part 2: GitHub Configuration

### Step 1: Generate SSH Key for Deployment

On your server:

```bash
# Generate deployment key
ssh-keygen -t ed25519 -f ~/.ssh/imagineer_deploy -N ""

# Display the private key (you'll add this to GitHub Secrets)
cat ~/.ssh/imagineer_deploy

# Add the public key to authorized_keys
cat ~/.ssh/imagineer_deploy.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### Step 2: Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add these secrets:

| Secret Name | Value | Description |
|------------|-------|-------------|
| `SSH_PRIVATE_KEY` | Contents of `~/.ssh/imagineer_deploy` | Private SSH key for deployment |
| `SSH_HOST` | Your server IP or hostname | Server address |
| `SSH_USER` | `jdubz` | SSH username |
| `VITE_APP_PASSWORD` | `[REDACTED]` | App password (deprecated, but still used) |

### Step 3: Test Auto-Deployment

1. Make a change to the frontend code in `web/`
2. Commit and push to main branch
3. Check GitHub Actions: https://github.com/joshbwentworth/imagineer/actions
4. Verify deployment succeeded
5. Test the changes at https://imagineer.joshwentworth.com

## Part 3: OAuth Configuration

### Update Google Cloud Console

Add these authorized redirect URIs to your Google OAuth app:

**Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client IDs**

Add:
- `https://imagineer.joshwentworth.com/auth/google/callback`
- `http://localhost:10050/auth/google/callback` (for local dev)

Remove (no longer needed):
- `https://imagineer-generator.web.app/auth/google/callback`
- `https://imagineer-generator.firebaseapp.com/auth/google/callback`

## Part 4: Troubleshooting

### Check Service Status

```bash
# Quick status check
systemctl is-active nginx imagineer-api cloudflared-imagineer-api

# Detailed status
sudo systemctl status nginx
sudo systemctl status imagineer-api
sudo systemctl status cloudflared-imagineer-api
```

### View Logs

```bash
# Recent logs
sudo journalctl -u nginx -n 50
sudo journalctl -u imagineer-api -n 50
sudo journalctl -u cloudflared-imagineer-api -n 50

# Follow logs in real-time
sudo journalctl -u imagineer-api -f
```

### Restart Services

```bash
# Restart individual services
sudo systemctl restart nginx
sudo systemctl restart imagineer-api
sudo systemctl restart cloudflared-imagineer-api

# Restart all
sudo systemctl restart nginx imagineer-api cloudflared-imagineer-api
```

### Common Issues

**API not responding:**
```bash
# Check if API is running
sudo systemctl status imagineer-api

# Check logs for errors
sudo journalctl -u imagineer-api -n 100

# Verify environment file exists
ls -la /home/jdubz/Development/imagineer/.env.production

# Test API directly
curl http://localhost:10050/api/health
```

**Frontend not loading:**
```bash
# Check if nginx is running
sudo systemctl status nginx

# Verify public directory exists
ls -la /home/jdubz/Development/imagineer/public/

# Check nginx logs
sudo journalctl -u nginx -n 50

# Test nginx config
sudo nginx -t
```

**Tunnel not working:**
```bash
# Check tunnel status
sudo systemctl status cloudflared-imagineer-api

# View tunnel logs
sudo journalctl -u cloudflared-imagineer-api -n 100

# Verify tunnel config
cat /etc/cloudflared/config.yml

# List active tunnels
cloudflared tunnel list
```

**GitHub Actions deployment failing:**
```bash
# Check SSH connectivity from GitHub
# The workflow will show detailed error messages

# Verify SSH key permissions
ls -la ~/.ssh/
chmod 600 ~/.ssh/authorized_keys

# Test SSH connection manually
ssh jdubz@<your-server-ip> "echo 'SSH working'"
```

## Part 5: Manual Deployment (Fallback)

If GitHub Actions is not working, you can deploy manually:

```bash
cd /home/jdubz/Development/imagineer

# Pull latest changes
git pull origin main

# Build frontend
cd web && npm install && npm run build && cd ..

# Deploy to public/
rm -rf public && cp -r web/dist public

# Verify
ls -la public/
curl https://imagineer.joshwentworth.com
```

## Part 6: Monitoring

### Health Checks

```bash
# All health checks should return 200 OK
curl -I https://imagineer.joshwentworth.com/health
curl -I https://imagineer.joshwentworth.com/api/health
```

### Performance Monitoring

```bash
# Watch API logs
sudo journalctl -u imagineer-api -f | grep -i error

# Monitor nginx access
sudo tail -f /var/log/nginx/access.log

# Check system resources
htop
df -h
```

## Next Steps

After deployment is complete, you can:

1. **Start implementing the improvement plan** (see `docs/plans/REVISED_IMPROVEMENT_PLAN.md`)
2. **Set up monitoring and alerts** (Phase 1 of improvement plan)
3. **Configure backups** for outputs and database (when SQLite is added)
4. **Add SSL certificate monitoring** to ensure Cloudflare tunnel stays healthy

## Files Created/Modified

This deployment setup involved:

- `setup-production-services.sh` - Automated setup script
- `nginx-imagineer.conf` - nginx configuration
- `imagineer-api.service` - systemd service for API
- `cloudflared-imagineer-api.service` - systemd service for tunnel
- `cloudflared-config.yml` - Cloudflare Tunnel routing config
- `.env.production` - Backend environment (updated ALLOWED_ORIGINS)
- `web/.env.production` - Frontend environment (updated to use /api)
- `.github/workflows/deploy-frontend.yml` - Auto-deployment workflow

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review logs: `sudo journalctl -u <service-name> -n 100`
3. Verify configuration files match this guide
4. Test each component independently (nginx, API, tunnel)
