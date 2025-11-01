# Firebase Hosting + Cloudflare Deployment Plan

**Status:** Planning Phase - Not Yet Implemented
**Last Updated:** 2025-10-13

## Overview

This document outlines a comprehensive plan for deploying the Imagineer frontend to Firebase Hosting and securing the backend API through Cloudflare Tunnel, enabling global distribution, enhanced security, and rapid iteration capabilities.

## Current Architecture

```
┌─────────────────────────────────────────┐
│    Local Development Server             │
│    Port 10050 (0.0.0.0)                 │
│                                          │
│  ┌──────────────┐  ┌─────────────────┐ │
│  │   React      │  │   Flask API     │ │
│  │   Frontend   │  │   Backend       │ │
│  │   (Vite)     │  │   (Port 10050)  │ │
│  └──────────────┘  └─────────────────┘ │
│                                          │
│  CORS: Enabled (all origins)            │
│  Auth: None                              │
│  SSL: No                                 │
└─────────────────────────────────────────┘
```

**Limitations:**
- Frontend and backend tightly coupled on same server
- No CDN distribution for frontend
- Backend exposed on local network
- No DDoS protection or rate limiting
- No SSL/HTTPS
- Manual deployment process
- Single point of failure

## Target Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        INTERNET                                 │
└────────────────────────────────────────────────────────────────┘
                              │
                              │
          ┌───────────────────┴───────────────────┐
          │                                        │
          ▼                                        ▼
┌─────────────────────┐              ┌──────────────────────────┐
│  Firebase Hosting   │              │   Cloudflare Edge        │
│  (Global CDN)       │              │   (DDoS Protection)      │
│                     │              │                          │
│  • React Frontend   │              │  • WAF Rules             │
│  • Static Assets    │              │  • Rate Limiting         │
│  • SPA Routing      │◄─────API─────│  • SSL/TLS               │
│  • Gzip/Brotli     │   Proxies    │  • Caching               │
└─────────────────────┘              └──────────────────────────┘
                                                  │
                                                  │ Tunnel
                                                  │ (Encrypted)
                                                  │
                                     ┌────────────▼─────────────┐
                                     │  Your Server             │
                                     │  (localhost:10050)       │
                                     │                          │
                                     │  ┌───────────────────┐  │
                                     │  │  Flask API        │  │
                                     │  │  + Security       │  │
                                     │  │  + Rate Limiting  │  │
                                     │  │  + Logging        │  │
                                     │  └───────────────────┘  │
                                     │                          │
                                     │  Systemd Service         │
                                     │  Auto-restart            │
                                     └──────────────────────────┘
```

## Implementation Plan

### Phase 1: Backend Security & Stability

#### 1.1 Add Security Dependencies
**File:** `requirements.txt`
```txt
# Add these dependencies
Flask-Limiter>=3.5.0      # Rate limiting
python-dotenv>=1.0.0      # Environment variables
gunicorn>=21.2.0          # Production WSGI server
```

#### 1.2 Create Environment Configuration
**File:** `.env.example` (update)
```bash
# Environment (development, production)
FLASK_ENV=development

# API Configuration
FLASK_RUN_PORT=10050
FLASK_DEBUG=False

# Security
ALLOWED_ORIGINS=https://your-app.web.app,https://your-app.firebaseapp.com
CLOUDFLARE_VERIFY=true

# Rate Limiting
RATELIMIT_STORAGE_URI=memory://
RATELIMIT_ENABLED=true

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/imagineer/api.log
```

#### 1.3 Add Cloudflare IP Verification Middleware
**File:** `server/middleware.py` (new file)
```python
"""
Security middleware for Flask API
"""
from flask import request, jsonify
from functools import wraps
import ipaddress

# Cloudflare IP ranges (update periodically from https://www.cloudflare.com/ips/)
CLOUDFLARE_IPV4_RANGES = [
    '173.245.48.0/20', '103.21.244.0/22', '103.22.200.0/22',
    '103.31.4.0/22', '141.101.64.0/18', '108.162.192.0/18',
    '190.93.240.0/20', '188.114.96.0/20', '197.234.240.0/22',
    '198.41.128.0/17', '162.158.0.0/15', '104.16.0.0/13',
    '104.24.0.0/14', '172.64.0.0/13', '131.0.72.0/22'
]

