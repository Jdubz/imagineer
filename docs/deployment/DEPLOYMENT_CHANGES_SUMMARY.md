# Deployment Changes Summary

This document summarizes all changes made to set up production deployment for Imagineer at https://imagineer.joshwentworth.com

## Architecture Change

**Before:**
- Frontend: Firebase Hosting (imagineer-generator.web.app)
- Backend: Cloudflare Tunnel (imagineer.joshwentworth.com)
- Two separate domains

**After:**
- Frontend + Backend: Single domain (imagineer.joshwentworth.com)
- Cloudflare Tunnel routes to both services:
  - `/api/*` → Flask API (localhost:10050)
  - `/*` → nginx serving React (localhost:8080)

## New Files Created

### Service Configuration

**`setup-production-services.sh`** (Executable script)
- Automated installation script
- Installs nginx if needed
- Copies all config files to system locations
- Enables and starts all services
- Tests endpoints
- Run with: `bash setup-production-services.sh`

**`imagineer-api.service`** (systemd service)
- Manages Flask API as a service
- Auto-restarts on failure
- Loads environment from `.env.production`
- Logs to systemd journal

**`cloudflared-imagineer-api.service`** (systemd service)
- Manages Cloudflare Tunnel as a service
- Auto-restarts on failure
- Uses config from `/etc/cloudflared/config.yml`
- Logs to systemd journal

**`nginx-imagineer.conf`** (nginx site config)
- Serves React static files from `public/`
- Listens on port 8080
- SPA routing (all routes → index.html)
- Security headers
- Gzip compression
- Asset caching (1 year for JS/CSS, no-cache for index.html)
- Health check endpoint at `/health`

### Documentation

**`DEPLOYMENT_QUICK_START.md`** (Root directory)
- 20-minute quick start checklist
- Step-by-step instructions
- Troubleshooting tips
- ~20 minutes to complete

**`docs/deployment/PRODUCTION_DEPLOYMENT_GUIDE.md`**
- Comprehensive deployment documentation
- Architecture overview
- Detailed troubleshooting
- Monitoring and maintenance
- OAuth configuration
- Manual deployment fallback

## Modified Files

### Configuration Files

**`cloudflared-config.yml`**
- **Before**: Routed all traffic to Flask API
- **After**: Routes `/api/*` to Flask, everything else to nginx
```yaml
ingress:
  - hostname: imagineer.joshwentworth.com
    path: /api/*
    service: http://localhost:10050
  - hostname: imagineer.joshwentworth.com
    service: http://localhost:8080  # nginx
```

**`.env.production`**
- **Added**: `https://imagineer.joshwentworth.com` to `ALLOWED_ORIGINS`
- **Before**: Only Firebase URLs
- **After**: Includes new production domain

**`web/.env.production`**
- **Changed**: `VITE_API_BASE_URL` from absolute to relative path
- **Before**: `https://api.imagineer.joshwentworth.com/api`
- **After**: `/api` (relative path)
- Works because frontend and backend are on same domain

**`.env.example`**
- **Expanded**: Added all production environment variables
- **Added**: Flask configuration section
- **Added**: Security and rate limiting configuration
- **Added**: Logging configuration
- **Updated**: OAuth documentation with redirect URIs

**`web/.env.example`**
- **Added**: Development vs Production configuration notes
- **Documented**: Why relative paths work in production
- **Added**: Architecture explanation

### GitHub Actions

**`.github/workflows/deploy-frontend.yml`**
- **Completely rewritten** from Firebase deployment to SSH deployment
- **Removed**: Firebase deployment steps
- **Added**: SSH key setup
- **Added**: rsync deployment to server
- **Added**: Atomic file replacement (backup → replace → cleanup)
- **Added**: Deployment verification
- **Changed**: API URL to `/api` (relative path)
- Triggers on push to main or manual dispatch

## Required GitHub Secrets

These secrets need to be added to GitHub Actions:

| Secret | Value | Purpose |
|--------|-------|---------|
| `SSH_PRIVATE_KEY` | SSH private key | Deploy via SSH |
| `SSH_HOST` | Server IP/hostname | Server address |
| `SSH_USER` | `jdubz` | SSH username |
| `VITE_APP_PASSWORD` | `[REDACTED]` | App password |

## OAuth Configuration Update

**Google Cloud Console changes needed:**

**Add** these authorized redirect URIs:
- `https://imagineer.joshwentworth.com/auth/google/callback`

**Keep** for local development:
- `http://localhost:10050/auth/google/callback`

**Optional** (can remove if not using Firebase anymore):
- `https://imagineer-generator.web.app/auth/google/callback`
- `https://imagineer-generator.firebaseapp.com/auth/google/callback`

## Deployment Flow

### Current Manual Flow
```bash
cd /home/jdubz/Development/imagineer
cd web && npm run build && cd ..
rm -rf public && cp -r web/dist public
```

