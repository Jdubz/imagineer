# Firebase Deployment - Quick Start

**Project:** static-sites-257923
**App:** imagineer-generator

## 🚀 One-Time Setup

### 1. Install & Login

```bash
# Install Firebase CLI (if not already installed)
npm install -g firebase-tools

# Login to Firebase
firebase login

# Verify project is accessible
firebase projects:list
# Should show: static-sites-257923
```

### 2. Test Local Build

```bash
# Build frontend
cd web
npm run build
cd ..

# Test with Firebase serving
firebase serve --only hosting
# Visit: http://localhost:5000
```

### 3. Deploy to Production

```bash
# Deploy using Makefile
make deploy-frontend-prod

# Or manually
firebase deploy --only hosting:imagineer
```

**Your app will be live at:**
- https://imagineer-generator.web.app
- https://imagineer-generator.firebaseapp.com

---

## 🔐 GitHub Actions Setup (Optional)

For automatic deployments when you push to main:

### 1. Get Firebase Service Account

```bash
firebase login:ci
```

This outputs a token. **Copy it** - you'll need it for GitHub.

### 2. Add GitHub Secrets

Go to: https://github.com/yourusername/imagineer/settings/secrets/actions

Add these secrets:

```
Name: FIREBASE_SERVICE_ACCOUNT
Value: (paste the token from step 1)

Name: VITE_APP_PASSWORD
Value: carnuvian

Name: VITE_API_BASE_URL_PROD
Value: https://api.your-domain.com/api
```

### 3. Test Auto-Deploy

```bash
# Push to main
git checkout main
git commit --allow-empty -m "Test Firebase auto-deploy"
git push origin main

# Check GitHub Actions tab to see deployment progress
```

---

## 📝 Quick Commands

```bash
# Deploy
make deploy-frontend-prod

# Rollback
firebase hosting:rollback

# Local test
firebase serve --only hosting

# View deployments
firebase hosting:channel:list

# Check status
firebase use
```

---

## 🌐 Your URLs

**Firebase Hosting:**
- https://imagineer-generator.web.app
- https://imagineer-generator.firebaseapp.com

**Firebase Console:**
- https://console.firebase.google.com/project/static-sites-257923/hosting

---

## 🐛 Troubleshooting

**Wrong project?**
```bash
firebase use static-sites-257923
```

**Build fails?**
```bash
cd web
npm install
npm run build
```

**Deploy fails?**
```bash
firebase deploy --only hosting:imagineer --debug
```

---

**Full Documentation:** See [docs/FIREBASE_SETUP.md](docs/FIREBASE_SETUP.md)
