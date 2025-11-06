# Template-Album Separation: Deployment Guide

**Project**: Imagineer AI Image Generation Toolkit
**Feature**: Batch Template System
**Version**: 1.0.0
**Date**: 2025-11-04

---

## Pre-Deployment Checklist

Before deploying, ensure you have:

- [ ] Database backup created
- [ ] All changes committed to git
- [ ] Backend tested locally
- [ ] Frontend built and tested
- [ ] Production environment access
- [ ] Rollback plan ready

---

## Step 1: Backup Database

**CRITICAL**: Always backup before migration!

```bash
# SSH into production server
ssh your-server

# Navigate to app directory
cd /home/jdubz/Development/imagineer

# Create timestamped backup
cp instance/imagineer.db instance/imagineer_backup_$(date +%Y%m%d_%H%M%S).db

# Verify backup
ls -lh instance/imagineer_backup_*.db
```

**Expected output**: Backup file with ~3-4MB size

---

## Step 2: Deploy Backend Changes

### 2.1: Pull Latest Code

```bash
# Navigate to app directory
cd /home/jdubz/Development/imagineer

# Stash any local changes (if needed)
git stash

# Pull latest changes
git pull origin develop

# Show what changed
git log --oneline -10
```

### 2.2: Update Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Install any new Python dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep -E "flask|sqlalchemy|peft"
```

### 2.3: Run Database Migration

```bash
# Activate virtual environment
source venv/bin/activate

# Run migration script
python scripts/migrate_template_album_separation.py
```

**Expected output**:
```
================================================================================
TEMPLATE-ALBUM SEPARATION MIGRATION
================================================================================

[Step 0] Creating database backup...
✅ Database backup created: instance/imagineer_backup_TIMESTAMP.db

[Step 1] Creating new tables...
✅ Created batch_templates table
✅ Created batch_generation_runs table

[Step 2] Adding source tracking columns...
✅ Added source_type column to albums
✅ Added source_id column to albums

[Step 3] Deleting empty template albums...
🗑️  Deleted template album: Card Deck Template
🗑️  Deleted template album: Zodiac Template
🗑️  Deleted template album: Tarot Deck Template
✅ Deleted 3 empty template albums

[Step 4] Seeding batch templates...
✅ Created batch template: Playing Card Deck
✅ Created batch template: Tarot Major Arcana
✅ Created batch template: Zodiac Signs

[Step 5] Marking existing albums as manual...
✅ Marked 9 albums as source_type='manual'

[Step 6-8] Importing orphaned images...
✅ Imported 66 single-generation images to 'Ad-hoc Generations'

[Step 9] Adding album_name to scrape_jobs...
✅ Added album_name column to scrape_jobs

================================================================================
MIGRATION VERIFICATION
================================================================================
✅ batch_templates table exists
✅ batch_generation_runs table exists
✅ albums.source_type exists
✅ albums.source_id exists
✅ template albums deleted
✅ batch templates seeded

✅ Migration completed successfully!
```

**If migration fails**:
```bash
# Restore from backup
cp instance/imagineer_backup_TIMESTAMP.db instance/imagineer.db

# Report the error
```

### 2.4: Restart API Service

```bash
# Restart the Gunicorn service
sudo systemctl restart imagineer-api

# Check status
sudo systemctl status imagineer-api

# Monitor logs
sudo journalctl -u imagineer-api -f
```

**Expected**: Service should start without errors

### 2.5: Verify Backend

```bash
# Test batch templates endpoint
curl https://imagineer-api.joshwentworth.com/api/batch-templates

# Expected: JSON with 3 templates
# {
#   "templates": [
#     {"id": 1, "name": "Playing Card Deck", ...},
#     {"id": 2, "name": "Tarot Major Arcana", ...},
#     {"id": 3, "name": "Zodiac Signs", ...}
#   ],
#   "total": 3,
#   ...
# }

# Test albums endpoint
curl https://imagineer-api.joshwentworth.com/api/albums

