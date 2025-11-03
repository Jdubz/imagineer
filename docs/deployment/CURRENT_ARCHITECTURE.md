# Current Production Architecture

**Last Updated:** 2025-11-03
**Status:** ACTIVE - In Production

## Overview

Imagineer uses a modern decoupled architecture with Firebase Hosting for the frontend and Cloudflare Tunnel for secure backend API access.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           INTERNET                                   │
└────────────────────┬────────────────────────────┬───────────────────┘
                     │                             │
                     │                             │
          ┌──────────▼──────────┐      ┌──────────▼──────────────┐
          │  Firebase Hosting   │      │  Cloudflare Edge        │
          │  Global CDN         │      │  DDoS Protection        │
          ├─────────────────────┤      ├─────────────────────────┤
          │ imagineer-generator │      │ imagineer-api           │
          │ .web.app            │      │ .joshwentworth.com      │
          │                     │      │                         │
          │ • React SPA         │      │ • WAF Rules             │
          │ • Static Assets     │      │ • Rate Limiting         │
          │ • Gzip/Brotli       │      │ • SSL/TLS               │
          │ • Security Headers  │      │ • IP Filtering          │
          └─────────────────────┘      └─────────────────────────┘
                                                   │
                                                   │ Encrypted Tunnel
                                                   │ (QUIC Protocol)
                                                   │
                                      ┌────────────▼────────────────┐
                                      │  Local Server               │
                                      │  (No Public IP Exposed)     │
                                      ├─────────────────────────────┤
                                      │  Gunicorn (localhost:10050) │
                                      │  • Flask REST API           │
                                      │  • SQLite/PostgreSQL        │
                                      │  • Job Queue                │
                                      │  • Image Generation         │
                                      │                             │
                                      │  Stable Diffusion 1.5       │
                                      │  • CUDA GPU Acceleration    │
                                      │  • Multi-LoRA Support       │
                                      │  • Batch Generation         │
                                      └─────────────────────────────┘
```

## Component Details

### Frontend: Firebase Hosting

**URLs:**
- Primary: https://imagineer-generator.web.app
- Alternate: https://imagineer-generator.firebaseapp.com

**Features:**
- Global CDN distribution
- Automatic SSL/TLS certificates
- Gzip and Brotli compression
- SPA routing (all routes → index.html)
- Security headers (X-Frame-Options, CSP, etc.)
- Asset caching (1 year for versioned assets)
- Zero downtime deployments

**Configuration:**
- `firebase.json` - Hosting rules and headers
- `.firebaserc` - Project and site configuration
- `web/.env.production` - Production environment variables

**Deployment:**
```bash
cd web
npm run build
firebase deploy --only hosting
```

### Backend API: Flask + Gunicorn

**Local Endpoint:** http://localhost:10050
**Public Endpoint:** https://imagineer-api.joshwentworth.com/api

**Tech Stack:**
- Flask 3.1.0 (REST API framework)
- Gunicorn (WSGI server, 2 workers)
- SQLite (development) / PostgreSQL (production option)
- Stable Diffusion 1.5 via Diffusers
- CUDA 12.1+ for GPU acceleration

**Important Changes:**
- ✅ **NO LONGER SERVES** the `/public` directory
- ✅ **NO LONGER SERVES** `index.html` at root
- ✅ Root endpoint `/` now returns JSON with API information
- ✅ All static frontend assets served by Firebase Hosting

**Service Management:**
```bash
# Status
sudo systemctl status imagineer-api

# Logs
sudo journalctl -u imagineer-api -f

# Restart
sudo systemctl restart imagineer-api
```

**Service File:** `/etc/systemd/system/imagineer-api.service`
```ini
[Unit]
Description=Imagineer API Server
After=network.target

[Service]
Type=simple
User=jdubz
WorkingDirectory=/home/jdubz/Development/imagineer
Environment="PATH=/home/jdubz/Development/imagineer/venv/bin"
ExecStart=/home/jdubz/Development/imagineer/venv/bin/gunicorn \
    --bind 127.0.0.1:10050 \
    --workers 2 \
    --timeout 300 \
    --access-logfile /var/log/imagineer/access.log \
    --error-logfile /var/log/imagineer/error.log \
    server.api:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Cloudflare Tunnel

**Tunnel Name:** imagineer-api
**Tunnel ID:** db1a99dd-3d12-4315-b241-da2a55a5c30f

**Purpose:**
- Exposes local Flask API to the internet securely
- No public IP address required
- Encrypted tunnel using QUIC protocol
- Automatic SSL/TLS termination at Cloudflare edge
- DDoS protection and rate limiting

**Configuration:** `/etc/cloudflared/config.yml`
```yaml
tunnel: db1a99dd-3d12-4315-b241-da2a55a5c30f
credentials-file: /home/jdubz/.cloudflared/db1a99dd-3d12-4315-b241-da2a55a5c30f.json

ingress:
  # API endpoints go to Flask backend
  - hostname: imagineer-api.joshwentworth.com
    service: http://localhost:10050

  # Fallback
  - service: http_status:404
```

