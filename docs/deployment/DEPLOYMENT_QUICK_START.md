# Deployment Quick Start

This is your checklist to get Imagineer deployed to production at https://imagineer.joshwentworth.com

## What We've Set Up

✅ **Cloudflare Tunnel Configuration** - Routes traffic from imagineer.joshwentworth.com to your services
- `/api/*` → Flask API (localhost:10050)
- `/*` → nginx serving React (localhost:8080)

✅ **Systemd Services** - Process management with auto-restart
- `imagineer-api.service` - Flask API server
- `cloudflared-imagineer-api.service` - Cloudflare Tunnel
- `nginx` - Web server for React

✅ **nginx Configuration** - Serves React static files from `public/`

✅ **GitHub Actions Workflow** - Auto-deploys on push to main
- Builds React app
- Deploys via SSH to server
- Updates `public/` directory

✅ **Environment Configuration** - Updated for single-domain deployment
- Backend uses relative API paths
- CORS configured for imagineer.joshwentworth.com

## Your To-Do List

### 1. Run the Setup Script (5 minutes)

```bash
cd /home/jdubz/Development/imagineer
bash setup-production-services.sh
```

This installs and starts all services.

### 2. Initial Frontend Build (2 minutes)

```bash
cd /home/jdubz/Development/imagineer
cd web && npm install && npm run build && cd ..
rm -rf public && cp -r web/dist public
```

### 3. Test Locally (1 minute)

```bash
curl http://localhost:8080/health  # Should return "healthy"
curl http://localhost:10050/api/health  # Should return JSON
curl https://imagineer.joshwentworth.com/health  # Should work via tunnel
```

### 4. Set Up GitHub Secrets (5 minutes)

Generate SSH key:
```bash
ssh-keygen -t ed25519 -f ~/.ssh/imagineer_deploy -N ""
cat ~/.ssh/imagineer_deploy.pub >> ~/.ssh/authorized_keys
cat ~/.ssh/imagineer_deploy  # Copy this for GitHub
```

Go to GitHub → Settings → Secrets → Actions → New secret

Add these:
- `SSH_PRIVATE_KEY` = Contents of `~/.ssh/imagineer_deploy`
- `SSH_HOST` = Your server IP/hostname
- `SSH_USER` = `jdubz`
- `VITE_APP_PASSWORD` = `[REDACTED]`

### 5. Update Google OAuth (2 minutes)

Google Cloud Console → APIs & Services → Credentials → Your OAuth 2.0 Client

**Add** these authorized redirect URIs:
- `https://imagineer.joshwentworth.com/auth/google/callback`

**Keep** this one for local dev:
- `http://localhost:10050/auth/google/callback`

### 6. Test Auto-Deployment (2 minutes)

```bash
# Make a small change to trigger deployment
cd web/src
echo "// test deploy" >> App.jsx
git add .
git commit -m "test: Trigger deployment"
git push origin main
```

Watch it deploy: https://github.com/joshbwentworth/imagineer/actions

### 7. Verify Everything Works (2 minutes)

Visit these URLs:
- ✅ https://imagineer.joshwentworth.com (React app)
- ✅ https://imagineer.joshwentworth.com/api/health (API)
- ✅ https://imagineer.joshwentworth.com/auth/login (OAuth login)

## Total Time: ~20 minutes

## Troubleshooting

**Services not starting?**
```bash
sudo journalctl -u imagineer-api -n 50
sudo journalctl -u cloudflared-imagineer-api -n 50
sudo journalctl -u nginx -n 50
```

**GitHub Actions failing?**
- Check that SSH secrets are set correctly
- Verify SSH key is in `~/.ssh/authorized_keys`
- Test SSH manually: `ssh jdubz@<your-server> "echo test"`

**Frontend not loading?**
```bash
ls -la /home/jdubz/Development/imagineer/public/
sudo systemctl status nginx
```

**API not responding?**
```bash
sudo systemctl status imagineer-api
curl http://localhost:10050/api/health
```

## Next Steps

After deployment is complete:

1. **Test OAuth login** - Make sure Google authentication works
2. **Start the improvement plan** - See `docs/plans/REVISED_IMPROVEMENT_PLAN.md`
3. **Set up monitoring** - Add alerts for service failures
4. **Configure backups** - Protect your generated images and data

## Reference Documentation

For detailed information, see:
- **Full Guide**: `docs/deployment/PRODUCTION_DEPLOYMENT_GUIDE.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Improvement Plan**: `docs/plans/REVISED_IMPROVEMENT_PLAN.md`
