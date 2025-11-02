# Production Architecture - Imagineer

## Current State Analysis (2025-10-31)

### What's Actually Deployed

**Domain: imagineer.joshwentworth.com**
- DNS: Points to Cloudflare IPs (104.21.56.188, 172.67.155.138)
- Backend: Serves Firebase Hosting content
- Behavior: Returns React SPA for ALL paths (including `/api/*`)
- CDN: Cloudflare CDN caching Firebase Hosting

**Domain: imagineer-generator.web.app**
- DNS: Firebase Hosting direct URL
- Backend: Firebase Hosting
- Behavior: Returns React SPA (working correctly)

**API Subdomain: imagineer-api.joshwentworth.com**
- DNS: **Does NOT exist**
- Status: Not configured

### The Problem

The frontend (deployed to Firebase) is configured to make API calls to:
```
VITE_API_BASE_URL=https://imagineer-api.joshwentworth.com/api
```

But this subdomain doesn't exist, causing API calls to fail.

Additionally, `imagineer.joshwentworth.com` is configured in Firebase Hosting as a custom domain, which means it's serving the frontend instead of proxying to the backend API.

### Root Cause

1. **DNS Misconfiguration**: `imagineer-api.joshwentworth.com` was never created
2. **Firebase Custom Domain**: `imagineer.joshwentworth.com` was added to Firebase Hosting, overriding the intended Cloudflare Tunnel routing
3. **Documentation Drift**: Multiple deployment docs describe different architectures

## Intended Architecture

### User's Desired Setup

```
Frontend (React SPA)
    ├─ Primary: https://imagineer-generator.web.app (Firebase Hosting)
    └─ Alias: https://imagineer-generator.firebaseapp.com

Backend API (Flask)
    └─ https://imagineer.joshwentworth.com/api/*
       ├─ Cloudflare Tunnel (db1a99dd-3d12-4315-b241-da2a55a5c30f)
       └─ Routes to: http://localhost:10050 (Flask on production server)

Additional Routing
    └─ https://imagineer.joshwentworth.com/* (non-API)
       └─ Could proxy to Firebase OR serve nothing (API-only domain)
```

### Key Design Principles

1. **Frontend**: Hosted on Firebase Hosting (CDN, auto-scaling, SSL)
2. **Backend**: Self-hosted Flask API via Cloudflare Tunnel (secure, no open ports)
3. **Single API Domain**: All API traffic goes through `imagineer.joshwentworth.com`
4. **CORS**: Backend allows Firebase Hosting origins

## Recommended Fix

### Option 1: Use Main Domain for API (Simplest)

**What to change:**

1. **Remove Firebase Custom Domain**:
   - Go to Firebase Console → Hosting → Custom domains
   - Remove `imagineer.joshwentworth.com` from Firebase
   - This frees up the domain for Cloudflare Tunnel

2. **Verify Cloudflare Tunnel**:
   ```bash
   ssh jdubz@<server-ip>  # Use IP, not domain

   # Check tunnel status
   sudo systemctl status cloudflared-imagineer-api

   # Check tunnel config
   cat ~/.cloudflared/config.yml
   ```

   Should show:
   ```yaml
   ingress:
     - hostname: imagineer.joshwentworth.com
       path: /api/*
       service: http://localhost:10050
   ```

3. **Update DNS in Cloudflare**:
   - Record: `imagineer.joshwentworth.com`
   - Type: CNAME
   - Value: `<tunnel-id>.cfargotunnel.com`
   - Proxy: Enabled (orange cloud)

4. **Update Frontend Configuration**:
   ```bash
   # web/.env.production
   VITE_API_BASE_URL=https://imagineer.joshwentworth.com/api
   ```

5. **Redeploy Frontend**:
   ```bash
   cd web
   npm run deploy:build
   firebase deploy --only hosting
   ```

**Result:**
- Frontend: `https://imagineer-generator.web.app`
- API: `https://imagineer.joshwentworth.com/api/*`

### Option 2: Use API Subdomain (Current Frontend Config) ✅ *In progress*

**What to change:**

1. **Create DNS Record**:
   - Record: `imagineer-api.joshwentworth.com`
   - Type: CNAME
   - Value: `<tunnel-id>.cfargotunnel.com`
   - Proxy: Enabled

2. **Update Cloudflare Tunnel Config**:
   ```bash
   ssh jdubz@<server-ip>

   # Edit tunnel config
   nano ~/.cloudflared/config.yml
   ```

   Change to:
   ```yaml
   tunnel: db1a99dd-3d12-4315-b241-da2a55a5c30f
   credentials-file: /home/jdubz/.cloudflared/db1a99dd-3d12-4315-b241-da2a55a5c30f.json

   ingress:
     - hostname: imagineer-api.joshwentworth.com
       service: http://localhost:10050
     - service: http_status:404
   ```

3. **Restart Tunnel**:
   ```bash
   sudo systemctl restart cloudflared-imagineer-api
   sudo systemctl status cloudflared-imagineer-api
   ```

4. **Keep Firebase Custom Domain** (optional):
   - Can keep `imagineer.joshwentworth.com` pointing to Firebase
   - This gives you a branded URL for the frontend

5. **Frontend Configuration**: Ensure builds use `https://imagineer-api.joshwentworth.com/api`

**Result:**
- Frontend: `https://imagineer.joshwentworth.com` (via Firebase)
- API: `https://imagineer-api.joshwentworth.com/api/*`

### Option 3: Hybrid (Recommended for Scalability)

