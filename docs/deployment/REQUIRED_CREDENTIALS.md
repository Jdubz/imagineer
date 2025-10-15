# Required Credentials and Authentication

Complete guide to all keys, tokens, and logins needed for Imagineer deployment.

## 🔑 Required Credentials

### 1. Cloudflare API Token

**What it's for:** Terraform needs this to manage your Cloudflare DNS, WAF rules, and rate limiting.

**How to get it:**

1. Go to https://dash.cloudflare.com/profile/api-tokens
2. Click **"Create Token"**
3. Use template: **"Edit zone DNS"**
4. Or create custom token with these permissions:
   - **Zone.DNS**: Edit
   - **Zone.Firewall Services**: Edit
   - **Zone**: Include → `joshwentworth.com`
5. Click **"Continue to summary"** → **"Create Token"**
6. **Copy the token** (you'll only see it once!)

**Where to use it:**
```bash
# Add to terraform/terraform.tfvars
cloudflare_api_token = "your-token-here"
```

**Security:**
- Never commit this to git (already in .gitignore)
- Token has zone-specific permissions (safer than global API key)
- Can be regenerated if compromised

---

### 2. Cloudflare Account (Browser Login)

**What it's for:** Authenticate `cloudflared` to create tunnels in your Cloudflare account.

**How to authenticate:**

```bash
# Run the tunnel setup script
bash scripts/deploy/setup-cloudflare-tunnel-custom.sh

# It will automatically open your browser for authentication
# Log in with your Cloudflare account credentials
```

Or manually:
```bash
cloudflared tunnel login
```

**What happens:**
- Opens browser to Cloudflare login
- Authorizes cloudflared on your machine
- Saves certificate to `~/.cloudflared/cert.pem`
- This is a **one-time setup** per machine

**Credentials:**
- Your Cloudflare account email
- Your Cloudflare account password
- (2FA if enabled)

---

### 3. Firebase / Google Account

**What it's for:** Deploy frontend to Firebase Hosting.

**How to authenticate:**

```bash
# Install Firebase CLI (if not installed)
npm install -g firebase-tools

# Login
firebase login

# Verify you're logged in
firebase projects:list
```

**What happens:**
- Opens browser for Google authentication
- You log in with your Google account
- Grants Firebase CLI access
- Saves credentials locally

**Credentials:**
- Google account email (the one with access to Firebase project `static-sites-257923`)
- Google account password

**Verify access:**
```bash
# Should show static-sites-257923 project
firebase projects:list

# Check hosting targets
firebase target:apply hosting imagineer imagineer-generator
```

---

### 4. GitHub Secrets (Optional - for CI/CD)

**What they're for:** Automated deployments via GitHub Actions.

**Required secrets:**

1. **`FIREBASE_SERVICE_ACCOUNT`**
   - For automated Firebase deployments
   - How to get:
     ```bash
     # Go to Firebase Console
     # https://console.firebase.google.com/project/static-sites-257923/settings/serviceaccounts
     # Click "Generate new private key"
     # Copy entire JSON content
     ```
   - Where to add: GitHub Settings → Secrets → Actions → New secret

2. **`VITE_APP_PASSWORD`**
   - App password: `carnuvian`
   - Where to add: GitHub Settings → Secrets → Actions → New secret
   - Value: `carnuvian`

3. **`CLOUDFLARE_API_TOKEN`**
   - Same token from step 1
   - Where to add: GitHub Settings → Secrets → Actions → New secret

4. **`CLOUDFLARE_TUNNEL_ID`**
   - Obtained during tunnel setup
   - Where to add: GitHub Settings → Secrets → Actions → New secret
   - Get it from: `cloudflared tunnel list`

**How to add GitHub Secrets:**
1. Go to https://github.com/yourusername/imagineer
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**
4. Add name and value
5. Repeat for each secret

---

### 5. Webhook Secret (Optional - for auto-deployment)

**What it's for:** Secure webhook communication from GitHub to your server for auto-deployment.

**How to generate:**

```bash
# Generate a random secret (32 characters)
openssl rand -hex 32
```

**Where to use it:**

1. **In your server (.env.production):**
   ```bash
   WEBHOOK_SECRET=your-generated-secret-here
   ```

2. **In GitHub webhook settings:**
   - Go to: https://github.com/yourusername/imagineer/settings/hooks
   - Click **"Add webhook"**
   - Payload URL: `http://your-server-ip:5001/webhook`
   - Content type: `application/json`
   - Secret: `your-generated-secret-here` (same as .env.production)
   - Events: Just the push event
   - Active: ✓

**Security:**
- Validates webhook signatures with HMAC-SHA256
- Prevents unauthorized deployment triggers
- Never commit to git (already in .gitignore)

---

## 📋 Quick Setup Checklist

Use this checklist to track your authentication setup:

### Pre-Deployment Setup

- [ ] **Cloudflare API Token** generated
  - [ ] Added to `terraform/terraform.tfvars`
  - [ ] Tested with `terraform validate`

- [ ] **Cloudflare Account** authenticated
  - [ ] Ran `cloudflared tunnel login`
  - [ ] Certificate exists at `~/.cloudflared/cert.pem`

- [ ] **Firebase/Google Account** authenticated
  - [ ] Ran `firebase login`
  - [ ] Can see project with `firebase projects:list`

### Optional CI/CD Setup

- [ ] **GitHub Secrets** configured
  - [ ] `FIREBASE_SERVICE_ACCOUNT` added
  - [ ] `VITE_APP_PASSWORD` added
  - [ ] `CLOUDFLARE_API_TOKEN` added
  - [ ] `CLOUDFLARE_TUNNEL_ID` added (after tunnel setup)

### Optional Auto-Deployment Setup

- [ ] **Webhook Secret** generated
  - [ ] Added to `.env.production`
  - [ ] Added to GitHub webhook settings
  - [ ] Webhook listener service running

---

## 🧪 Testing Authentication

### Test Cloudflare API Token

```bash
cd terraform

# Initialize (downloads providers)
terraform init

# Validate config (tests API token)
terraform validate

# Test plan (requires valid token)
terraform plan
```

**Expected:** Should connect to Cloudflare and show planned changes.
**Error:** If token is invalid, you'll see authentication errors.

### Test Cloudflare Tunnel Authentication

```bash
# List tunnels (requires authentication)
cloudflared tunnel list

# Check for certificate
ls -la ~/.cloudflared/cert.pem
```

**Expected:** Should show your tunnels (or empty list if none created yet).
**Error:** If not authenticated, will prompt you to run `cloudflared tunnel login`.

### Test Firebase Authentication

```bash
# List projects
firebase projects:list

# Should show static-sites-257923
```

**Expected:** Lists your Firebase projects including `static-sites-257923`.
**Error:** If not authenticated, will prompt you to run `firebase login`.

### Test GitHub Secrets (in CI/CD)

```bash
# Push to a test branch
git checkout -b test-deployment
git push origin test-deployment

# Check Actions tab in GitHub
# https://github.com/yourusername/imagineer/actions

# Should see workflow run without authentication errors
```

---

## 🔐 Security Best Practices

### 1. Never Commit Credentials

These files are in `.gitignore` (never commit):
- `.env.production`
- `web/.env.production`
- `terraform/terraform.tfvars`
- `~/.cloudflared/cert.pem`

### 2. Use Environment-Specific Tokens

Don't use your global Cloudflare API key. Use zone-specific API tokens with minimal permissions.

### 3. Rotate Credentials Regularly

**If compromised:**

```bash
# Regenerate Cloudflare API token
# 1. Go to https://dash.cloudflare.com/profile/api-tokens
# 2. Delete old token
# 3. Create new token
# 4. Update terraform/terraform.tfvars

# Regenerate webhook secret
openssl rand -hex 32
# Update .env.production and GitHub webhook

# Regenerate Firebase service account
# 1. Go to Firebase Console → Settings → Service Accounts
# 2. Delete old key
# 3. Generate new key
# 4. Update GitHub secret
```

### 4. Restrict Access

- Cloudflare API token: Zone-specific only
- Firebase service account: Hosting only
- GitHub secrets: Repository-specific
- Webhook secret: Strong random value

### 5. Store Securely

**On your machine:**
- Use encrypted filesystem
- Restrict file permissions: `chmod 600 .env.production`
- Use a password manager for backup

**In GitHub:**
- Use GitHub Secrets (encrypted at rest)
- Never print secrets in logs
- Never expose in workflow output

---

## 🚨 Troubleshooting Authentication Issues

### Cloudflare API Token Issues

**Error: "Invalid API Token"**
```bash
# Check token in terraform.tfvars
cat terraform/terraform.tfvars | grep cloudflare_api_token

# Verify permissions at:
# https://dash.cloudflare.com/profile/api-tokens

# Regenerate if needed
```

**Error: "Permission denied for zone"**
```bash
# Token needs "Zone.DNS: Edit" permission
# Recreate token with correct permissions
```

### Cloudflare Tunnel Authentication Issues

**Error: "You need to authenticate cloudflared"**
```bash
# Authenticate
cloudflared tunnel login

# Or run tunnel setup (does this automatically)
bash scripts/deploy/setup-cloudflare-tunnel-custom.sh
```

**Error: "Tunnel not found"**
```bash
# List tunnels to verify authentication
cloudflared tunnel list

# Create tunnel
cloudflared tunnel create imagineer-api
```

### Firebase Authentication Issues

**Error: "User not authenticated"**
```bash
# Login
firebase login

# If that fails, logout first
firebase logout
firebase login
```

**Error: "Permission denied for project"**
```bash
# Verify your Google account has access to the project
firebase projects:list

# If project not listed, you need to be added as a collaborator
# Ask project owner to add your Google account
```

**Error: "Target not found"**
```bash
# Check .firebaserc
cat .firebaserc

# Apply target
firebase target:apply hosting imagineer imagineer-generator
```

### GitHub Secrets Issues

**Error: Secrets not available in workflow**
```bash
# Check secret names match exactly (case-sensitive)
# In .github/workflows/*.yml:
secrets.FIREBASE_SERVICE_ACCOUNT  # Must match GitHub secret name

# Verify secrets exist
# Go to: GitHub → Settings → Secrets → Actions
```

**Error: "Firebase service account invalid"**
```bash
# Regenerate service account key
# 1. Firebase Console → Settings → Service Accounts
# 2. Generate new private key
# 3. Copy entire JSON
# 4. Update GitHub secret with full JSON content
```

---

## 📝 Credential Storage Template

Use this template to organize your credentials (store in password manager, not in repo):

```
=== Imagineer Production Credentials ===

Cloudflare API Token:
  Value: [your-token-here]
  Created: [date]
  Permissions: Zone.DNS Edit, Zone.Firewall Edit
  Zone: joshwentworth.com
  Used in: terraform/terraform.tfvars

Cloudflare Tunnel ID:
  Value: [obtained during setup]
  Name: imagineer-api
  Domain: imagineer.joshwentworth.com
  Used in: terraform/terraform.tfvars

Webhook Secret:
  Value: [generated with openssl rand -hex 32]
  Created: [date]
  Used in: .env.production, GitHub webhook

App Password:
  Value: carnuvian
  Used in: web/.env.production, GitHub secret VITE_APP_PASSWORD

Firebase Project:
  Project ID: static-sites-257923
  Hosting Site: imagineer-generator
  Service Account: [JSON key for GitHub Actions]

GitHub Repository:
  URL: https://github.com/yourusername/imagineer
  Secrets:
    - FIREBASE_SERVICE_ACCOUNT: [JSON key]
    - VITE_APP_PASSWORD: carnuvian
    - CLOUDFLARE_API_TOKEN: [token]
    - CLOUDFLARE_TUNNEL_ID: [tunnel id]
```

---

## 🎯 Summary

### Absolutely Required (for deployment to work):

1. **Cloudflare API Token** → `terraform/terraform.tfvars`
2. **Cloudflare Account Login** → `cloudflared tunnel login` (one-time)
3. **Firebase/Google Login** → `firebase login` (one-time)

### Optional (for automation):

4. **GitHub Secrets** → For CI/CD auto-deployment
5. **Webhook Secret** → For push-triggered deployments

### Quick Test:

```bash
# Test all authentication
bash scripts/deploy/deploy-all.sh --dry-run

# Should pass:
# ✓ Cloudflare API token valid (Terraform)
# ✓ Cloudflare tunnel authenticated
# ✓ Firebase authenticated
```

---

## 📖 Related Documentation

- **Cloudflare Tunnel Setup**: [../CLOUDFLARE_TUNNEL_SETUP.md](../CLOUDFLARE_TUNNEL_SETUP.md)
- **Deployment Guide**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Deployment Orchestration**: [DEPLOYMENT_ORCHESTRATION.md](DEPLOYMENT_ORCHESTRATION.md)
- **GitHub Actions Setup**: [../.github/workflows/](../.github/workflows/)

---

**Questions?** Check the troubleshooting section above or open an issue.