# Expected: JSON with 9 albums, all with source_type='manual'
```

---

## Step 3: Deploy Frontend Changes

### 3.1: Install Dependencies

```bash
# Navigate to web directory
cd web

# Install dependencies
npm install

# Verify no errors
```

### 3.2: Build Production Bundle

```bash
# Build for production
npm run build

# Check build output
ls -lh dist/
```

**Expected**: `dist/` directory with:
- `index.html`
- `assets/` folder with JS/CSS bundles
- Total size: ~2-5MB

### 3.3: Test Build Locally (Optional)

```bash
# Serve build locally
npm run preview

# Open browser to http://localhost:4173
# Navigate to /batch-templates
# Verify page loads
```

### 3.4: Deploy to Firebase

```bash
# Deploy to Firebase Hosting
firebase deploy --only hosting

# Wait for deployment to complete
```

**Expected output**:
```
=== Deploying to 'imagineer-generator'...

✔ hosting: deploy complete

✔ Deploy complete!

Project Console: https://console.firebase.google.com/project/imagineer-generator/overview
Hosting URL: https://imagineer-generator.web.app
```

---

## Step 4: Post-Deployment Verification

### 4.1: Test Backend Endpoints

```bash
# List templates
curl https://imagineer-api.joshwentworth.com/api/batch-templates

# Get specific template
curl https://imagineer-api.joshwentworth.com/api/batch-templates/1

# List albums
curl https://imagineer-api.joshwentworth.com/api/albums
```

### 4.2: Test Frontend

1. **Navigate to app**: https://imagineer-generator.web.app

2. **Test Templates Tab**:
   - Click "Templates" tab in navigation
   - Verify 3 templates appear
   - Click "Generate Batch" on any template
   - Fill in album name and theme
   - Click "Generate Batch"
   - Verify toast notification appears

3. **Test Albums Tab**:
   - Click "Albums" tab
   - Verify 9 albums appear
   - Verify NO template albums appear
   - Verify source badges NOT shown (all manual)

4. **Test Generate Tab**:
   - Click "Generate" tab
   - Verify single generation form works
   - Verify batch section shows link to Templates tab
   - Click "Go to Templates →" button
   - Verify navigates to Templates page

### 4.3: Smoke Tests

- [ ] Homepage loads
- [ ] Navigation works
- [ ] Templates page loads and shows 3 templates
- [ ] Albums page shows 9 albums (no templates)
- [ ] Generate form works
- [ ] Template generation creates run record
- [ ] No console errors
- [ ] No 404s in network tab

---

## Step 5: Monitor & Validate

### 5.1: Check Logs

```bash
# Monitor API logs for errors
sudo journalctl -u imagineer-api -f

# Check for errors
sudo journalctl -u imagineer-api --since "5 minutes ago" | grep ERROR
```

### 5.2: Database Verification

```bash
# SSH into server
cd /home/jdubz/Development/imagineer
source venv/bin/activate

# Check database state
python -c "
from server.database import db, Album, BatchTemplate
from server.api import app

with app.app_context():
    print(f'Batch Templates: {BatchTemplate.query.count()}')
    print(f'Albums: {Album.query.count()}')
    print(f'Template Albums: {Album.query.filter_by(is_set_template=True).count()}')
"
```

**Expected output**:
```
Batch Templates: 3
Albums: 9
Template Albums: 0
```

---

## Rollback Procedure

If critical issues are discovered:

### Option 1: Database Rollback Only

```bash
# Stop API
sudo systemctl stop imagineer-api

# Restore database backup
cp instance/imagineer_backup_TIMESTAMP.db instance/imagineer.db

# Restart API
sudo systemctl start imagineer-api
```

### Option 2: Full Rollback (Code + Database)

```bash
# Stop API
sudo systemctl stop imagineer-api

# Restore database
cp instance/imagineer_backup_TIMESTAMP.db instance/imagineer.db

# Revert code
git log --oneline -10  # Find commit before migration
git checkout <commit-hash>

# Restart API
sudo systemctl restart imagineer-api

