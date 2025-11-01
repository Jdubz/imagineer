# Production Deployment Fix Summary

## Issues Identified

### 1. **API Service Crashing** ❌
- **Cause:** Missing `DATABASE_URL` in `.env.production`
- **Error:** `RuntimeError: DATABASE_URL must be configured in production`
- **Impact:** API service restarted 1,923 times in crash loop

### 2. **Frontend Not Built** ❌
- **Cause:** `web/dist/` never created, `/public` directory empty
- **Impact:** 404 errors on all non-API routes

### 3. **Auto-Deploy Missing Frontend Build** ❌
- **Cause:** `auto-deploy.sh` only restarted backend, didn't rebuild frontend
- **Impact:** Future deployments would break frontend

---

## Fixes Applied

### ✅ 1. Added DATABASE_URL to .env.production
```bash
DATABASE_URL=sqlite:////home/jdubz/Development/imagineer/instance/imagineer.db
```

**Why SQLite is fine:**
- Single server deployment (not distributed)
- Low-to-moderate write concurrency
- Simple relational data (users, albums, images)
- No need for PostgreSQL features
- Easier backup and maintenance

### ✅ 2. Built Frontend
```bash
cd web && npm ci && npm run deploy:build
```

Output: `/home/jdubz/Development/imagineer/public/`
- Built React SPA with optimized production bundles
- Gzip and Brotli compressed assets
- nginx already configured to serve from this directory

### ✅ 3. Updated auto-deploy.sh
Added frontend build step to GitHub webhook deployment:
```bash
# Build frontend
echo "📦 Building frontend..."
cd "$APP_DIR/web"
npm ci --production=false
npm run deploy:build
cd "$APP_DIR"
echo "✅ Frontend built"
```

Also added nginx reload after service restart.

---

## What You Need to Do

### Run the restart script:
```bash
bash scripts/deploy/restart-production.sh
```

This will:
1. Restart the imagineer-api service (picks up new DATABASE_URL)
2. Reload nginx (picks up built frontend)
3. Test all endpoints
4. Report status

---

## Deployment Architecture

```
imagineer.joshwentworth.com (Cloudflare DNS)
         ↓
    Cloudflare Tunnel (cloudflared service)
         ↓
    ┌────────────┬─────────────┐
    ↓            ↓             ↓
/api/*      everything else   (404 fallback)
    ↓            ↓
localhost:10050  localhost:8080
    ↓            ↓
 Flask API      nginx
    ↓            ↓
SQLite DB      /public/ (React SPA)
```

### Configuration Files:
- **Tunnel:** `/etc/cloudflared/config.yml` ✅
- **nginx:** `/etc/nginx/sites-available/imagineer` ✅
- **API Service:** `/etc/systemd/system/imagineer-api.service` ✅
- **API Config:** `.env.production` ✅ (now with DATABASE_URL)
- **Frontend Build:** `web/package.json` → `deploy:build` script ✅

---

## GitHub Workflow Integration

### Current CI/CD Pipeline:

**On Pull Request:**
- Frontend: lint, typecheck, test
- Backend: format check, lint, test
- No deployment

**On Push to Main:**
- Builds frontend production bundle
- **Local webhook triggers:** `auto-deploy.sh`
  1. `git pull origin main`
  2. **Build frontend** (newly added)
  3. Restart imagineer-api service
  4. **Reload nginx** (newly added)
  5. Health check

### Workflow File:
`.github/workflows/ci.yml:105-108`
```yaml
- name: Build production bundle
  working-directory: web
  run: npm run deploy:build
```

This validates the build works but doesn't deploy it. The **actual deployment** happens via webhook when you push to main, which triggers `auto-deploy.sh` on your server.

---

## Testing

### Local Endpoints:
```bash
# API
curl http://localhost:10050/api/health
# Should return: {"status": "healthy"}

# Frontend
curl http://localhost:8080/
# Should return: HTML with <!DOCTYPE html>
```

### Public Endpoints:
```bash
# API
curl https://api.imagineer.joshwentworth.com/api/health

# Frontend
curl https://imagineer.joshwentworth.com/
# Or visit in browser
```

---

## Service Management

### API Service:
```bash
# Status
sudo systemctl status imagineer-api

# Logs (real-time)
sudo journalctl -u imagineer-api -f

# Restart
sudo systemctl restart imagineer-api

# Stop
sudo systemctl stop imagineer-api
```

### nginx:
```bash
# Status
sudo systemctl status nginx

# Reload config (no downtime)
sudo systemctl reload nginx

# Test config
sudo nginx -t
```

### Cloudflare Tunnel:
```bash
# Status
sudo systemctl status cloudflared

# Logs
sudo journalctl -u cloudflared -f

# Restart
sudo systemctl restart cloudflared
```

---

## Database Info

**Type:** SQLite
**Location:** `/home/jdubz/Development/imagineer/instance/imagineer.db`
**Managed by:** SQLAlchemy (Flask-SQLAlchemy)
**Migrations:** Database tables created automatically on first run

### Backup:
```bash
# Simple backup
cp instance/imagineer.db instance/imagineer.db.backup-$(date +%Y%m%d)

# Automated daily backup (optional)
# Add to crontab:
0 3 * * * cp /home/jdubz/Development/imagineer/instance/imagineer.db /backups/imagineer-$(date +\%Y\%m\%d).db
```

---

## Security Notes

- ✅ `.env.production` already in `.gitignore`
- ✅ Database credentials not exposed (local SQLite file)
- ✅ OAuth secrets properly configured
- ✅ CORS restricted to known origins
- ✅ Rate limiting enabled via nginx

---

## Future Improvements (Optional)

1. **PostgreSQL Migration:** If you ever need it
   - High concurrency requirements
   - Multiple app servers
   - Advanced SQL features
   - (Not needed now)

2. **Automated Testing:**
   - Add integration tests in CI
   - Test deployment to staging environment

3. **Database Backups:**
   - Automated daily backups
   - Retention policy (keep 30 days)

4. **Monitoring:**
   - Application performance monitoring
   - Error tracking (Sentry)
   - Uptime monitoring

---

## Files Changed

1. **`.env.production`** - Added `DATABASE_URL`
2. **`scripts/deploy/auto-deploy.sh`** - Added frontend build step
3. **`web/package.json`** - (no changes, already had `deploy:build` script)
4. **`public/`** - Built frontend assets (generated)

---

## Rollback Plan

If something goes wrong:

```bash
# Stop services
sudo systemctl stop imagineer-api

# Rollback code
cd /home/jdubz/Development/imagineer
git log --oneline -5  # Find commit to rollback to
git checkout <commit-hash>

# Rebuild frontend
cd web && npm ci && npm run deploy:build && cd ..

# Restart services
sudo systemctl start imagineer-api
sudo systemctl reload nginx
```

---

## Summary

✅ **Problem:** API crashed due to missing DATABASE_URL, frontend never built
✅ **Solution:** Added SQLite DATABASE_URL, built frontend, updated auto-deploy
✅ **Status:** Ready to deploy - just run `scripts/deploy/restart-production.sh`
✅ **Future:** GitHub pushes to main will auto-deploy both backend and frontend

**No PostgreSQL needed** - SQLite is perfect for this use case!