### New Automated Flow (After GitHub Secrets Setup)
```bash
# Make changes to frontend code
git add .
git commit -m "feat: Add new feature"
git push origin main

# GitHub Actions automatically:
# 1. Checks out code
# 2. Installs dependencies
# 3. Runs linter
# 4. Runs tests
# 5. Builds React app
# 6. SSHs to server
# 7. Deploys to public/
# 8. Verifies deployment
```

## System Requirements

### Ports Used
- **8080**: nginx (React frontend) - internal only
- **10050**: Flask API - internal only
- **443/80**: Cloudflare Tunnel - public access

### Services Running
1. **nginx** - Web server for React static files
2. **imagineer-api** - Flask API server
3. **cloudflared-imagineer-api** - Cloudflare Tunnel

All services:
- Enabled for start on boot
- Auto-restart on failure
- Log to systemd journal

### Directories
- **`/home/jdubz/Development/imagineer/public/`** - React build (served by nginx)
- **`/etc/nginx/sites-available/imagineer`** - nginx config
- **`/etc/nginx/sites-enabled/imagineer`** - nginx config symlink
- **`/etc/systemd/system/imagineer-api.service`** - API service
- **`/etc/systemd/system/cloudflared-imagineer-api.service`** - Tunnel service
- **`/etc/cloudflared/config.yml`** - Tunnel config

## Service Management Commands

```bash
# Check status
sudo systemctl status nginx
sudo systemctl status imagineer-api
sudo systemctl status cloudflared-imagineer-api

# Start/stop/restart
sudo systemctl restart nginx
sudo systemctl restart imagineer-api
sudo systemctl restart cloudflared-imagineer-api

# View logs
sudo journalctl -u nginx -f
sudo journalctl -u imagineer-api -f
sudo journalctl -u cloudflared-imagineer-api -f

# Enable/disable auto-start
sudo systemctl enable nginx
sudo systemctl disable nginx
```

## Testing Checklist

After deployment, test these endpoints:

- [ ] `http://localhost:8080/health` - nginx health check
- [ ] `http://localhost:10050/api/health` - API health check
- [ ] `https://imagineer.joshwentworth.com` - Public frontend
- [ ] `https://api.imagineer.joshwentworth.com/api/health` - Public API
- [ ] `https://imagineer.joshwentworth.com/auth/login` - OAuth login

## Rollback Plan

If something goes wrong:

### Rollback Services
```bash
# Stop new services
sudo systemctl stop imagineer-api cloudflared-imagineer-api nginx

# Check what's running
sudo systemctl --all | grep -E "imagineer|cloudflared"
```

### Rollback Files
```bash
# All config files are in the repo
cd /home/jdubz/Development/imagineer
git log --oneline  # Find commit before changes
git checkout <commit-hash> -- <file>
```

### Manual Deployment (Bypass GitHub Actions)
```bash
cd /home/jdubz/Development/imagineer
git pull origin main
cd web && npm install && npm run build && cd ..
rm -rf public && cp -r web/dist public
```

## Next Steps

1. **Run setup script**: `bash setup-production-services.sh`
2. **Build and deploy frontend**: See Quick Start guide
3. **Configure GitHub secrets**: Enable auto-deployment
4. **Update Google OAuth**: Add redirect URI
5. **Test everything**: Visit all endpoints
6. **Start improvement plan**: See `docs/plans/REVISED_IMPROVEMENT_PLAN.md`

## Files Changed This Session

**Created:**
- `setup-production-services.sh`
- `imagineer-api.service`
- `cloudflared-imagineer-api.service`
- `nginx-imagineer.conf`
- `DEPLOYMENT_QUICK_START.md`
- `docs/deployment/PRODUCTION_DEPLOYMENT_GUIDE.md`
- `DEPLOYMENT_CHANGES_SUMMARY.md` (this file)

**Modified:**
- `cloudflared-config.yml`
- `.env.production`
- `web/.env.production`
- `.env.example`
- `web/.env.example`
- `.github/workflows/deploy-frontend.yml`

**Status:**
- 7 files created
- 6 files modified
- 0 files deleted
- Total changes: 13 files

## Commit Message Suggestion

```
feat: Set up production deployment with nginx and auto-deploy

Deploy Imagineer to single domain (imagineer.joshwentworth.com) with:

Infrastructure:
- Add nginx to serve React static files from public/
- Create systemd services for API, tunnel, and nginx
- Configure Cloudflare Tunnel to route /api/* and /*
- Add automated setup script for all services

GitHub Actions:
- Rewrite deploy-frontend.yml for SSH deployment
- Replace Firebase deployment with rsync to server
- Add atomic file replacement with backup
- Build with relative API paths (/api)

Configuration:
- Update frontend to use relative API paths
- Add imagineer.joshwentworth.com to CORS origins
- Update environment examples with production config
- Document OAuth redirect URIs

Documentation:
- Add DEPLOYMENT_QUICK_START.md (20-min checklist)
- Add comprehensive production deployment guide
- Document all configuration changes
- Include troubleshooting and rollback procedures

Files changed: 13 (7 created, 6 modified)

This completes the deployment infrastructure setup.
Next steps: Run setup script, configure GitHub secrets, test.
```