# Redeploy old frontend
cd web
git checkout <commit-hash>
npm install
npm run build
firebase deploy --only hosting
```

---

## Troubleshooting

### Issue: Migration Script Fails

**Symptom**: Script exits with error

**Solution**:
1. Check error message in output
2. Verify database not corrupted: `sqlite3 instance/imagineer.db "PRAGMA integrity_check;"`
3. Restore backup if needed
4. Check Python version: `python --version` (should be 3.12+)
5. Verify dependencies: `pip list`

### Issue: API Won't Start

**Symptom**: `systemctl status imagineer-api` shows failed

**Solution**:
```bash
# Check logs
sudo journalctl -u imagineer-api -n 50

# Common issues:
# - Import error: pip install missing package
# - Port in use: Check port 10050
# - Database error: Verify database file exists
```

### Issue: Frontend Shows Errors

**Symptom**: Console errors or blank page

**Solution**:
1. Check browser console (F12)
2. Verify API is accessible: `curl https://imagineer-api.joshwentworth.com/health`
3. Clear browser cache (Ctrl+Shift+R)
4. Check Firebase deployment logs
5. Verify build succeeded: `ls -la web/dist/`

### Issue: Templates Not Showing

**Symptom**: Templates page is empty

**Solution**:
```bash
# Verify templates in database
python -c "
from server.database import BatchTemplate
from server.api import app
with app.app_context():
    for t in BatchTemplate.query.all():
        print(f'{t.id}: {t.name}')
"

# Re-seed if needed
# (Migration script is idempotent, safe to re-run)
```

---

## Success Criteria

Deployment is successful when:

- ✅ API responds to `/api/batch-templates`
- ✅ Templates page shows 3 templates
- ✅ Albums page shows 9 albums (no templates)
- ✅ Generate form has link to Templates
- ✅ Batch generation creates run records
- ✅ No errors in logs
- ✅ Database has 3 BatchTemplate records
- ✅ Database has 0 template albums
- ✅ All 9 albums have `source_type='manual'`

---

## Post-Deployment Tasks

After successful deployment:

1. **Monitor for 24 hours**:
   - Check logs daily
   - Monitor error rates
   - Watch for user issues

2. **Update Documentation**:
   - Update CLAUDE.md with new workflow
   - Update ARCHITECTURE.md with new models
   - Create user guide for Templates page

3. **Cleanup**:
   - After 30 days, delete old backups
   - Remove old template seeder code (if confirmed stable)

4. **Next Phase**:
   - Plan Phase 2.2: Job Queue Integration
   - Implement actual batch generation
   - Add run history UI

---

## Support Contacts

**Issues**: https://github.com/Jdubz/imagineer/issues
**Documentation**: `/docs/plans/`

---

## Appendix: File Manifest

### Backend Changes
1. `server/database.py` - Added 2 models
2. `server/routes/batch_templates.py` - NEW (7 endpoints)
3. `server/routes/albums.py` - Updated filtering
4. `server/api.py` - Registered blueprint
5. `scripts/migrate_template_album_separation.py` - NEW (migration)

### Frontend Changes
6. `web/src/types/models.ts` - Added 4 interfaces
7. `web/src/lib/api.ts` - Added 7 methods
8. `web/src/pages/BatchTemplatesPage.tsx` - NEW
9. `web/src/components/AlbumsTab.tsx` - Removed template filter, added badges
10. `web/src/components/GenerateForm.tsx` - Removed batch UI
11. `web/src/App.tsx` - Added route

### Documentation
12. `docs/plans/MIGRATION_CONCERNS_ADDRESSED.md`
13. `docs/plans/MIGRATION_COMPLETE.md`
14. `docs/plans/PHASE_2_BACKEND_COMPLETE.md`
15. `docs/plans/PHASE_3_FRONTEND_PROGRESS.md`
16. `docs/plans/IMPLEMENTATION_COMPLETE.md`
17. `docs/DEPLOYMENT_GUIDE.md` (this file)

**Total**: 17 files modified/created

---

**Deployment Guide Version**: 1.0.0
**Last Updated**: 2025-11-04
**Prepared By**: Claude Code (AI Assistant)
