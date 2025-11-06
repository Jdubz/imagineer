# Archived Deployment Documentation

**Archived:** 2025-11-05
**Reason:** Obsolete or duplicate documentation cleanup

This directory contains 24 deployment documents that were archived during a comprehensive documentation consolidation. These docs either describe old architectures (Nginx, Celery) or are duplicates of current documentation.

## Why These Were Archived

### 1. Old Architecture (No Longer Used)

**Nginx-based deployment:**
- `PRODUCTION_DEPLOYMENT_GUIDE.md`
- `PRODUCTION_SETUP.md`
- `DEPLOYMENT_GUIDE.md`
- `DEPLOYMENT_QUICK_START.md`

Production now uses Firebase Hosting + Cloudflare Tunnel instead of Nginx.

**Celery workers:**
- `CELERY.md`
- `DEPLOYMENT_CHECKLIST.md` (mentions Celery validation)

Production now uses Python threading instead of Celery for background tasks.

**External dependencies:**
- `WEB_SCRAPING_SIMPLE_FIX.md` (references training-data subprocess)

Scraping now uses internal async implementation (server.scraping package).

### 2. Duplicate Content

Multiple docs covered the same information:
- `FIREBASE_CLOUDFLARE_DEPLOYMENT.md` vs `CURRENT_ARCHITECTURE.md`
- `PRODUCTION_ARCHITECTURE.md` vs `CURRENT_ARCHITECTURE.md`
- `PRODUCTION_README.md` vs `CURRENT_ARCHITECTURE.md`
- `INFRASTRUCTURE_SUMMARY.md` vs `CURRENT_ARCHITECTURE.md`
- `DEPLOYMENT_README.md` vs deployment README
- `FIREBASE_QUICKSTART.md` vs `FIREBASE_SETUP.md`
- `REQUIRED_CREDENTIALS.md` vs `CREDENTIALS_QUICK_REFERENCE.md`
- `DEPLOYMENT_CHEATSHEET.md` (incomplete duplicate)

### 3. Historical/Status Documents

Planning and status docs that served their purpose:
- `DEPLOYMENT_STATUS_AND_NEXT_STEPS.md`
- `DEPLOYMENT_CHANGES_SUMMARY.md`
- `DEPLOYMENT_ORCHESTRATION_COMPLETE.md`
- `DEPLOYMENT_ORCHESTRATION_SUMMARY.md`
- `DEPLOYMENT_ORCHESTRATION.md`
- `API_ROUTING_FIX_SUMMARY.md`
- `FIX_CHECKLIST.md`
- `VERIFICATION_CHECKLIST.md`
- `SECURE_AUTHENTICATION_PLAN.md` (implemented)

These documented the deployment migration process which is now complete.

## Current Documentation

See [docs/deployment/README.md](../README.md) for the consolidated current documentation.

**Essential docs (only 5 remain):**
1. `CURRENT_ARCHITECTURE.md` - Complete production architecture
2. `FIREBASE_SETUP.md` - Frontend deployment
3. `CLOUDFLARE_TUNNEL_SETUP.md` - Backend tunnel setup
4. `GOOGLE_OAUTH_SETUP.md` - Authentication setup
5. `CREDENTIALS_QUICK_REFERENCE.md` - API keys and secrets

## Archived File Count

- **24 files** totaling ~10,000 lines
- **Kept:** 5 essential docs (~2,500 lines)
- **Reduction:** ~75% fewer docs, focusing only on current architecture

## If You Need These

These files are preserved in git history and this archive for reference. However, the information they contain is either:
- Outdated (describes old architecture)
- Duplicate (covered in current docs)
- Historical (deployment process notes)

For current deployment procedures, always refer to the active documentation in `/docs/deployment/`.

## Related Cleanup

This documentation cleanup was part of a larger effort to remove obsolete code and align with current architecture:
- Removed deprecated Nginx configs → `config/deployment/archive/nginx_deprecated/`
- Migrated scraping to internal async implementation (removed external training-data dependency)
- Removed 850+ lines of deprecated scraping code

See commit history for details.
