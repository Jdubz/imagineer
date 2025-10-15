# Firebase Hosting Setup Guide

**Project:** static-sites-257923
**App:** imagineer-generator
**Last Updated:** 2025-10-14

## Quick Setup

### 1. Install Firebase CLI

```bash
# Install globally
npm install -g firebase-tools

# Verify installation
firebase --version
```

### 2. Login to Firebase

```bash
# Login with your Google account
firebase login

# Verify you're logged in
firebase projects:list
```

You should see `static-sites-257923` in the list.

### 3. Configuration Files

The Firebase configuration is already set up:

**`.firebaserc`** - Project configuration:
```json
{
  "projects": {
    "default": "static-sites-257923"
  },
  "targets": {
    "static-sites-257923": {
      "hosting": {
        "imagineer": ["imagineer-generator"]
      }
    }
  }
}
```

**`firebase.json`** - Hosting configuration:
- SPA routing (all routes → index.html)
- Asset caching (1 year for static files)
- Security headers (XSS, CSP, frame denial)
- Clean URLs

### 4. Test Build Locally

```bash
# Build the frontend
cd web
npm run build

# Test Firebase serving locally
cd ..
firebase serve --only hosting
# Opens at http://localhost:5000
```

### 5. Deploy to Production

```bash
# Using Makefile (recommended)
make deploy-frontend-prod

# Or manually
cd web
npm run build
cd ..
firebase deploy --only hosting:imagineer
```

### 6. Verify Deployment

After deployment, you'll see output like:

```
✔  Deploy complete!

Project Console: https://console.firebase.google.com/project/static-sites-257923/overview
Hosting URL: https://imagineer-generator.web.app
```

Visit the Hosting URL to test your deployment.

---

## GitHub Actions Setup

To enable automatic deployments via GitHub Actions, you need to add Firebase credentials as GitHub secrets.

### Step 1: Get Firebase Service Account

```bash
# Generate a service account key
firebase login:ci

# This will output a token like:
# 1//0abc123...xyz789

# Save this token - you'll need it for GitHub
```

**Or use a service account JSON:**

