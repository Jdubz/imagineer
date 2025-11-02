# Infrastructure Verification Checklist

Use this checklist to verify the production infrastructure is correctly configured.

## DNS Verification

### Frontend Domain (imagineer.joshwentworth.com)
```bash
dig imagineer.joshwentworth.com
```
**Expected:** Should resolve to Cloudflare IPs pointing to Firebase

```bash
curl -I https://imagineer.joshwentworth.com/
```
**Expected:**
- Status: `200 OK`
- Content-Type: `text/html`
- Server headers showing Cloudflare/Firebase

### API Domain (imagineer-api.joshwentworth.com)
```bash
dig imagineer-api.joshwentworth.com
```
**Expected:** Should resolve to Cloudflare Tunnel address (`*.cfargotunnel.com`)

```bash
curl https://imagineer-api.joshwentworth.com/api/health
```
**Expected:**
```json
{
  "status": "healthy",
  "timestamp": "...",
  "version": "..."
}
```

## Cloudflare Configuration

### Tunnel Status
```bash
# On the server
sudo systemctl status cloudflared
```
**Expected:** `active (running)`

Check tunnel configuration:
```bash
cat /home/jdubz/.cloudflared/config.yml
```
**Expected:**
```yaml
tunnel: db1a99dd-3d12-4315-b241-da2a55a5c30f
ingress:
  - hostname: imagineer-api.joshwentworth.com
    service: http://localhost:10050
  - service: http_status:404
```

### Cloudflare Dashboard Verification
1. Login to Cloudflare Dashboard
2. Select domain: `joshwentworth.com`
3. Check DNS records:
   - `imagineer` CNAME → `imagineer-generator.web.app` (Proxied ☁️)
   - `imagineer-api` CNAME → `db1a99dd-3d12-4315-b241-da2a55a5c30f.cfargotunnel.com` (DNS only)

## Firebase Configuration

### Hosting Site
```bash
firebase hosting:sites:list
```
**Expected:** Should show `imagineer-generator` site

### Custom Domain
Check in Firebase Console:
1. Go to Hosting section
2. Select `imagineer-generator` site
3. Verify custom domain: `imagineer.joshwentworth.com`
4. Status should be "Connected"

### Test Firebase Direct URLs
```bash
curl -I https://imagineer-generator.web.app/
curl -I https://imagineer-generator.firebaseapp.com/
```
**Expected:** Both should return `200 OK` with HTML

## Frontend Configuration

### Check Build Configuration
```bash
cat web/.env.production | grep VITE_API_BASE_URL
```
**Expected:** `VITE_API_BASE_URL=https://imagineer-api.joshwentworth.com/api`

### Verify Built Files
After building:
```bash
grep -r "imagineer-api.joshwentworth.com" public/assets/*.js
```
**Expected:** Should find the API URL in bundled JavaScript

## Backend Configuration

### Flask API Status
```bash
# On the server
sudo systemctl status imagineer-api
```
**Expected:** `active (running)`

### Local API Health
```bash
# On the server
curl http://localhost:10050/api/health
```
**Expected:** JSON response with status "healthy"

### CORS Configuration
```bash
# Check environment variables
cat /home/jdubz/imagineer/.env.production | grep ALLOWED_ORIGINS
```
**Expected:** Should include all frontend domains:
```
ALLOWED_ORIGINS=https://imagineer.joshwentworth.com,https://imagineer-generator.web.app,https://imagineer-generator.firebaseapp.com
```

## End-to-End Testing

### 1. Frontend Loads
1. Open browser: https://imagineer.joshwentworth.com
2. **Expected:** React app loads, no console errors

### 2. API Connectivity
1. Open browser console
2. Check Network tab
3. **Expected:** API requests to `https://imagineer-api.joshwentworth.com/api/*` succeed

### 3. Authentication Flow
1. Click "Login" on frontend
2. Should redirect to Google OAuth
3. After auth, should redirect back to app
4. **Expected:** User logged in successfully

### 4. API Functionality
Test a simple API endpoint:
```bash
curl https://imagineer-api.joshwentworth.com/api/database/stats
```
**Expected:** JSON response with database statistics

## Common Issues

### Issue: Frontend loads but API calls fail
**Check:**
1. Cloudflare tunnel is running: `sudo systemctl status cloudflared`
2. Flask API is running: `sudo systemctl status imagineer-api`
3. DNS resolves correctly: `dig imagineer-api.joshwentworth.com`

### Issue: CORS errors in browser
**Check:**
1. Backend ALLOWED_ORIGINS includes frontend domain
2. Frontend is using correct API URL
3. Both domains use HTTPS

### Issue: OAuth redirect fails
**Check:**
1. Google Cloud Console has correct redirect URI: `https://imagineer-api.joshwentworth.com/api/auth/google/callback`
2. Backend environment variables set correctly
3. Session cookies working (HTTPS required)

### Issue: DNS not resolving
**Check:**
1. Cloudflare DNS records exist and are correct
2. DNS propagation may take time (use `dig @1.1.1.1` to check Cloudflare directly)
3. Clear local DNS cache

## Quick Test Script

Save as `test-infra.sh`:
```bash
#!/bin/bash

echo "=== Testing Infrastructure ==="
echo

echo "1. Testing Frontend (imagineer.joshwentworth.com)..."
if curl -sf -o /dev/null https://imagineer.joshwentworth.com/; then
    echo "✅ Frontend accessible"
else
    echo "❌ Frontend not accessible"
fi

echo

echo "2. Testing API Health (imagineer-api.joshwentworth.com)..."
if curl -sf https://imagineer-api.joshwentworth.com/api/health | grep -q "healthy"; then
    echo "✅ API healthy"
else
    echo "❌ API not healthy"
fi

echo

echo "3. Testing API Stats Endpoint..."
if curl -sf https://imagineer-api.joshwentworth.com/api/database/stats | grep -q "images"; then
    echo "✅ API endpoint working"
else
    echo "❌ API endpoint not working"
fi

echo

echo "4. Checking DNS Resolution..."
if dig +short imagineer-api.joshwentworth.com | grep -q ".cfargotunnel.com"; then
    echo "✅ DNS points to Cloudflare Tunnel"
else
    echo "❌ DNS not pointing to tunnel"
fi

echo
echo "=== Test Complete ==="
```

Run with: `bash test-infra.sh`

## Manual Verification Steps

1. ✅ Frontend loads at `https://imagineer.joshwentworth.com`
2. ✅ API responds at `https://imagineer-api.joshwentworth.com/api/health`
3. ✅ Cloudflare tunnel is running
4. ✅ Flask API is running
5. ✅ DNS records are correct
6. ✅ CORS allows frontend domain
7. ✅ Google OAuth redirect URI configured
8. ✅ Frontend built with correct API URL
9. ✅ No console errors when using the app
10. ✅ Can successfully generate images

## Service Restart (If Needed)

If verification fails, try restarting services:

```bash
# On the server
sudo systemctl restart imagineer-api
sudo systemctl restart cloudflared

# Wait 10 seconds
sleep 10

# Test again
curl https://imagineer-api.joshwentworth.com/api/health
```
