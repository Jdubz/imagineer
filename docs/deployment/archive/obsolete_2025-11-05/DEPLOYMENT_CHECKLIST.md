# Production Deployment Checklist

**Last Updated:** 2025-11-05
**Purpose:** Standardized process for deploying Imagineer to production

## Overview

This checklist ensures safe, consistent deployments to the production server running on `main` branch at port 10050, served through Cloudflare Tunnel at `imagineer-api.joshwentworth.com`.

---

## Pre-Deployment Checklist

### Code Readiness

- [ ] All changes merged to `develop` branch
- [ ] All pre-push checks passing on `develop`
- [ ] Manual testing completed on development server (port 5000)
- [ ] No uncommitted changes in working directory
- [ ] Database migrations tested in development environment

### Documentation Updates

- [ ] CHANGELOG.md updated with release notes
- [ ] README.md updated if user-facing changes exist
- [ ] API documentation updated if endpoints changed
- [ ] CLAUDE.md updated if architecture changed

### Frontend Deployment

- [ ] Frontend built successfully: `cd web && npm run build`
- [ ] Frontend deployed to Firebase: `firebase deploy --only hosting`
- [ ] Firebase deployment verified at `https://imagineer-generator.web.app`

### Dependencies

- [ ] `requirements.txt` up to date
- [ ] `web/package.json` up to date
- [ ] No security vulnerabilities in dependencies

---

## Creating Production Release

### 1. Create Pull Request

```bash
# Ensure you're on develop with latest changes
git checkout develop
git pull origin develop

# Create PR from develop → main (via GitHub UI or CLI)
gh pr create --base main --head develop --title "Release: [Version/Date]" --body "Release notes..."
```

### 2. PR Review

- [ ] Review all changes in the PR diff
- [ ] Verify no test data or debug code included
- [ ] Check for hardcoded secrets or credentials
- [ ] Confirm production configs (`config.yaml`) only changed via this PR
- [ ] Verify CI/CD checks pass (linting, type checking, tests)

### 3. Merge to Main

- [ ] Get approval (self-approval OK for solo dev)
- [ ] Merge PR using "Squash and merge" or "Merge commit"
- [ ] Verify merge successful
- [ ] Delete feature branch if applicable

---

## Post-Merge Verification

### 1. Monitor CI/CD Pipeline

- [ ] CI/CD pipeline starts automatically after merge
- [ ] All pipeline steps complete successfully
- [ ] No errors in deployment logs

### 2. Verify Production Server Status

```bash
# Check systemd service status
sudo systemctl status imagineer-api

# Expected output:
# ● imagineer-api.service - Imagineer API Server
#    Active: active (running) since [timestamp]
```

### 3. Verify Health Endpoint

```bash
# Check health endpoint
curl http://localhost:10050/api/health | jq

# Verify response contains:
# {
#   "status": "ok",
#   "environment": "production",    ← MUST be "production"
#   "branch": "main",                ← MUST be "main"
#   "version": "[expected version]",
#   "git_commit": "[commit hash]"
# }
```

**If environment != "production" or branch != "main":**
- **DO NOT PROCEED**
- Check server configuration
- Review systemd service file
- Investigate deployment logs

### 4. Verify External Access

```bash
# Test public API endpoint (via Cloudflare Tunnel)
curl https://imagineer-api.joshwentworth.com/api/health | jq

# Should return same response as localhost
```

### 5. Smoke Test Critical Functionality

- [ ] **Image Generation**: Generate single image via frontend
- [ ] **Batch Generation**: Create batch from template
- [ ] **Album Listing**: View albums in gallery
- [ ] **Authentication**: Google OAuth login works
- [ ] **Admin Access**: Admin-only endpoints accessible
- [ ] **Scraping** (if applicable): Scrape job starts successfully

### 6. Monitor Logs

```bash
# Live production logs
sudo journalctl -u imagineer-api -f

# Error logs
tail -f /var/log/imagineer/error.log

# Access logs
tail -f /var/log/imagineer/access.log
```

**Monitor for:**
- No error spikes
- No repeated warnings
- No authentication failures
- Response times normal

---

## Rollback Procedure

**Use this if production is broken after deployment**

