# API Routing Fix - Quick Checklist

## Problem
API calls return HTML instead of JSON because `imagineer.joshwentworth.com` points to Firebase Hosting instead of Cloudflare Tunnel.

## Solution Overview
Remove domain from Firebase, point DNS to Cloudflare Tunnel, update frontend config, redeploy.

---

## Step-by-Step Fix

### ☐ Step 1: Remove Firebase Custom Domain (5 minutes)

**Who**: Person with Firebase Console access
**Where**: https://console.firebase.google.com/project/static-sites-257923/hosting/sites

1. Select `imagineer-generator` site
2. Click "Custom domains" tab
3. Find `imagineer.joshwentworth.com`
4. Click three dots → "Remove domain"
5. Confirm removal
6. ✅ Domain removed from Firebase

**Verify**:
```bash
# Wait 2 minutes, then check headers:
curl -I https://imagineer.joshwentworth.com/

# Should eventually stop serving Firebase content
```

---

### ☐ Step 2: Update Cloudflare DNS (5 minutes)

**Who**: Person with Cloudflare Dashboard access
**Where**: https://dash.cloudflare.com/

1. Select `joshwentworth.com` zone
2. Go to "DNS" → "Records"
3. Find `imagineer` record (or create if missing)
4. Update/Create:
   - **Type**: CNAME
   - **Name**: imagineer
   - **Target**: `db1a99dd-3d12-4315-b241-da2a55a5c30f.cfargotunnel.com`
   - **Proxy status**: ✅ Enabled (orange cloud)
   - **TTL**: Auto
5. Click "Save"
6. ✅ DNS updated

**Verify**:
```bash
# Check DNS propagation:
dig imagineer.joshwentworth.com

# Look for CNAME to .cfargotunnel.com
```

---

### ☐ Step 3: Get Server IP Address

**Problem**: SSH to `imagineer.joshwentworth.com` times out because domain points to Cloudflare.

**Solution**: Get actual server IP

**Option A - From Cloudflare**:
1. Cloudflare Dashboard → `joshwentworth.com` zone
2. Look for origin server IP in other records
3. Or check "Analytics" → "Traffic" for origin IP

**Option B - From Hosting Provider**:
- Check AWS/GCP/DigitalOcean/Linode dashboard
- Look for instance with hostname "imagineer"

**Option C - From Another Domain**:
```bash
# If you have another domain pointing to same server:
dig other-domain.joshwentworth.com
```

**Record the IP**: `__________________`

---

### ☐ Step 4: Fix Server Configuration (10 minutes)

**Who**: Person with SSH access
**What**: Run automated fix script on server

```bash
# SSH using IP address (not domain!)
ssh jdubz@<SERVER_IP_FROM_STEP_3>

# Navigate to app directory
cd /home/jdubz/Development/imagineer

# Pull latest changes (includes fix script)
git pull origin main  # or develop, depending on branch

# Make script executable
chmod +x scripts/deploy/fix-api-routing.sh

# Run the fix script
bash scripts/deploy/fix-api-routing.sh
```

**Script will**:
- Backup current tunnel config
- Install correct tunnel configuration
- Restart Flask API service
- Restart Cloudflare Tunnel service
- Verify both services are healthy
- Show you the results

**Expected output**:
```
[2025-10-31 ...] Starting API routing fix...
[2025-10-31 ...] Backing up current tunnel configuration...
[2025-10-31 ...] Creating correct tunnel configuration...
[2025-10-31 ...] Restarting Flask API service...
[2025-10-31 ...] Flask API is healthy!
[2025-10-31 ...] Restarting Cloudflare Tunnel service...
[2025-10-31 ...] API routing fix completed!
```

**Verify**:
```bash
# Still on server, check services:
sudo systemctl status imagineer-api
sudo systemctl status cloudflared-imagineer-api

# Both should show: "active (running)"

# Test API locally:
curl http://localhost:10050/api/health

# Should return: {"status":"ok", ...}
```

✅ Server configuration updated

---

### ☐ Step 5: Test API Endpoint (2 minutes)

**Who**: Anyone
**What**: Verify API is accessible via public domain

```bash
# Wait 1-2 minutes for DNS propagation
sleep 120

# Test API endpoint (should return JSON, NOT HTML)
curl https://imagineer.joshwentworth.com/api/health
```

**Expected response**:
```json
{"status":"ok","timestamp":"2025-10-31T..."}
```

**Wrong response (means DNS not updated yet)**:
```html
<!DOCTYPE html>
<html lang="en">
...
```

If you still get HTML:
- Wait another 5 minutes for DNS propagation
- Clear your DNS cache: `sudo systemd-resolve --flush-caches`
- Try again

✅ API endpoint returns JSON

---

### ☐ Step 6: Update Frontend Configuration (2 minutes)

**Who**: Developer with repo access
**What**: Update API URL in frontend

```bash
# On your development machine
cd /home/jdubz/Development/imagineer

# Edit production environment file
vim web/.env.production
```

**Change this line**:
```bash
# FROM:
VITE_API_BASE_URL=https://imagineer-api.joshwentworth.com/api

# TO:
VITE_API_BASE_URL=https://imagineer.joshwentworth.com/api
```

**Save and commit**:
```bash
git add web/.env.production
git commit -m "fix: update API URL to working domain"
```