1. Go to [Firebase Console](https://console.firebase.google.com/project/static-sites-257923/settings/serviceaccounts/adminsdk)
2. Click **Generate New Private Key**
3. Download the JSON file (keep it secure!)

### Step 2: Add GitHub Secrets

Go to your GitHub repository:
1. **Settings → Secrets and variables → Actions**
2. Click **New repository secret**

Add these secrets:

**Required secrets:**

```
FIREBASE_SERVICE_ACCOUNT
```
Paste the entire content of the service account JSON file, OR use the token from `firebase login:ci`.

If using the token method, the GitHub Action needs to be updated to use the token instead of service account.

**Additional secrets:**

```
FIREBASE_PROJECT_ID = static-sites-257923
```

**Frontend configuration secrets:**

```
VITE_APP_PASSWORD = carnuvian
VITE_API_BASE_URL_DEV = http://localhost:10050/api
VITE_API_BASE_URL_PROD = https://api.your-domain.com/api
```

### Step 3: Update GitHub Actions Workflow

The workflow at `.github/workflows/deploy-frontend.yml` is already configured. It will:

1. Build the frontend with environment-specific config
2. Deploy to Firebase on push to main/develop
3. Can be manually triggered with custom environment

### Step 4: Test GitHub Actions

```bash
# Push to main to trigger deployment
git checkout main
git commit --allow-empty -m "Test Firebase deploy"
git push origin main

# Or manually trigger:
# Go to GitHub → Actions → Deploy Frontend → Run workflow
```

---

## Firebase Hosting Configuration

### Current Settings (firebase.json)

**Routing:**
- All routes redirect to `/index.html` (SPA support)
- Clean URLs (no `.html` extension needed)
- No trailing slashes

**Caching:**
- Static assets (JS, CSS, images): 1 year
- HTML files: No cache (always fetch latest)

**Security Headers:**
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`

**Error Pages:**
- 404 → index.html (SPA handles routing)

### Custom Domain Setup (Optional)

To use a custom domain like `imagineer.your-domain.com`:

1. **In Firebase Console:**
   - Go to Hosting → Add custom domain
   - Enter your domain
   - Follow DNS configuration steps

2. **Add DNS records:**
   ```
   Type: A
   Name: imagineer (or @)
   Value: (Firebase provides the IP)
   ```

3. **Wait for SSL:**
   - Firebase automatically provisions SSL certificate
   - Takes 15 minutes to 24 hours

4. **Update environment variables:**
   ```bash
   # In GitHub secrets
   VITE_API_BASE_URL_PROD=https://api.your-domain.com/api
   ```

---

## Management Commands

### Deploy

```bash
# Production (via Makefile)
make deploy-frontend-prod

# Development
make deploy-frontend-dev

# Manual (from project root)
firebase deploy --only hosting:imagineer

# Preview (create preview channel)
firebase hosting:channel:deploy preview-$(date +%s)
```

### Rollback

```bash
# View deployment history
firebase hosting:channel:list

# Rollback to previous version
firebase hosting:rollback

# Or restore specific version from Firebase Console
```

### View Logs

```bash
# Firebase Console → Hosting → View logs
# Or use CLI
firebase hosting:channel:list
```

### Local Testing

```bash
# Build frontend
cd web && npm run build && cd ..

# Serve locally on port 5000
firebase serve --only hosting

# Test in browser
open http://localhost:5000
```

---

## Environment URLs

After deployment, your app will be available at:

**Firebase Hosting URL:**
- `https://imagineer-generator.web.app`
- `https://imagineer-generator.firebaseapp.com`

**Custom Domain (if configured):**
- `https://imagineer.your-domain.com`

---

## Troubleshooting

### Authentication Issues

```bash
# Re-authenticate
firebase logout
firebase login

# Check current user
firebase login:list
```

### Build Fails

```bash
# Check build locally
cd web
npm run build

# Check for errors
npm run lint
```

### Deployment Fails

```bash
# Check Firebase status
firebase projects:list

# Verify project ID
cat .firebaserc

# Check hosting configuration
firebase hosting:sites:list

# Re-deploy
firebase deploy --only hosting:imagineer --debug
```

### GitHub Actions Fails

```bash
# Check secrets are set
# GitHub → Settings → Secrets → Actions

# Verify service account has permissions
# Firebase Console → Settings → Service Accounts

# Check workflow logs
# GitHub → Actions → Select failed run → View logs
```

### Wrong Project/App

```bash
# Check current project
firebase use

# Switch project
firebase use static-sites-257923

# List targets
firebase target:list

# Re-apply target
firebase target:apply hosting imagineer imagineer-generator
```

---

## Firebase Console Links

**Project Overview:**
https://console.firebase.google.com/project/static-sites-257923/overview

**Hosting Dashboard:**
https://console.firebase.google.com/project/static-sites-257923/hosting

**Service Accounts:**
https://console.firebase.google.com/project/static-sites-257923/settings/serviceaccounts

**Usage & Billing:**
https://console.firebase.google.com/project/static-sites-257923/usage

---

## Firebase CLI Reference

```bash
# Authentication
firebase login                    # Login
firebase logout                   # Logout
firebase login:list               # List accounts

# Projects
firebase projects:list            # List all projects
firebase use static-sites-257923  # Switch project

# Hosting
firebase deploy --only hosting:imagineer        # Deploy
firebase hosting:channel:deploy preview-test    # Preview deploy
firebase hosting:channel:list                   # List channels
firebase hosting:rollback                       # Rollback
firebase serve --only hosting                   # Local serve

# Targets
firebase target:list              # List targets
firebase target:apply hosting imagineer imagineer-generator  # Apply target

# Help
firebase --help                   # General help
firebase deploy --help            # Deploy help
```

---

## Quick Commands

```bash
# Setup
firebase login
firebase use static-sites-257923

# Deploy
make deploy-frontend-prod

# Rollback
firebase hosting:rollback

# Local test
firebase serve --only hosting

# Check status
firebase hosting:sites:list
```

---

## Security Checklist

- [x] `.firebaserc` configured with correct project
- [x] `firebase.json` has security headers
- [x] Service account key stored securely (GitHub Secrets)
- [x] `.gitignore` excludes sensitive files
- [ ] Custom domain configured (optional)
- [ ] SSL certificate active (automatic with Firebase)
- [ ] Environment variables set in GitHub Secrets
- [ ] CORS configured on API backend

---

## Next Steps

1. **Test local build:**
   ```bash
   cd web && npm run build
   firebase serve --only hosting
   ```

2. **Deploy to production:**
   ```bash
   make deploy-frontend-prod
   ```

3. **Set up GitHub Actions:**
   - Add Firebase service account to GitHub Secrets
   - Add environment variable secrets
   - Push to main to trigger deployment

4. **Verify deployment:**
   - Visit https://imagineer-generator.web.app
   - Test password gate
   - Verify API connectivity

5. **Optional - Custom domain:**
   - Configure in Firebase Console
   - Update DNS records
   - Wait for SSL provisioning

---

**For more information:**
- [Firebase Hosting Docs](https://firebase.google.com/docs/hosting)
- [GitHub Actions for Firebase](https://github.com/marketplace/actions/deploy-to-firebase-hosting)
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

**Document Version:** 1.0
**Author:** Claude Code
**Last Review:** 2025-10-14