### Immediate Rollback

```bash
# 1. Revert the merge commit on main
git checkout main
git pull origin main
git revert HEAD  # Creates new commit that undoes the merge
git push origin main

# 2. CI/CD auto-deploys previous version
# Monitor: sudo journalctl -u imagineer-api -f

# 3. Verify rollback
curl http://localhost:10050/api/health | jq '.version'
```

### Manual Restart (Last Resort)

```bash
# Only if CI/CD doesn't auto-restart
sudo systemctl restart imagineer-api

# Wait for startup
sleep 5

# Verify health
curl http://localhost:10050/api/health
```

### Post-Rollback

- [ ] Verify production is stable
- [ ] Notify users if needed
- [ ] Create issue documenting the problem
- [ ] Fix issue on `develop` branch
- [ ] Test thoroughly before re-deploying

---

## Database Migration Procedure

**For deployments that include schema changes**

### Pre-Deployment

```bash
# Test migration in development
python scripts/migrate.py

# Backup production database
cp instance/imagineer.db instance/imagineer.db.backup-$(date +%Y%m%d-%H%M%S)
```

### During Deployment

- [ ] CI/CD runs migrations automatically
- [ ] Monitor migration output in logs
- [ ] Verify no migration errors

### Rollback with Migrations

```bash
# If rollback needed after migration
# 1. Stop production service
sudo systemctl stop imagineer-api

# 2. Restore database backup
cp instance/imagineer.db.backup-[timestamp] instance/imagineer.db

# 3. Revert code (see Rollback Procedure above)

# 4. Start production service
sudo systemctl start imagineer-api
```

---

## Emergency Contacts & Resources

### Server Access

- **Production Server**: Port 10050 (localhost only)
- **Public API**: https://imagineer-api.joshwentworth.com (via Cloudflare Tunnel)
- **Frontend**: https://imagineer-generator.web.app (Firebase Hosting)

### Log Locations

- **Systemd Logs**: `sudo journalctl -u imagineer-api -f`
- **Error Logs**: `/var/log/imagineer/error.log`
- **Access Logs**: `/var/log/imagineer/access.log`
- **Application Logs**: Check systemd journal

### Service Management

```bash
# View status
sudo systemctl status imagineer-api

# View logs (live)
sudo journalctl -u imagineer-api -f

# View logs (last 100 lines)
sudo journalctl -u imagineer-api -n 100

# Restart (emergency only)
sudo systemctl restart imagineer-api

# Check config
sudo systemctl cat imagineer-api
```

### Configuration Files

- **Production Config**: `config.yaml` (main branch only)
- **Environment**: `.env.production` (gitignored)
- **Systemd Service**: `/etc/systemd/system/imagineer-api.service`
- **Cloudflare Tunnel**: `/etc/cloudflared/config.yml`

---

## Post-Deployment Tasks

### Documentation

- [ ] Update deployment log/wiki with deployment notes
- [ ] Document any issues encountered
- [ ] Update this checklist if process changed

### Monitoring

- [ ] Check error rates in next 24 hours
- [ ] Monitor disk space usage
- [ ] Verify scheduled jobs running (Celery workers)
- [ ] Check database size growth

### Cleanup

- [ ] Archive old log files if disk space low
- [ ] Remove old database backups (keep last 7 days)
- [ ] Merge `main` back to `develop` if needed

```bash
# Sync develop with main after successful deployment
git checkout develop
git merge main
git push origin develop
```

---

## Deployment Frequency Guidelines

- **Hotfixes**: Deploy ASAP after verification in dev
- **Features**: Deploy weekly or bi-weekly
- **Major Changes**: Deploy during low-traffic periods
- **Database Migrations**: Deploy with extra caution, prefer off-peak hours

---

## Notes

- **Production is sacred**: Never make manual changes on production server
- **All changes via PR**: No direct commits to `main`
- **Test in development first**: Always use `./run-dev.sh` for testing
- **Monitor after deploy**: Watch logs for at least 30 minutes after deployment
- **Document everything**: Update this checklist and deployment logs

---

**Last Deployment:** [Update after each deployment]
**Next Scheduled Deployment:** [Update with planned date]
