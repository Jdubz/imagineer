# Production Fixes - October 27, 2025

## Issues Identified

1. **vite.svg 404** - Missing favicon file
2. **OAuth callback using http://** - Need HTTPS in production
3. **Thumbnail endpoints returning 500** - Server-side errors

## Fixes Applied

### 1. OAuth HTTPS Fix
**File:** `server/api.py`
- Added `ProxyFix` middleware to trust reverse proxy headers
- Set `PREFERRED_URL_SCHEME = "https"` in production
- This ensures OAuth callback URLs use `https://` instead of `http://`

**Action Required:**
- Update Google OAuth authorized redirect URIs to:
  - `https://imagineer-api.joshwentworth.com/api/auth/google/callback`

### 2. Missing Favicon Fix
**Files:**
- Created `web/public/vite.svg`
- Rebuilt frontend to copy favicon to build output

**Action Required:**
- Deploy the updated build to production

### 3. Thumbnail Diagnostics
**File:** `scripts/diagnose_thumbnails.py`
- Diagnostic script to identify thumbnail generation issues

## Deployment Steps

### Step 1: Deploy Code Updates

```bash
# Commit the changes
git add server/api.py web/public/vite.svg public/vite.svg \
        .env.example .env.production.example scripts/diagnose_thumbnails.py
git commit -m "fix: Add HTTPS support for OAuth and fix missing favicon

- Add ProxyFix middleware for HTTPS detection behind reverse proxy
- Create missing vite.svg favicon
- Update environment examples with correct HTTPS callback URLs
- Add thumbnail diagnostics script

Fixes:
- OAuth callback now uses https:// in production
- vite.svg 404 error resolved
- Added diagnostics for thumbnail 500 errors"

git push origin develop
```

### Step 2: Run Diagnostics on Production

SSH into your production server and run:

```bash
cd /path/to/imagineer
source venv/bin/activate
python3 scripts/diagnose_thumbnails.py
```

This will check:
- Config file and paths
- Outputs directory existence and permissions
- Thumbnails directory creation
- Database connectivity
- Sample image file accessibility

### Step 3: Fix Common Issues

Based on diagnostics output:

**If outputs directory doesn't exist:**
```bash
sudo mkdir -p /mnt/speedy/imagineer/outputs/thumbnails
sudo chown -R www-data:www-data /mnt/speedy/imagineer/outputs
sudo chmod -R 755 /mnt/speedy/imagineer/outputs
```

**If permission denied:**
```bash
# Check current owner
ls -la /mnt/speedy/imagineer/

# Fix permissions (replace user with your Flask user)
sudo chown -R flask-user:flask-user /mnt/speedy/imagineer/outputs
sudo chmod -R 755 /mnt/speedy/imagineer/outputs
```

**If path doesn't exist on production:**
Check if the production config uses a different path. Update `config.yaml` on production:

```yaml
outputs:
  base_dir: /correct/path/to/outputs
```

### Step 4: Restart Production Server

```bash
# If using systemd
sudo systemctl restart imagineer

# If using Docker
docker-compose restart

# If running directly
pkill -f "python.*server/api.py"
python server/api.py
```

### Step 5: Verify Fixes

1. **Check OAuth:**
   - Visit `https://imagineer.joshwentworth.com`
   - Click Login
   - Should redirect to Google OAuth with HTTPS callback URL

2. **Check Favicon:**
   - Open browser DevTools Network tab
   - Refresh page
   - `/vite.svg` should return 200 OK

3. **Check Thumbnails:**
   - Navigate to images page
   - Thumbnails should load without 500 errors
   - Check `/api/images/105/thumbnail` specifically

## Verification Checklist

- [ ] Code deployed to production
- [ ] Diagnostics script executed
- [ ] Output/thumbnail directories exist with correct permissions
- [ ] Production server restarted
- [ ] OAuth uses HTTPS callback
- [ ] Google OAuth credentials updated with HTTPS URL
- [ ] vite.svg returns 200
- [ ] Thumbnails load without 500 errors
- [ ] Production logs show no errors

## Rollback Plan

If issues persist:

```bash
# Revert to previous commit
git revert HEAD
git push origin develop

# Restart server
sudo systemctl restart imagineer
```

## Additional Notes

### ProxyFix Configuration

The ProxyFix middleware trusts these headers from your reverse proxy:
- `X-Forwarded-For` (client IP)
- `X-Forwarded-Proto` (http/https)
- `X-Forwarded-Host` (original host)
- `X-Forwarded-Prefix` (path prefix)

Make sure your reverse proxy (Cloudflare Tunnel/nginx) is sending these headers.

### Thumbnail Performance

If thumbnails are slow to generate, consider pre-generating them:

```bash
# Add this to your deployment script
python3 -c "
from server.database import Image, db, init_database
from flask import Flask
from pathlib import Path
from PIL import Image as PILImage
import yaml

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/imagineer.db'
init_database(app)

with open('config.yaml') as f:
    config = yaml.safe_load(f)

outputs_dir = Path(config['outputs']['base_dir'])
thumbnail_dir = outputs_dir / 'thumbnails'
thumbnail_dir.mkdir(parents=True, exist_ok=True)

with app.app_context():
    images = Image.query.filter_by(is_public=True).all()
    for img in images:
        thumbnail_path = thumbnail_dir / f'{img.id}.webp'
        if not thumbnail_path.exists():
            image_path = outputs_dir / img.file_path
            if image_path.exists():
                with PILImage.open(image_path) as pil_img:
                    pil_img.thumbnail((300, 300))
                    pil_img.save(thumbnail_path, 'WEBP', quality=85)
                print(f'Generated thumbnail for image {img.id}')
"
```