Uses main domain with path-based routing:

1. **Configure Cloudflare Tunnel for Dual Routing**:
   ```yaml
   ingress:
     # API requests go to Flask
     - hostname: imagineer.joshwentworth.com
       path: /api/*
       service: http://localhost:10050

     # Everything else proxies to Firebase
     - hostname: imagineer.joshwentworth.com
       service: https://imagineer-generator.web.app

     - service: http_status:404
   ```

2. **Update Frontend**:
   ```bash
   # web/.env.production
   VITE_API_BASE_URL=https://imagineer.joshwentworth.com/api
   ```

3. **Update DNS**:
   - `imagineer.joshwentworth.com` → CNAME to tunnel

**Result:**
- Frontend: `https://imagineer.joshwentworth.com` (proxied to Firebase)
- API: `https://imagineer.joshwentworth.com/api/*` (direct to Flask)
- Fallback: `https://imagineer-generator.web.app` (direct Firebase)

## Testing Plan

After implementing any option:

### 1. Test API Endpoint
```bash
# Should return JSON health status
curl https://imagineer.joshwentworth.com/api/health
# or
curl https://imagineer-api.joshwentworth.com/api/health

# Expected response:
{"status":"ok","timestamp":"2025-10-31T..."}
```

### 2. Test Frontend
```bash
# Should return HTML
curl https://imagineer-generator.web.app/ | grep "<title>"

# Expected output:
<title>Imagineer - AI Image Generation</title>
```

### 3. Test End-to-End
1. Open frontend in browser: `https://imagineer-generator.web.app`
2. Check browser console for API errors
3. Try logging in with Google OAuth
4. Try generating an image
5. Verify no CORS errors

### 4. Verify Services on Server
```bash
ssh jdubz@<server-ip>

# Check API is running
sudo systemctl status imagineer-api
curl http://localhost:10050/api/health

# Check tunnel is running
sudo systemctl status cloudflared-imagineer-api
sudo journalctl -u cloudflared-imagineer-api -n 20

# Check tunnel routing
cloudflared tunnel info db1a99dd-3d12-4315-b241-da2a55a5c30f
```

## Current Service Configuration

### Flask API (imagineer-api.service)
- **Location**: `/etc/systemd/system/imagineer-api.service`
- **Port**: 10050
- **Working Dir**: `/home/jdubz/Development/imagineer`
- **Command**: `venv/bin/python server/api.py`
- **Environment**: `.env.production`

### Cloudflare Tunnel (cloudflared-imagineer-api.service)
- **Location**: `/etc/systemd/system/cloudflared-imagineer-api.service`
- **Config**: `~/.cloudflared/config.yml`
- **Tunnel ID**: `db1a99dd-3d12-4315-b241-da2a55a5c30f`
- **Credentials**: `~/.cloudflared/db1a99dd-3d12-4315-b241-da2a55a5c30f.json`

### Nginx (if used)
- **Config**: `/etc/nginx/sites-available/imagineer`
- **Port**: 8080
- **Purpose**: Serves static frontend build (if not using Firebase exclusively)

## Documentation Corrections Needed

The following files contain incorrect architecture information:

1. **docs/deployment/PRODUCTION_DEPLOYMENT_GUIDE.md**
   - Lines 14-20: Describes nginx serving React on port 8080
   - Reality: Frontend is on Firebase, not nginx

2. **docs/deployment/CLOUDFLARE_TUNNEL_SETUP.md**
   - Line 76: Says backend is at `http://127.0.0.1:10050`
   - Line 199: Lists API at `imagineer-api.joshwentworth.com`
   - Reality: Subdomain doesn't exist

3. **web/.env.production**
   - Line 10: `VITE_API_BASE_URL=https://imagineer-api.joshwentworth.com/api`
   - Reality: Should match actual deployment (Option 1, 2, or 3 above)

## Next Steps

1. **Immediate**: Choose Option 1, 2, or 3 based on requirements
2. **SSH Access**: Resolve SSH timeout issues to access server
3. **Implement Fix**: Update DNS, tunnel config, and frontend as needed
4. **Test Thoroughly**: Run all tests in Testing Plan section
5. **Update Docs**: Correct all deployment documentation
6. **Monitor**: Set up monitoring for API health and tunnel status

## Appendix: Diagnostic Commands

### Check DNS
```bash
# Check what imagineer resolves to
dig imagineer.joshwentworth.com
nslookup imagineer.joshwentworth.com

# Check API subdomain
dig imagineer-api.joshwentworth.com
```

### Check Firebase Custom Domains
```bash
firebase hosting:channel:list --project static-sites-257923
```

### Check Cloudflare Tunnels
```bash
# On server
cloudflared tunnel list
cloudflared tunnel info db1a99dd-3d12-4315-b241-da2a55a5c30f
```

### Check What's Serving Content
```bash
# Check response headers
curl -I https://imagineer.joshwentworth.com/

# Look for:
# - "server: cloudflare" (CDN)
# - "x-served-by" (Firebase/Fastly)
# - "cf-ray" (Cloudflare)
```

## Contact Information

- **Server**: imagineer.joshwentworth.com (or direct IP)
- **SSH User**: jdubz
- **Firebase Project**: static-sites-257923
- **Cloudflare Zone**: joshwentworth.com
- **Tunnel ID**: db1a99dd-3d12-4315-b241-da2a55a5c30f

---

**Last Updated**: 2025-10-31
**Status**: Architecture mismatch identified, awaiting fix implementation
