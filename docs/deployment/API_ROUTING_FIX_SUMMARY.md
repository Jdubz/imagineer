# API Routing Fix Summary

## Investigation Results (2025-10-31)

### Problem Identified

**Issue**: API calls to `https://imagineer.joshwentworth.com/api/*` return HTML (React app) instead of JSON from the Flask backend.

**Root Cause**: Domain misconfiguration with multiple contributing factors:

1. **DNS Points to Firebase**: `imagineer.joshwentworth.com` was added as a custom domain in Firebase Hosting
2. **Frontend Config Mismatch**: Frontend expects API at `https://api.imagineer.joshwentworth.com/api` but this subdomain doesn't exist in DNS
3. **Cloudflare Tunnel Not Active**: Even though tunnel is configured on server, the domain isn't routing to it
4. **Documentation Drift**: Multiple deployment docs describe different architectures

### What I Found

#### DNS Configuration
```
imagineer.joshwentworth.com
  → Resolves to: 104.21.56.188, 172.67.155.138 (Cloudflare IPs)
  → Routes to: Firebase Hosting (serving React app)
  → Response: HTML for ALL paths including /api/*

api.imagineer.joshwentworth.com
  → DNS record: DOES NOT EXIST
  → Status: Never created
```

#### Services Status
```
Frontend:
  - imagineer-generator.web.app → Firebase Hosting (working)
  - imagineer.joshwentworth.com → Firebase Hosting (custom domain)

Backend:
  - Cloudflare Tunnel configured but domain not routing to it
  - Flask API presumably running on server port 10050
  - Cannot verify due to SSH timeout issues
```

#### Frontend Configuration
```bash
# web/.env.production
VITE_API_BASE_URL=https://api.imagineer.joshwentworth.com/api

# This subdomain doesn't exist, so all API calls fail!
```

### What's Broken

1. **API Calls Fail**: Frontend tries to reach `api.imagineer.joshwentworth.com` which doesn't exist
2. **Wrong Domain Usage**: `imagineer.joshwentworth.com` serves frontend instead of proxying API
3. **Architecture Mismatch**: Deployed setup doesn't match any documentation

### Test Results

#### Working Endpoints
```bash
# Frontend (Firebase) - WORKS
curl https://imagineer-generator.web.app/
→ Returns: HTML (React app)
→ Status: 200 OK

# Frontend (Custom Domain) - WORKS (but shouldn't be here)
curl https://imagineer.joshwentworth.com/
→ Returns: HTML (React app)
→ Status: 200 OK
```

#### Broken Endpoints
```bash
# API via main domain - FAILS (returns HTML instead of JSON)
curl https://imagineer.joshwentworth.com/api/health
→ Returns: HTML (React app)
→ Expected: {"status":"ok"}
→ Status: WRONG RESPONSE TYPE

# API via subdomain - FAILS (DNS doesn't exist)
curl https://api.imagineer.joshwentworth.com/api/health
→ Returns: DNS resolution error
→ Expected: {"status":"ok"}
→ Status: DOMAIN NOT FOUND
```

## The Fix (3 Options)

### Option 1: Single Domain (Simplest) ⭐ RECOMMENDED

Use `imagineer.joshwentworth.com` for API only.

**Steps:**
1. Remove `imagineer.joshwentworth.com` from Firebase Custom Domains
2. Update DNS to point to Cloudflare Tunnel
3. Configure tunnel to route `/api/*` to Flask (port 10050)
4. Update frontend to use `https://imagineer.joshwentworth.com/api`
5. Redeploy frontend to Firebase

**Result:**
- Frontend: `https://imagineer-generator.web.app` (Firebase direct)
- API: `https://imagineer.joshwentworth.com/api/*` (via Cloudflare Tunnel)

**Pros:**
- Simple configuration
- One domain for API
- Clear separation

**Cons:**
- No branded frontend URL (uses Firebase subdomain)

### Option 2: API Subdomain (Match Current Frontend)

Create `api.imagineer.joshwentworth.com` subdomain.

**Steps:**
1. Create DNS CNAME: `api.imagineer.joshwentworth.com` → tunnel
2. Update tunnel config to use `api.imagineer.joshwentworth.com`
3. Keep `imagineer.joshwentworth.com` on Firebase (optional)
4. No frontend changes needed (already configured for this)

**Result:**
- Frontend: `https://imagineer.joshwentworth.com` (Firebase, branded)
- API: `https://api.imagineer.joshwentworth.com/api/*` (via Cloudflare Tunnel)

