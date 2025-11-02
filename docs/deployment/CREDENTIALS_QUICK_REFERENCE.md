# Credentials Quick Reference

## 🔑 What You Need

### 1. Cloudflare API Token
**Get it:** https://dash.cloudflare.com/profile/api-tokens
**Where:** `terraform/terraform.tfvars`
```bash
cloudflare_api_token = "your_token_here"
```
**Permissions needed:**
- Zone.DNS: Edit
- Zone.Firewall Services: Edit
- Zone: joshwentworth.com

---

### 2. Cloudflare Account (Browser Login)
**Command:** `cloudflared tunnel login`
**When:** During tunnel setup (one-time per machine)
**Creates:** `~/.cloudflared/cert.pem`

---

### 3. Firebase/Google Account
**Command:** `firebase login`
**When:** Before deploying frontend (one-time per machine)
**Project:** static-sites-257923

---

## 🔧 Configuration Files

### `.env.production` (Backend)
```bash
FLASK_ENV=production
FLASK_DEBUG=false
FLASK_RUN_PORT=10050

ALLOWED_ORIGINS=https://imagineer-generator.web.app,https://imagineer-generator.firebaseapp.com
CLOUDFLARE_VERIFY=true

WEBHOOK_SECRET=your-webhook-secret-here  # Generate: openssl rand -hex 32
GITHUB_REPO=yourusername/imagineer
DEPLOY_BRANCH=main
```

### `web/.env.production` (Frontend)
```bash
VITE_API_BASE_URL=https://imagineer-api.joshwentworth.com/api
VITE_APP_PASSWORD=[REDACTED]
```

### `terraform/terraform.tfvars` (Infrastructure)
```bash
cloudflare_api_token = "your_cloudflare_token_here"
domain = "joshwentworth.com"
api_subdomain = "imagineer"
tunnel_id = "your_tunnel_id_here"  # Filled during tunnel setup
environment = "production"
```

---

## ✅ Pre-Deployment Checklist

```bash
# 1. Copy configuration templates
cp .env.production.example .env.production
cp web/.env.production.example web/.env.production
cp terraform/terraform.tfvars.example terraform/terraform.tfvars

# 2. Get Cloudflare API token
# → https://dash.cloudflare.com/profile/api-tokens
# → Add to terraform/terraform.tfvars

# 3. Authenticate Cloudflare tunnel
cloudflared tunnel login

# 4. Authenticate Firebase
firebase login

# 5. Test authentication
bash scripts/deploy/deploy-all.sh --dry-run
```

---

## 🧪 Test Your Credentials

```bash
# Test Cloudflare API token
cd terraform && terraform validate

# Test Cloudflare tunnel auth
cloudflared tunnel list

# Test Firebase auth
firebase projects:list

# Test all together
cd .. && make deploy-all-dry-run
```

---

## 🚨 Quick Fixes

**"Invalid API Token"**
```bash
# Regenerate at: https://dash.cloudflare.com/profile/api-tokens
# Update terraform/terraform.tfvars
```

**"You need to authenticate cloudflared"**
```bash
cloudflared tunnel login
```

**"User not authenticated" (Firebase)**
```bash
firebase logout
firebase login
```

---

## 📱 GitHub Secrets (Optional - for CI/CD)

Add these at: https://github.com/yourusername/imagineer/settings/secrets/actions

| Secret Name | Value | Get From |
|-------------|-------|----------|
| `FIREBASE_SERVICE_ACCOUNT` | JSON key | Firebase Console → Settings → Service Accounts |
| `VITE_APP_PASSWORD` | `[REDACTED]` | (hardcoded value) |
| `CLOUDFLARE_API_TOKEN` | Your token | Same as terraform.tfvars |
| `CLOUDFLARE_TUNNEL_ID` | Tunnel ID | `cloudflared tunnel list` |

---

## 🔐 Security Notes

**Never commit these files:**
- `.env.production`
- `web/.env.production`
- `terraform/terraform.tfvars`
- `~/.cloudflared/cert.pem`

**They're already in .gitignore ✓**

**Store credentials in a password manager!**

---

## 📚 Full Documentation

See [docs/REQUIRED_CREDENTIALS.md](docs/REQUIRED_CREDENTIALS.md) for complete details.