✅ Frontend configuration updated

---

### ☐ Step 7: Redeploy Frontend (5 minutes)

**Who**: Person with Firebase deployment access
**What**: Build and deploy updated frontend

```bash
cd /home/jdubz/Development/imagineer/web

# Install dependencies (if needed)
npm ci

# Build production bundle with new API URL
npm run deploy:build

# Deploy to Firebase Hosting
firebase deploy --only hosting --project static-sites-257923
```

**Expected output**:
```
✔ Deploy complete!

Project Console: https://console.firebase.google.com/project/static-sites-257923/overview
Hosting URL: https://imagineer-generator.web.app
```

✅ Frontend deployed

---

### ☐ Step 8: End-to-End Testing (5 minutes)

**Who**: Anyone
**What**: Verify everything works

#### Test 1: Frontend Loads
```bash
curl https://imagineer-generator.web.app/ | grep "<title>"

# Expected: <title>Imagineer - AI Image Generation</title>
```
✅ Frontend loads

#### Test 2: API Returns JSON
```bash
curl https://imagineer.joshwentworth.com/api/health

# Expected: {"status":"ok", ...}
```
✅ API returns JSON

#### Test 3: API Sets List
```bash
curl https://imagineer.joshwentworth.com/api/sets

# Expected: JSON array of available sets
```
✅ API endpoints work

#### Test 4: Browser Console
1. Open https://imagineer-generator.web.app in Chrome/Firefox
2. Open DevTools (F12)
3. Go to Console tab
4. Check for errors

**Should NOT see**:
- CORS errors
- Failed to fetch
- Network errors for `/api/*`

✅ No console errors

#### Test 5: Try Generating an Image
1. Log in with Google OAuth
2. Select a set (e.g., "Playing Cards")
3. Click "Generate Batch"
4. Watch queue tab

**Should see**:
- Job appears in queue
- Status updates
- Eventually completes

✅ Image generation works

---

## Rollback Plan (If Something Goes Wrong)

### Rollback Step 1: Restore Tunnel Config
```bash
ssh jdubz@<SERVER_IP>
cd ~/.cloudflared

# Find backup
ls -lt config.yml.backup.*

# Restore latest backup
cp config.yml.backup.YYYYMMDD_HHMMSS config.yml

# Restart tunnel
sudo systemctl restart cloudflared-imagineer-api
```

### Rollback Step 2: Restore DNS
1. Cloudflare Dashboard → joshwentworth.com → DNS
2. Change `imagineer` CNAME back to Firebase or pause record
3. Save

### Rollback Step 3: Re-add to Firebase
1. Firebase Console → Hosting → Custom domains
2. Add `imagineer.joshwentworth.com`
3. Follow verification steps

### Rollback Step 4: Restore Frontend Config
```bash
cd /home/jdubz/Development/imagineer
git checkout HEAD~1 web/.env.production
cd web
npm run deploy:build
firebase deploy --only hosting
```

---

## Success Criteria

All boxes checked:
- ✅ Firebase custom domain removed
- ✅ Cloudflare DNS updated to tunnel
- ✅ Server tunnel config fixed
- ✅ API endpoint returns JSON (not HTML)
- ✅ Frontend config updated
- ✅ Frontend redeployed
- ✅ No console errors in browser
- ✅ Can generate images end-to-end

---

## Common Issues

### Issue: "DNS still points to Firebase"
**Solution**: Wait longer (up to 10 minutes), clear DNS cache

### Issue: "API returns 502 Bad Gateway"
**Solution**: Check Flask service is running:
```bash
ssh jdubz@<SERVER_IP>
sudo systemctl status imagineer-api
sudo journalctl -u imagineer-api -n 50
```

### Issue: "API returns 404 Not Found"
**Solution**: Check tunnel routing:
```bash
ssh jdubz@<SERVER_IP>
cat ~/.cloudflared/config.yml
sudo systemctl restart cloudflared-imagineer-api
```

### Issue: "CORS errors in browser"
**Solution**: Check backend ALLOWED_ORIGINS:
```bash
ssh jdubz@<SERVER_IP>
cd /home/jdubz/Development/imagineer
cat .env.production | grep ALLOWED_ORIGINS

# Should include Firebase URLs:
# ALLOWED_ORIGINS=https://imagineer-generator.web.app,https://imagineer-generator.firebaseapp.com
```

---

## Help & Support

**Documentation**:
- Full details: `docs/deployment/PRODUCTION_ARCHITECTURE.md`
- Investigation: `docs/deployment/API_ROUTING_FIX_SUMMARY.md`

**Logs**:
```bash
# API logs
ssh jdubz@<SERVER_IP>
sudo journalctl -u imagineer-api -f

# Tunnel logs
sudo journalctl -u cloudflared-imagineer-api -f

# Both together
sudo journalctl -u imagineer-api -u cloudflared-imagineer-api -f
```

**Test Commands**:
```bash
# API health
curl https://imagineer.joshwentworth.com/api/health

# DNS check
dig imagineer.joshwentworth.com

# SSL check
curl -vI https://imagineer.joshwentworth.com/ 2>&1 | grep -i server
```

---

**Estimated Total Time**: 30-40 minutes (including DNS propagation wait times)

**Last Updated**: 2025-10-31