**Pros:**
- Matches current frontend config
- Branded frontend URL
- Clean API subdomain

**Cons:**
- Requires DNS changes
- More complex setup

### Option 3: Hybrid Routing (Most Flexible)

Use single domain with path-based routing via Cloudflare Tunnel.

**Steps:**
1. Remove domain from Firebase
2. Configure tunnel to:
   - Route `/api/*` to Flask (port 10050)
   - Route `/*` to Firebase (proxy)
3. Update frontend to use `https://imagineer.joshwentworth.com/api`
4. Redeploy frontend

**Result:**
- Frontend: `https://imagineer.joshwentworth.com` (via tunnel → Firebase)
- API: `https://imagineer.joshwentworth.com/api/*` (via tunnel → Flask)

**Pros:**
- Single branded domain for everything
- Flexible routing
- Can add more services later

**Cons:**
- Most complex setup
- Tunnel becomes single point of failure
- Slight latency for frontend

## Implementation Plan

### Phase 1: Prerequisites (MANUAL STEP REQUIRED)

**Remove Firebase Custom Domain**:
1. Go to [Firebase Console](https://console.firebase.google.com/project/static-sites-257923/hosting/sites)
2. Select `imagineer-generator` site
3. Go to "Custom domains" tab
4. Remove `imagineer.joshwentworth.com`
5. Wait for DNS to propagate (2-5 minutes)

### Phase 2: Server Configuration (SSH Required)

**Run the fix script**:
```bash
ssh jdubz@<server-ip-address>  # Use IP, not domain
cd /home/jdubz/Development/imagineer
bash scripts/deploy/fix-api-routing.sh
```

The script will:
- Backup current tunnel config
- Create correct tunnel configuration
- Restart Flask API service
- Restart Cloudflare Tunnel service
- Verify both services are healthy
- Display next steps

### Phase 3: DNS Configuration (Cloudflare Dashboard)

**Update DNS Record**:
1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Select `joshwentworth.com` zone
3. Go to DNS → Records
4. Find or create record:
   - Type: `CNAME`
   - Name: `imagineer`
   - Target: `db1a99dd-3d12-4315-b241-da2a55a5c30f.cfargotunnel.com`
   - Proxy status: Enabled (orange cloud)
   - TTL: Auto
5. Save

### Phase 4: Frontend Configuration

**Update environment file**:
```bash
cd /home/jdubz/Development/imagineer
vim web/.env.production
```

Change to:
```bash
VITE_API_BASE_URL=https://imagineer.joshwentworth.com/api
```

### Phase 5: Frontend Deployment

**Redeploy to Firebase**:
```bash
cd /home/jdubz/Development/imagineer/web
npm run deploy:build
firebase deploy --only hosting --project static-sites-257923
```

### Phase 6: Testing

**Test API Endpoint**:
```bash
# Wait 1-2 minutes for DNS propagation, then:
curl https://imagineer.joshwentworth.com/api/health

# Expected response:
{"status":"ok","timestamp":"2025-10-31T..."}

# NOT HTML!
```

**Test Frontend**:
1. Open: https://imagineer-generator.web.app
2. Open browser console (F12)
3. Check for API errors (should be none)
4. Try logging in
5. Try generating an image

**Test End-to-End**:
```bash
# All these should work:
curl https://imagineer-generator.web.app/                    # HTML
curl https://imagineer.joshwentworth.com/api/health         # JSON
curl https://imagineer.joshwentworth.com/api/sets           # JSON
```

## Files Created/Modified

### New Files
1. `/home/jdubz/Development/imagineer/docs/deployment/PRODUCTION_ARCHITECTURE.md`
   - Complete architecture documentation
   - Problem analysis
   - Three fix options with pros/cons
   - Testing procedures

2. `/home/jdubz/Development/imagineer/scripts/deploy/fix-api-routing.sh`
   - Automated fix script for server
   - Updates tunnel configuration
   - Restarts services
   - Verifies health

3. `/home/jdubz/Development/imagineer/docs/deployment/API_ROUTING_FIX_SUMMARY.md`
   - This file
   - Investigation summary
   - Implementation plan

### Files to Modify
1. `web/.env.production`
   - Change API URL from `api.imagineer.joshwentworth.com` to `imagineer.joshwentworth.com`

2. `~/.cloudflared/config.yml` (on server)
   - Update tunnel routing configuration
   - Done by fix script

## SSH Access Issue

**Problem**: SSH connection to `jdubz@imagineer.joshwentworth.com` times out.

**Possible Causes**:
1. Domain resolves to Cloudflare (not server IP)
2. Cloudflare doesn't proxy SSH traffic
3. No SSH rule in tunnel configuration

**Workaround**:
```bash
# Get actual server IP from Cloudflare DNS or hosting provider
# Then SSH using IP instead of domain:
ssh jdubz@<actual-server-ip>
```

**Alternative**: If server IP is unknown:
1. Check Cloudflare dashboard for origin server IP
2. Check hosting provider (AWS/GCP/DigitalOcean/etc)
3. Ask server administrator for IP

## Troubleshooting

### API Still Returns HTML

**Possible causes**:
- Firebase custom domain not removed
- DNS still pointing to Firebase
- Tunnel not running
- Tunnel config incorrect

**Debug steps**:
```bash
# Check what DNS points to
dig imagineer.joshwentworth.com

# Should see: .cfargotunnel.com CNAME
# If not, DNS not updated yet

# Check tunnel status
ssh jdubz@<server-ip>
sudo systemctl status cloudflared-imagineer-api
sudo journalctl -u cloudflared-imagineer-api -n 50
```

### DNS Not Updating

**Cause**: DNS propagation takes time

**Solution**:
```bash
# Clear local DNS cache
sudo systemd-resolve --flush-caches

# Check specific DNS server
dig @1.1.1.1 imagineer.joshwentworth.com

# Wait 5 minutes and try again
```

### Tunnel Not Connecting

**Possible causes**:
- API service not running
- Wrong port in tunnel config
- Credentials file missing

**Debug steps**:
```bash
ssh jdubz@<server-ip>

# Check API is running
sudo systemctl status imagineer-api
curl http://localhost:10050/api/health

# Check tunnel config
cat ~/.cloudflared/config.yml

# Check tunnel credentials exist
ls -la ~/.cloudflared/*.json

# Restart tunnel with verbose logging
sudo systemctl stop cloudflared-imagineer-api
sudo cloudflared tunnel --config ~/.cloudflared/config.yml run
# Watch output for errors
```

### CORS Errors in Browser

**Cause**: Backend not allowing Firebase origin

**Solution**:
```bash
ssh jdubz@<server-ip>
cd /home/jdubz/Development/imagineer

# Check .env.production
cat .env.production | grep ALLOWED_ORIGINS

# Should include:
# ALLOWED_ORIGINS=https://imagineer-generator.web.app,https://imagineer-generator.firebaseapp.com

# If wrong, fix and restart:
vim .env.production
sudo systemctl restart imagineer-api
```

## Documentation Updates Needed

After fix is implemented, update these files:

1. **docs/deployment/PRODUCTION_DEPLOYMENT_GUIDE.md**
   - Remove nginx sections (not used for frontend)
   - Update architecture diagram
   - Correct domain references

2. **docs/deployment/CLOUDFLARE_TUNNEL_SETUP.md**
   - Fix API URL references
   - Update tunnel configuration examples
   - Clarify domain vs subdomain usage

3. **docs/deployment/DEPLOYMENT_QUICK_START.md**
   - Update with actual working URLs
   - Simplify steps

4. **web/.env.example**
   - Update production configuration example
   - Clarify domain structure

## Summary

### What Was Wrong
- `imagineer.joshwentworth.com` pointing to Firebase (frontend) instead of Cloudflare Tunnel (API)
- Frontend configured for non-existent `api.imagineer.joshwentworth.com` subdomain
- Cloudflare Tunnel configured but not receiving traffic

### What Needs to Be Fixed
1. Remove domain from Firebase Custom Domains
2. Update DNS to point to Cloudflare Tunnel
3. Update tunnel configuration (done by script)
4. Update frontend API URL
5. Redeploy frontend

### What Will Work After Fix
- Frontend: `https://imagineer-generator.web.app` (Firebase Hosting)
- API: `https://imagineer.joshwentworth.com/api/*` (via Cloudflare Tunnel → Flask)
- End-to-end: Login, generate images, view gallery

### Next Actions Required
1. **Manual**: Remove Firebase custom domain (requires Firebase Console access)
2. **Manual**: Update Cloudflare DNS (requires Cloudflare Dashboard access)
3. **Automated**: Run fix script on server (requires SSH access)
4. **Automated**: Update and redeploy frontend (can be done from dev machine)

---

**Created**: 2025-10-31
**Status**: Investigation complete, fix ready to implement
**Dependencies**: Firebase Console access, Cloudflare Dashboard access, SSH access to server