CLOUDFLARE_IPV6_RANGES = [
    '2400:cb00::/32', '2606:4700::/32', '2803:f800::/32',
    '2405:b500::/32', '2405:8100::/32', '2a06:98c0::/29',
    '2c0f:f248::/32'
]


def verify_cloudflare_ip():
    """Verify request comes from Cloudflare IP range"""
    if not os.environ.get('CLOUDFLARE_VERIFY', 'false').lower() == 'true':
        return True  # Skip verification in dev

    client_ip = request.headers.get('CF-Connecting-IP') or request.remote_addr

    try:
        ip = ipaddress.ip_address(client_ip)

        # Check IPv4 ranges
        if isinstance(ip, ipaddress.IPv4Address):
            for cidr in CLOUDFLARE_IPV4_RANGES:
                if ip in ipaddress.ip_network(cidr):
                    return True

        # Check IPv6 ranges
        if isinstance(ip, ipaddress.IPv6Address):
            for cidr in CLOUDFLARE_IPV6_RANGES:
                if ip in ipaddress.ip_network(cidr):
                    return True

        return False
    except ValueError:
        return False


def require_cloudflare(f):
    """Decorator to require requests come from Cloudflare"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not verify_cloudflare_ip():
            return jsonify({'error': 'Access denied'}), 403
        return f(*args, **kwargs)
    return decorated_function
```

#### 1.4 Update Flask API with Security
**File:** `server/api.py` (modifications)
```python
# Add imports
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import os

# Load environment variables
load_dotenv()

# Configure logging
log_level = os.environ.get('LOG_LEVEL', 'INFO')
log_file = os.environ.get('LOG_FILE', '/var/log/imagineer/api.log')

# Create logs directory if it doesn't exist
os.makedirs(os.path.dirname(log_file), exist_ok=True)

# Set up file handler with rotation
file_handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=10)
file_handler.setLevel(getattr(logging, log_level))
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))

# Configure app logger
app.logger.addHandler(file_handler)
app.logger.setLevel(getattr(logging, log_level))

# Update CORS configuration
allowed_origins = os.environ.get('ALLOWED_ORIGINS', '*').split(',')
CORS(app, origins=allowed_origins)

# Add rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per hour", "50 per minute"],
    storage_uri=os.environ.get('RATELIMIT_STORAGE_URI', 'memory://'),
    enabled=os.environ.get('RATELIMIT_ENABLED', 'true').lower() == 'true'
)

# Apply stricter limits to generation endpoints
@app.route('/api/generate', methods=['POST'])
@limiter.limit("10 per minute")
def generate():
    # existing code...

@app.route('/api/generate/batch', methods=['POST'])
@limiter.limit("5 per minute")
def generate_batch():
    # existing code...
```

#### 1.5 Create Systemd Service
**File:** `server/systemd/imagineer-api.service`
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

**Installation commands:**
```bash
# Create log directory
sudo mkdir -p /var/log/imagineer
sudo chown jdubz:jdubz /var/log/imagineer

# Install service
sudo cp server/systemd/imagineer-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable imagineer-api
sudo systemctl start imagineer-api

# Check status
sudo systemctl status imagineer-api
sudo journalctl -u imagineer-api -f
```

### Phase 2: Frontend Configuration

#### 2.1 Environment-Based API Configuration
**File:** `web/.env.development`
```bash
VITE_API_BASE_URL=http://localhost:10050/api
```

**File:** `web/.env.production`
```bash
VITE_API_BASE_URL=https://api.your-domain.com/api
```

#### 2.2 Update Vite Configuration
**File:** `web/vite.config.js`
```javascript
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    build: {
      outDir: '../public',
      emptyOutDir: true,
      sourcemap: mode === 'development',
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ['react', 'react-dom'],
            axios: ['axios']
          }
        }
      }
    },
    server: {
      port: parseInt(process.env.PORT || '10051'),
      proxy: mode === 'development' ? {
        '/api': {
          target: env.VITE_API_BASE_URL || 'http://localhost:10050',
          changeOrigin: true
        }
      } : undefined
    }
  }
})
```

#### 2.3 Create API Client with Environment Config
**File:** `web/src/utils/api.js` (new file)
```javascript
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes for long-running generations
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add request interceptor for logging in dev
if (import.meta.env.DEV) {
  apiClient.interceptors.request.use(request => {
    console.log('API Request:', request.method.toUpperCase(), request.url)
    return request
  })
}

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export default apiClient
```

#### 2.4 Update App.jsx to Use API Client
**File:** `web/src/App.jsx` (update all fetch calls)
```javascript
import apiClient from './utils/api'

// Replace all fetch('/api/...') calls with apiClient
const fetchConfig = async () => {
  try {
    const response = await apiClient.get('/config')
    setConfig(response.data)
  } catch (error) {
    console.error('Failed to fetch config:', error)
  }
}

// Apply to all other API calls...
```

### Phase 3: Firebase Hosting Setup

#### 3.1 Install Firebase CLI
```bash
npm install -g firebase-tools
firebase login
```

#### 3.2 Initialize Firebase Project
```bash
cd /home/jdubz/Development/imagineer
firebase init hosting
```

**Selections:**
- Use existing project or create new
- Public directory: `public`
- Single-page app: `Yes`
- GitHub deploys: `No` (we'll set up GitHub Actions manually)

#### 3.3 Firebase Configuration
**File:** `firebase.json`
```json
{
  "hosting": {
    "public": "public",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ],
    "headers": [
      {
        "source": "**/*.@(jpg|jpeg|gif|png|svg|webp)",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "max-age=31536000"
          }
        ]
      },
      {
        "source": "**/*.@(js|css)",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "max-age=31536000"
          }
        ]
      },
      {
        "source": "index.html",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "no-cache, no-store, must-revalidate"
          }
        ]
      },
      {
        "source": "**",
        "headers": [
          {
            "key": "X-Content-Type-Options",
            "value": "nosniff"
          },
          {
            "key": "X-Frame-Options",
            "value": "DENY"
          },
          {
            "key": "X-XSS-Protection",
            "value": "1; mode=block"
          }
        ]
      }
    ]
  }
}
```

#### 3.4 Add Custom Domain & Verify DNS
1. In the Firebase Console, go to **Hosting → Add custom domain** and enter `imagineer.joshwentworth.com`.
2. Firebase will show a TXT verification record (host + value). Copy it exactly.
3. Create that TXT record in Cloudflare with the proxy **disabled**:
   ```bash
   # Example — replace with the host/value Firebase gives you
   cloudflare dns create \
     --zone joshwentworth.com \
     --type TXT \
     --name _firebase-imagineer \
     --content "firebase=long-token-from-firebase" \
     --ttl 3600 \
     --proxied false
   ```
4. Wait until Firebase confirms domain ownership (can take several minutes).
5. After verification, Firebase will provide the routing record:
   - For `imagineer.joshwentworth.com` (a subdomain) add a **CNAME** to `ghs.googlehosted.com`, proxy **off**.
   - For an apex domain, Firebase instead gives you A/AAAA records—add each one with proxy **off**.

**File:** `.firebaserc`
```json
{
  "projects": {
    "default": "your-project-id",
    "staging": "your-project-id",
    "production": "your-project-id"
  },
  "targets": {
    "your-project-id": {
      "hosting": {
        "dev": [
          "your-project-dev"
        ],
        "prod": [
          "your-project-prod"
        ]
      }
    }
  }
}
```

#### 3.5 Build and Deploy Scripts
**File:** `package.json` (add to root)
```json
{
  "name": "imagineer",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "build:web": "cd web && npm run build",
    "deploy:dev": "npm run build:web && firebase deploy --only hosting:dev",
    "deploy:prod": "npm run build:web && firebase deploy --only hosting:prod",
    "preview": "firebase hosting:channel:deploy preview"
  }
}
```

### Phase 4: Cloudflare Tunnel Setup

#### 4.1 Install Cloudflared
```bash
# Download and install cloudflared
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Authenticate with Cloudflare
cloudflared tunnel login
```

#### 4.2 Create Tunnel
```bash
# Create a new tunnel
cloudflared tunnel create imagineer-api

# Note the tunnel ID from the output
# Save the credentials file location: ~/.cloudflared/<tunnel-id>.json
```

#### 4.3 Configure Tunnel
**File:** `cloudflare/tunnel-config.yml`
```yaml
tunnel: imagineer-api
credentials-file: /home/jdubz/.cloudflared/<tunnel-id>.json

ingress:
  # API endpoint
  - hostname: api.your-domain.com
    service: http://127.0.0.1:10050
    originRequest:
      noTLSVerify: false
      connectTimeout: 30s

  # Health check endpoint
  - hostname: api.your-domain.com
    path: /api/health
    service: http://127.0.0.1:10050

  # Catch-all rule (required)
  - service: http_status:404
```

#### 4.4 Configure DNS in Cloudflare Dashboard
```bash
# Run this command to get DNS records to add
cloudflared tunnel route dns imagineer-api api.your-domain.com
```

Or manually add in Cloudflare dashboard:
- Type: CNAME
- Name: api
- Target: <tunnel-id>.cfargotunnel.com
- Proxy: Enabled (orange cloud)

#### 4.5 Create Systemd Service for Tunnel
**File:** `cloudflare/systemd/cloudflared-imagineer.service`
```ini
[Unit]
Description=Cloudflare Tunnel for Imagineer API
After=network.target

[Service]
Type=simple
User=jdubz
ExecStart=/usr/local/bin/cloudflared tunnel --config /home/jdubz/Development/imagineer/cloudflare/tunnel-config.yml run imagineer-api
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Installation:**
```bash
sudo cp cloudflare/systemd/cloudflared-imagineer.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cloudflared-imagineer
sudo systemctl start cloudflared-imagineer
sudo systemctl status cloudflared-imagineer
```

#### 4.6 Cloudflare Firewall Rules

In Cloudflare Dashboard → Security → WAF:

**Rate Limiting Rule:**
```
Rule Name: API Rate Limit
Expression: (http.request.uri.path contains "/api/generate")
Action: Block
Duration: 1 hour
Requests: 10 requests per minute per IP
```

**Bot Protection:**
```
Rule Name: Block Bad Bots
Expression: (cf.bot_management.score lt 30)
Action: Challenge
```

### Phase 5: GitHub Actions CI/CD

#### 5.1 Create GitHub Secrets
In GitHub repository → Settings → Secrets → Actions:
- `FIREBASE_SERVICE_ACCOUNT`: Firebase service account JSON
- `FIREBASE_PROJECT_ID`: Your Firebase project ID

#### 5.2 GitHub Actions Workflow
**File:** `.github/workflows/deploy-frontend.yml`
```yaml
name: Deploy Frontend to Firebase

on:
  push:
    branches:
      - main
      - develop
    paths:
      - 'web/**'
      - '.github/workflows/deploy-frontend.yml'
  workflow_dispatch:

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: web/package-lock.json

      - name: Install dependencies
        working-directory: ./web
        run: npm ci

      - name: Run tests
        working-directory: ./web
        run: npm test -- --run

      - name: Build frontend
        working-directory: ./web
        env:
          VITE_API_BASE_URL: ${{ github.ref == 'refs/heads/main' && 'https://api.your-domain.com/api' || 'https://api-dev.your-domain.com/api' }}
        run: npm run build

      - name: Deploy to Firebase (Production)
        if: github.ref == 'refs/heads/main'
        uses: FirebaseExtended/action-hosting-deploy@v0
        with:
          repoToken: '${{ secrets.GITHUB_TOKEN }}'
          firebaseServiceAccount: '${{ secrets.FIREBASE_SERVICE_ACCOUNT }}'
          projectId: '${{ secrets.FIREBASE_PROJECT_ID }}'
          channelId: live
          target: prod

      - name: Deploy to Firebase (Staging)
        if: github.ref == 'refs/heads/develop'
        uses: FirebaseExtended/action-hosting-deploy@v0
        with:
          repoToken: '${{ secrets.GITHUB_TOKEN }}'
          firebaseServiceAccount: '${{ secrets.FIREBASE_SERVICE_ACCOUNT }}'
          projectId: '${{ secrets.FIREBASE_PROJECT_ID }}'
          channelId: live
          target: dev
```

### Phase 6: Update .gitignore

**File:** `.gitignore` (add)
```
# Firebase
.firebase/
firebase-debug.log
.firebaserc

# Cloudflare
cloudflare/tunnel-config.yml
.cloudflared/
*.json

# Environment files
.env
.env.local
.env.production
.env.development

# Logs
/var/log/imagineer/
*.log
```

## Deployment Checklist

### Pre-Deployment
- [ ] Backup current configuration
- [ ] Test all API endpoints locally
- [ ] Review security settings
- [ ] Update Cloudflare IP ranges (check https://www.cloudflare.com/ips/)

### Backend Deployment
- [ ] Install Python dependencies: `pip install -r requirements.txt`
- [ ] Create `.env` file with production values
- [ ] Test with gunicorn locally: `gunicorn server.api:app`
- [ ] Install systemd service
- [ ] Enable and start service
- [ ] Check logs: `sudo journalctl -u imagineer-api -f`

### Cloudflare Tunnel Deployment
- [ ] Install cloudflared
- [ ] Authenticate with Cloudflare
- [ ] Create tunnel
- [ ] Configure tunnel YAML
- [ ] Add DNS records
- [ ] Install tunnel systemd service
- [ ] Start tunnel and verify connectivity

### Frontend Deployment
- [ ] Install Firebase CLI: `npm install -g firebase-tools`
- [ ] Login to Firebase: `firebase login`
- [ ] Initialize Firebase project
- [ ] Update `.env.production` with API URL
- [ ] Test build locally: `cd web && npm run build`
- [ ] Deploy to staging: `npm run deploy:dev`
- [ ] Test staging thoroughly
- [ ] Deploy to production: `npm run deploy:prod`

### Post-Deployment Verification
- [ ] Test frontend loads on Firebase URL
- [ ] Verify API calls route through Cloudflare
- [ ] Check rate limiting works
- [ ] Verify Cloudflare IP check (if enabled)
- [ ] Test image generation end-to-end
- [ ] Check application logs
- [ ] Monitor error rates
- [ ] Set up uptime monitoring (e.g., UptimeRobot)

### GitHub Actions Setup
- [ ] Add Firebase service account to GitHub Secrets
- [ ] Push workflow file to repository
- [ ] Trigger test deployment
- [ ] Verify automatic deployments work

## Rollback Procedures

### Frontend Rollback
```bash
# View deployment history
firebase hosting:channel:list

# Rollback to previous version
firebase hosting:rollback

# Or deploy specific version
firebase hosting:clone <source-site> <target-site>
```

### Backend Rollback
```bash
# Stop service
sudo systemctl stop imagineer-api

# Restore previous version (from git)
git checkout <previous-commit> server/

# Restart service
sudo systemctl start imagineer-api
```

### Cloudflare Tunnel Rollback
```bash
# Stop tunnel
sudo systemctl stop cloudflared-imagineer

# Update configuration
nano cloudflare/tunnel-config.yml

# Restart tunnel
sudo systemctl start cloudflared-imagineer
```

## Monitoring and Maintenance

### Log Locations
- API logs: `/var/log/imagineer/api.log`
- API access logs: `/var/log/imagineer/access.log`
- API error logs: `/var/log/imagineer/error.log`
- Systemd logs: `journalctl -u imagineer-api`
- Cloudflare tunnel logs: `journalctl -u cloudflared-imagineer`

### Health Checks
```bash
# Check API health
curl https://api.your-domain.com/api/health

# Check services
sudo systemctl status imagineer-api
sudo systemctl status cloudflared-imagineer

# Check logs for errors
sudo journalctl -u imagineer-api --since "1 hour ago" | grep ERROR
```

### Performance Monitoring
- Cloudflare Analytics dashboard
- Firebase Hosting usage and performance
- API response times in logs
- GPU utilization: `nvidia-smi`

### Regular Maintenance Tasks
- **Weekly:** Review error logs, check disk space
- **Monthly:** Update Cloudflare IP ranges, review rate limits
- **Quarterly:** Update dependencies, security audit
- **Rotate logs:** Handled automatically by RotatingFileHandler

## Security Considerations

### API Security
- ✅ Cloudflare IP verification prevents direct access
- ✅ Rate limiting prevents abuse
- ✅ CORS restricted to allowed origins
- ✅ Input validation on all endpoints
- ✅ Path traversal protection
- ⚠️ No authentication (consider adding if public-facing)

### Infrastructure Security
- ✅ Backend only accessible via Cloudflare Tunnel
- ✅ No public IP exposure
- ✅ Automatic SSL/TLS via Cloudflare
- ✅ DDoS protection via Cloudflare
- ✅ WAF rules for bot protection

### Secrets Management
- ✅ Environment variables for sensitive data
- ✅ `.env` files excluded from git
- ✅ Cloudflare credentials stored securely
- ✅ Firebase credentials in GitHub Secrets

## Cost Estimates

### Firebase Hosting (Free Tier)
- 10GB storage
- 360MB/day bandwidth
- Should cover initial usage
- Paid plan: $0.026/GB storage, $0.15/GB bandwidth

### Cloudflare (Free Tier)
- Unlimited bandwidth
- Basic DDoS protection
- Basic WAF
- Rate limiting: 10,000 requests/month (paid after)

### Your Server
- No additional hosting costs (already owned)
- Electricity cost for running server

**Total Additional Cost:** $0-5/month initially

## Benefits Summary

### Security
- 🔒 Backend not publicly accessible
- 🛡️ DDoS protection via Cloudflare
- 🚫 Rate limiting prevents abuse
- 🔐 Automatic SSL/TLS
- 🎯 IP-based access control

### Performance
- ⚡ CDN distribution for frontend
- 🌍 Global edge caching
- 📦 Optimized asset delivery
- 🔄 Reduced server load

### Reliability
- 🔄 Auto-restart on crash
- 📊 Comprehensive logging
- 🏥 Health check endpoints
- ⏮️ Easy rollback procedures

### Development
- 🚀 30-second deployments
- 🔄 Automatic CI/CD
- 🎯 Staging environment
- 🔥 Hot reload in dev

## Next Steps

When ready to implement:

1. **Start with Backend Security** (1-2 hours)
   - Add dependencies
   - Implement middleware
   - Test locally

2. **Set Up Systemd Service** (30 minutes)
   - Create service file
   - Test service

3. **Configure Frontend** (1 hour)
   - Add environment configs
   - Update API client
   - Test locally

4. **Set Up Firebase** (30 minutes)
   - Initialize project
   - Configure hosting
   - Test deploy

5. **Set Up Cloudflare Tunnel** (1-2 hours)
   - Install cloudflared
   - Create tunnel
   - Configure DNS
   - Test connectivity

6. **Set Up CI/CD** (1 hour)
   - Add GitHub secrets
   - Create workflow
   - Test deployment

**Total Estimated Time:** 5-7 hours

## References

- [Firebase Hosting Documentation](https://firebase.google.com/docs/hosting)
- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Flask-Limiter Documentation](https://flask-limiter.readthedocs.io/)
- [Cloudflare IP Ranges](https://www.cloudflare.com/ips/)
- [GitHub Actions for Firebase](https://github.com/marketplace/actions/deploy-to-firebase-hosting)

---

**Document Version:** 1.0
**Author:** Claude Code
**Last Review:** 2025-10-13
