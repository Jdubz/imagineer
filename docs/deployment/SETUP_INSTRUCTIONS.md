# Final Setup Instructions

## What's Been Completed ✅

1. **Frontend Built** - React app compiled to `public/` directory with relative API paths
2. **SSH Key Generated** - Deployment key created at `~/.ssh/imagineer_deploy`
3. **Services Tested** - API responding on localhost:10050
4. **Configuration Updated** - All config files ready to deploy

## What You Need to Do (5-10 minutes)

### Step 1: Run the Setup Script (5 min)

This will install nginx and configure all services with the new routing:

```bash
cd /home/jdubz/Development/imagineer
bash complete-setup.sh
```

This script will:
- Install nginx (if needed)
- Update cloudflared config with new routing rules
- Install nginx site configuration
- Install systemd services for API and tunnel
- Restart all services
- Test all endpoints

### Step 2: Add GitHub Secrets (5 min)

Go to: https://github.com/joshbwentworth/imagineer/settings/secrets/actions

Click **"New repository secret"** and add each of these:

#### SSH_PRIVATE_KEY
```
# Generate a new deploy key and paste the private key here.
# Never store the actual private key in Git. Add it only as a secret.
```

#### SSH_HOST
```
192.168.86.35
```

#### SSH_USER
```
jdubz
```

#### VITE_APP_PASSWORD
```
# Deprecated. No longer required now that the password gate has been removed.
```

### Step 3: Test the Deployment (2 min)

After running the setup script, test these URLs:

```bash
# Test locally
curl http://localhost:8080/health          # nginx health check
curl http://localhost:10050/api/health     # API health check

# Test publicly (may take a minute for tunnel to connect)
curl https://imagineer.joshwentworth.com/health
curl https://imagineer.joshwentworth.com/api/health
```

Visit in your browser:
- **Frontend:** https://imagineer.joshwentworth.com
- **API:** https://imagineer.joshwentworth.com/api/health

### Step 4: Test Auto-Deployment (2 min)

Make a small change to trigger deployment:

```bash
cd /home/jdubz/Development/imagineer
git add .
git commit -m "test: Verify auto-deployment"
git push origin main
```

Watch the deployment: https://github.com/joshbwentworth/imagineer/actions

## Architecture Overview

```
User Request → https://imagineer.joshwentworth.com
    ↓
Cloudflare Tunnel (db1a99dd-3d12-4315-b241-da2a55a5c30f)
    ↓
    ├─ /api/* → localhost:10050 (Flask API)
    └─ /*     → localhost:8080 (nginx → React)
```

## Service Management

```bash
# Check status
sudo systemctl status nginx imagineer-api cloudflared-imagineer-api

# View logs
sudo journalctl -u nginx -f
sudo journalctl -u imagineer-api -f
sudo journalctl -u cloudflared-imagineer-api -f

# Restart services
sudo systemctl restart nginx
sudo systemctl restart imagineer-api
sudo systemctl restart cloudflared-imagineer-api
```

## Troubleshooting

### Public domain not resolving?

Wait 1-2 minutes for the tunnel to reconnect after restarting the service. Check tunnel status:

```bash
cloudflared tunnel info imagineer-api
ps aux | grep cloudflared
```

### Frontend not loading?

Check nginx status and logs:

```bash
sudo systemctl status nginx
sudo journalctl -u nginx -n 50
ls -la /home/jdubz/Development/imagineer/public/
```

### API not responding?

```bash
sudo systemctl status imagineer-api
sudo journalctl -u imagineer-api -n 50
curl http://localhost:10050/api/health
```

### GitHub Actions deployment failing?

1. Verify all secrets are added correctly
2. Test SSH manually:
   ```bash
   ssh -i ~/.ssh/imagineer_deploy jdubz@192.168.86.35 "echo test"
   ```
3. Check workflow logs on GitHub Actions page

## Files Reference

### Configuration Files Created
- `complete-setup.sh` - Setup script (run this first)
- `setup-production-services.sh` - Alternative automated setup
- `imagineer-api.service` - API systemd service
- `cloudflared-imagineer-api.service` - Tunnel systemd service
- `nginx-imagineer.conf` - nginx configuration
- `cloudflared-config.yml` - Tunnel routing rules

### Documentation
- `DEPLOYMENT_QUICK_START.md` - Quick reference guide
- `docs/deployment/PRODUCTION_DEPLOYMENT_GUIDE.md` - Comprehensive guide
- `DEPLOYMENT_CHANGES_SUMMARY.md` - All changes made
- `SETUP_INSTRUCTIONS.md` - This file

## Success Checklist

- [ ] Run `complete-setup.sh` successfully
- [ ] All 4 GitHub Secrets added
- [ ] `curl http://localhost:8080/health` returns "healthy"
- [ ] `curl http://localhost:10050/api/health` returns JSON
- [ ] `curl https://imagineer.joshwentworth.com/health` works
- [ ] `curl https://imagineer.joshwentworth.com/api/health` works
- [ ] Can visit https://imagineer.joshwentworth.com in browser
- [ ] OAuth login works
- [ ] Push to main triggers auto-deployment
- [ ] Changes appear on live site

## What's Next?

Once everything is deployed and working:

1. **Test OAuth thoroughly** - Make sure Google login works
2. **Start the improvement plan** - See `docs/plans/REVISED_IMPROVEMENT_PLAN.md`
   - Phase 1: Database setup, security fixes, simplified auth
3. **Set up monitoring** - Add health check alerts
4. **Configure backups** - Protect generated images

## Need Help?

1. Check `docs/deployment/PRODUCTION_DEPLOYMENT_GUIDE.md` for detailed troubleshooting
2. Review service logs with `journalctl`
3. Test each component individually (nginx, API, tunnel)
4. Verify all config files match the documentation