**Service Management:**
```bash
# Status
sudo systemctl status cloudflared-imagineer-api

# Logs
sudo journalctl -u cloudflared-imagineer-api -f

# Restart
sudo systemctl restart cloudflared-imagineer-api

# Tunnel Info
cloudflared tunnel list
cloudflared tunnel info imagineer-api
```

### Nginx (DEPRECATED - Not Used in Production)

**File:** `/etc/nginx/sites-available/imagineer`

**Status:**
- ⚠️ Config exists but is **NOT active** in production
- Used port 8080 for local testing only
- Replaced by Firebase Hosting + Cloudflare Tunnel
- Can be safely disabled or removed

**Why Deprecated:**
- Public directory no longer needs to be served locally
- Firebase Hosting provides better CDN performance
- Cloudflare Tunnel handles API routing
- Simpler architecture with fewer moving parts

## Environment Variables

### Frontend (web/.env.production)

```bash
# Firebase Hosting URLs
# https://imagineer-generator.web.app
# https://imagineer-generator.firebaseapp.com

# API Base URL for production
VITE_API_BASE_URL=https://imagineer-api.joshwentworth.com/api
```

### Backend (.env - NOT committed to git)

```bash
# Environment
FLASK_ENV=production
FLASK_DEBUG=False

# CORS Origins (Firebase Hosting URLs)
ALLOWED_ORIGINS=https://imagineer-generator.web.app,https://imagineer-generator.firebaseapp.com

# Database
DATABASE_URL=sqlite:////home/jdubz/Development/imagineer/instance/imagineer.db

# OAuth (Google)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-secret
GOOGLE_REDIRECT_URI=https://imagineer-api.joshwentworth.com/auth/callback

# Session
SECRET_KEY=your-secret-key
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
```

## Request Flow

### User Visits Frontend

1. User navigates to `https://imagineer-generator.web.app`
2. Firebase Hosting serves `index.html` and static assets from CDN
3. React app loads and initializes
4. App reads `VITE_API_BASE_URL` from build-time environment

### API Request from Frontend

1. React app makes API call to `https://imagineer-api.joshwentworth.com/api/generate`
2. Request hits Cloudflare edge servers
3. Cloudflare applies WAF rules and rate limiting
4. Request routed through encrypted tunnel to `localhost:10050`
5. Gunicorn receives request and forwards to Flask app
6. Flask processes request, generates image, returns response
7. Response travels back through tunnel to Cloudflare
8. Cloudflare applies security headers and returns to client

### Image Upload/Download

1. Admin uploads image via frontend
2. POST request to `/api/images/upload` with multipart form data
3. Flask saves to local storage (outputs directory)
4. Image served via `/api/images/{id}/file` or `/api/images/{id}/thumbnail`
5. Images proxied through Cloudflare (with caching)

## Security Features

### Frontend (Firebase)
- ✅ Automatic HTTPS with strong SSL/TLS
- ✅ Security headers (X-Frame-Options, CSP, HSTS)
- ✅ DDoS protection via Google Cloud
- ✅ No sensitive data in client code

### API (Cloudflare + Flask)
- ✅ Backend not publicly accessible (no open ports)
- ✅ Cloudflare WAF and rate limiting
- ✅ CORS restricted to Firebase Hosting origins
- ✅ Input validation on all endpoints
- ✅ Session-based authentication with HTTP-only cookies
- ✅ Google OAuth for admin access

## Performance Optimizations

### Frontend
- Code splitting (vendor chunks, route-based chunks)
- Tree shaking (unused code eliminated)
- Minification and compression (Brotli/Gzip)
- CDN edge caching (global distribution)
- Lazy loading of images and components

### Backend
- Gunicorn with 2 workers (concurrent request handling)
- GPU acceleration for image generation (CUDA)
- Attention slicing to reduce VRAM usage
- FP16 precision for faster inference
- Persistent model loading (no reload per request)

## Monitoring and Logging

### Backend Logs
- **Access Log:** `/var/log/imagineer/access.log`
- **Error Log:** `/var/log/imagineer/error.log`
- **Systemd Journal:** `journalctl -u imagineer-api`

### Tunnel Logs
- **Systemd Journal:** `journalctl -u cloudflared-imagineer-api`

### Frontend Monitoring
- Firebase Hosting usage dashboard
- Performance metrics in Firebase Console
- Error tracking (if configured)

### Health Checks

```bash
# Backend API
curl http://localhost:10050/api/health
curl https://imagineer-api.joshwentworth.com/api/health

# Frontend
curl https://imagineer-generator.web.app/

# Tunnel Status
sudo systemctl status cloudflared-imagineer-api
cloudflared tunnel info imagineer-api
```

## Deployment Workflow

### Frontend Deployment

```bash
# 1. Build production bundle
cd web
npm run build

# 2. Test build locally (optional)
firebase serve

# 3. Deploy to Firebase Hosting
firebase deploy --only hosting

# 4. Verify deployment
curl https://imagineer-generator.web.app/
```

