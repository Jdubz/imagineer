# Infrastructure Summary

**Last Updated:** 2025-11-01

## Production Architecture

### Frontend
- **Primary Domain:** `https://imagineer.joshwentworth.com`
- **Hosting:** Firebase Hosting (site: `imagineer-generator`)
- **CDN/Proxy:** Cloudflare (DNS proxy enabled)
- **Direct URLs:**
  - `https://imagineer-generator.web.app`
  - `https://imagineer-generator.firebaseapp.com`

### Backend API
- **API Domain:** `https://api.imagineer.joshwentworth.com`
- **Service:** Flask (Python) running on port 10050
- **Tunnel:** Cloudflare Tunnel (`db1a99dd-3d12-4315-b241-da2a55a5c30f`)
- **Server:** Local server accessible via Cloudflare Tunnel

## DNS Configuration

### Cloudflare DNS Records

| Record Type | Name | Target | Proxy Status | Purpose |
|-------------|------|--------|--------------|---------|
| CNAME | `imagineer.joshwentworth.com` | `imagineer-generator.web.app` | Proxied (Orange Cloud) | Frontend hosting |
| CNAME | `api.imagineer.joshwentworth.com` | `db1a99dd-3d12-4315-b241-da2a55a5c30f.cfargotunnel.com` | DNS only (Grey Cloud) | API tunnel |

## Request Flow

### Frontend Request
```
User Browser
    ↓
https://imagineer.joshwentworth.com
    ↓
Cloudflare CDN (proxied)
    ↓
Firebase Hosting
    ↓
React SPA served
```

### API Request
```
Frontend (React)
    ↓
https://api.imagineer.joshwentworth.com/api/*
    ↓
Cloudflare DNS
    ↓
Cloudflare Tunnel
    ↓
Local Server (localhost:10050)
    ↓
Flask API
```

## Configuration Files

### Frontend Configuration
- **File:** `web/.env.production`
- **API URL:** `VITE_API_BASE_URL=https://api.imagineer.joshwentworth.com/api`

### Cloudflare Tunnel Configuration
- **File:** `config/deployment/cloudflared-config.yml`
- **Tunnel ID:** `db1a99dd-3d12-4315-b241-da2a55a5c30f`
- **Hostname:** `api.imagineer.joshwentworth.com`
- **Service:** `http://localhost:10050`

### Firebase Configuration
- **Files:** `firebase.json`, `.firebaserc`
- **Project:** `static-sites-257923`
- **Site:** `imagineer-generator`
- **Custom Domain:** `imagineer.joshwentworth.com` (configured in Firebase Console + Cloudflare)

## Deployment Process

### Frontend Deployment
```bash
cd web
npm run deploy:build  # Builds with VITE_API_BASE_URL from .env.production
firebase deploy --only hosting:imagineer
```

### Backend Deployment
```bash
# Restart Flask API service
sudo systemctl restart imagineer-api

# Restart Cloudflare Tunnel
sudo systemctl restart cloudflared
```

## Health Checks

### Frontend
```bash
curl -I https://imagineer.joshwentworth.com/
# Should return: 200 OK with HTML content
```

### API
```bash
curl https://api.imagineer.joshwentworth.com/api/health
# Should return: {"status": "healthy", ...}
```

## CORS Configuration

### Backend CORS Settings
The Flask API must allow requests from:
- `https://imagineer.joshwentworth.com`
- `https://imagineer-generator.web.app`
- `https://imagineer-generator.firebaseapp.com`

**Configuration:** Set in `.env.production` (backend):
```bash
ALLOWED_ORIGINS=https://imagineer.joshwentworth.com,https://imagineer-generator.web.app,https://imagineer-generator.firebaseapp.com
```

## Google OAuth Configuration

### Redirect URIs (Google Cloud Console)
The following redirect URIs must be configured in Google Cloud Console:
- `https://api.imagineer.joshwentworth.com/api/auth/google/callback`
- `http://localhost:10050/api/auth/google/callback` (development)

## Troubleshooting

### Frontend Shows But API Fails
1. Check Cloudflare Tunnel is running:
   ```bash
   sudo systemctl status cloudflared
   ```

2. Check Flask API is running:
   ```bash
   sudo systemctl status imagineer-api
   curl http://localhost:10050/api/health
   ```

3. Verify DNS resolution:
   ```bash
   dig api.imagineer.joshwentworth.com
   nslookup api.imagineer.joshwentworth.com
   ```

### CORS Errors
1. Check backend `ALLOWED_ORIGINS` environment variable
2. Verify frontend is using correct API URL
3. Check browser console for specific CORS error

### Authentication Fails
1. Verify Google OAuth redirect URI matches exactly
2. Check backend logs for OAuth errors
3. Ensure session cookies are working (check HTTPS)

## Service Management

### Start/Stop Services

#### Flask API
```bash
sudo systemctl start imagineer-api
sudo systemctl stop imagineer-api
sudo systemctl restart imagineer-api
sudo systemctl status imagineer-api
```

#### Cloudflare Tunnel
```bash
sudo systemctl start cloudflared
sudo systemctl stop cloudflared
sudo systemctl restart cloudflared
sudo systemctl status cloudflared
```

### View Logs
```bash
# API logs
sudo journalctl -u imagineer-api -f

# Tunnel logs
sudo journalctl -u cloudflared -f
```

## Security Notes

1. **Cloudflare Proxy:** Frontend domain uses Cloudflare proxy (orange cloud) for DDoS protection and CDN
2. **API Tunnel:** API domain uses Cloudflare Tunnel for secure server access without exposing ports
3. **HTTPS Only:** Both frontend and API enforce HTTPS
4. **CORS:** Strict CORS policy only allows requests from known frontend domains

## Important URLs

### Production
- Frontend: https://imagineer.joshwentworth.com
- API: https://api.imagineer.joshwentworth.com/api
- Health Check: https://api.imagineer.joshwentworth.com/api/health

### Firebase Direct (Backup)
- Frontend: https://imagineer-generator.web.app
- Frontend: https://imagineer-generator.firebaseapp.com

### Development
- Frontend: http://localhost:3000
- API: http://localhost:10050/api
- Health Check: http://localhost:10050/api/health