### Backend Deployment

```bash
# 1. Pull latest code
cd /home/jdubz/Development/imagineer
git pull origin develop

# 2. Update dependencies (if needed)
source venv/bin/activate
pip install -r requirements.txt

# 3. Restart API service
sudo systemctl restart imagineer-api

# 4. Check status
sudo systemctl status imagineer-api
sudo journalctl -u imagineer-api -n 50

# 5. Test API
curl http://localhost:10050/api/health
```

### Tunnel Maintenance

```bash
# Update cloudflared (if needed)
sudo cloudflared update

# Restart tunnel
sudo systemctl restart cloudflared-imagineer-api

# Verify tunnel is connected
cloudflared tunnel info imagineer-api
```

## Troubleshooting

### Frontend Not Loading

```bash
# Check Firebase deployment status
firebase hosting:channel:list

# Check for deployment errors
firebase deploy --only hosting --debug

# Verify DNS
dig imagineer-generator.web.app
```

### API Not Accessible

```bash
# Check backend service
sudo systemctl status imagineer-api
sudo journalctl -u imagineer-api -n 50

# Check local API
curl http://localhost:10050/api/health

# Check tunnel
sudo systemctl status cloudflared-imagineer-api
cloudflared tunnel info imagineer-api

# Check public API
curl https://imagineer-api.joshwentworth.com/api/health
```

### 502 Bad Gateway

- Backend service is down → Restart imagineer-api
- Backend crashed → Check logs at `/var/log/imagineer/error.log`
- Tunnel disconnected → Restart cloudflared-imagineer-api

### CORS Errors

- Check `ALLOWED_ORIGINS` in backend `.env`
- Should include: `https://imagineer-generator.web.app,https://imagineer-generator.firebaseapp.com`
- Restart backend after changing environment variables

## Migration Notes

### What Changed (2025-11-03)

1. ✅ **Removed** `static_folder` and `static_url_path` from Flask app
2. ✅ **Changed** root `/` endpoint from serving HTML to returning JSON
3. ✅ **Removed** public directory serving from Flask
4. ✅ **Updated** CLAUDE.md with deployment architecture
5. ✅ **Documented** nginx as deprecated (not used in production)

### What Stayed the Same

- ✅ Cloudflare Tunnel configuration (no changes needed)
- ✅ Firebase Hosting configuration (no changes needed)
- ✅ API endpoints and routes (all /api/* paths unchanged)
- ✅ Environment variables (no changes needed)
- ✅ Database schema and storage paths

## Future Improvements

### Potential Enhancements
- [ ] Add Redis for rate limiting (currently in-memory)
- [ ] PostgreSQL for production database
- [ ] Implement API authentication/authorization
- [ ] Add Sentry or error tracking
- [ ] Set up CI/CD with GitHub Actions
- [ ] Add automated tests
- [ ] Implement API versioning
- [ ] Add WebSocket support for real-time updates

### Nginx Removal
- [ ] Disable nginx service: `sudo systemctl stop nginx`
- [ ] Disable autostart: `sudo systemctl disable nginx`
- [ ] Remove config: `sudo rm /etc/nginx/sites-enabled/imagineer`
- [ ] (Optional) Uninstall nginx if not used for other projects

## Related Documentation

- [Firebase Cloudflare Deployment Plan](./FIREBASE_CLOUDFLARE_DEPLOYMENT.md)
- [Cloudflare Tunnel Setup](./CLOUDFLARE_TUNNEL_SETUP.md)
- [Production Deployment Guide](./PRODUCTION_DEPLOYMENT_GUIDE.md)
- [Main Architecture Doc](../ARCHITECTURE.md)
- [CLAUDE.md](../../CLAUDE.md)

## Quick Reference

```bash
# === PRODUCTION SERVICES ===

# Backend API
sudo systemctl status imagineer-api
sudo systemctl restart imagineer-api
sudo journalctl -u imagineer-api -f

# Cloudflare Tunnel
sudo systemctl status cloudflared-imagineer-api
sudo systemctl restart cloudflared-imagineer-api
sudo journalctl -u cloudflared-imagineer-api -f

# === DEPLOYMENTS ===

# Frontend (Firebase)
cd web && npm run build
firebase deploy --only hosting

# Backend (Git Pull + Restart)
git pull origin develop
sudo systemctl restart imagineer-api

# === HEALTH CHECKS ===

# Local API
curl http://localhost:10050/api/health

# Public API
curl https://imagineer-api.joshwentworth.com/api/health

# Frontend
curl https://imagineer-generator.web.app/

# Tunnel Info
cloudflared tunnel info imagineer-api

# === LOGS ===

tail -f /var/log/imagineer/error.log
tail -f /var/log/imagineer/access.log
sudo journalctl -u imagineer-api -f
sudo journalctl -u cloudflared-imagineer-api -f
```

---

**Document Version:** 1.0
**Author:** Claude Code
**Last Review:** 2025-11-03
