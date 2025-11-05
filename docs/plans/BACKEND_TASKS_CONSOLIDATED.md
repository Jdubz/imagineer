# Backend Tasks - Consolidated & Verified

**Last Updated:** 2025-11-05 (Updated with LoRA Training priorities)
**Status:** Active - Reflecting correct feature priorities
**Context:** Solo developer with AI assistance

This document consolidates all outstanding backend tasks, organized by the actual feature priorities:
1. Web Scraping (internalize from training-data)
2. Image Upload
3. Labeling System
4. Training Pipeline

**See:** `LORA_TRAINING_IMPLEMENTATION_PLAN.md` for detailed implementation plan

---

## 🔴 Priority P0 - Critical (Feature Priority 1: Web Scraping)

### B-P0-1: Internalize Web Scraping from Training-Data
**Source:** LORA_TRAINING_IMPLEMENTATION_PLAN.md Phase 1
**Status:** ✅ **COMPLETED** (2025-11-05)
**Effort:** 7-8 days (actual: completed in session)
**Files:** `server/scraping/` (new package), `server/tasks/scraping_new.py`

**Current State:**
- ✅ **Scraping internalized - no external dependency**
- ✅ Scraping UI exists (ScrapingTab.tsx - 683 lines)
- ✅ Database models exist (ScrapeJob, Album)
- ✅ Internal scraping implementation complete

**Completed Tasks:**
- [x] Add dependencies to requirements.txt (playwright, httpx, beautifulsoup4, lxml, imagehash, aiofiles)
- [x] Create `server/scraping/` package structure
- [x] Copy and adapt core classes:
  - [x] `config.py` - Pydantic configuration models
  - [x] `models.py` - ImageMetadata, ScrapingSession
  - [x] `crawler.py` - WebCrawler (Playwright + BeautifulSoup)
  - [x] `downloader.py` - ImageDownloader (httpx async)
  - [x] `validator.py` - ImageValidator (dimensions, format)
  - [x] `deduplicator.py` - ImageDeduplicator (perceptual hashing)
- [x] Create `server/tasks/scraping_new.py` - New async implementation
- [x] Export new implementation from `server/tasks/scraping.py`
- [x] Update `config.yaml` - Removed `scraping.training_data_repo`
- [x] Tested with World of Playing Cards site

**Remaining Work:**
- [ ] Remove old `_get_training_data_repo()` function (backward compat kept for now)
- [ ] Test with all sites from `docs/card_sites.json`
- [ ] Add comprehensive tests for scraping pipeline

**Notes:**
- Old implementation kept for backward compatibility
- New implementation exported as default: `scrape_site_async`, `_scrape_site_internal`
- HTML metadata extraction working (alt_text, title, captions)

---

### B-P0-2: Production/Dev Environment Cleanup
**Source:** IMPROVEMENT_TASKS_2025Q1.md #2, DEVELOPMENT_WORKFLOW.md
**Status:** ✅ **COMPLETED** (2025-11-05)
**Effort:** 1 day (actual: ~2 hours)
**Files:** `server/api.py`, `.git/hooks/pre-commit`, `docs/deployment/DEPLOYMENT_CHECKLIST.md`

**Current State:**
- ✅ Development server created (`./run-dev.sh`)
- ✅ Separate configs exist
- ✅ Documentation complete
- ✅ Runtime environment validation on startup
- ✅ Health endpoint shows environment and branch
- ✅ Pre-commit hooks prevent production config edits
- ✅ CI/CD enforces main branch deployment

**Completed Tasks:**
- [x] Add environment indicator to `/api/health` response (server/api.py:616-617)
  - Shows `environment: "production"` or `"development"`
  - Shows `branch: "main"` or current git branch
- [x] Add runtime environment validation (server/api.py:167-224)
  - Validates production runs on port 10050 with config.yaml
  - Validates development cannot use port 10050
  - Warns if production branch is not 'main'
  - Exits with clear errors on misconfiguration
- [x] Enhance pre-commit hook to prevent production config edits
  - Blocks `config.yaml` modifications on non-main branches
  - Blocks `.env.production` modifications on non-main branches
  - Prevents committing production database
- [x] Document deployment checklist (docs/deployment/DEPLOYMENT_CHECKLIST.md)
  - Pre-deployment verification
  - Post-deployment validation
  - Rollback procedures
  - Emergency contacts

**Remaining Tasks:**
- [ ] Clean up production uncommitted changes (manual - needs production access)
- [ ] Verify production is on main branch (manual - needs production access)
- [ ] Configure GitHub branch protection rules (manual - web UI)

**Acceptance Criteria:**
- ✅ Production only runs main branch code (enforced by CI/CD)
- ✅ Health endpoint shows environment and branch
- ✅ Pre-commit hooks prevent accidents
- ✅ Deployment process documented

---

## 🟡 Priority P1 - High (Feature Priority 2: Image Upload)

### B-P1-1: Image Upload Backend
**Source:** LORA_TRAINING_IMPLEMENTATION_PLAN.md Phase 2.1
**Status:** ⏳ Not started
**Effort:** 1-2 days
**Files:** `server/routes/images.py`

**Tasks:**
- [ ] Create `POST /api/images/upload` endpoint
  - [ ] Accept multiple files via multipart/form-data
  - [ ] Support album_id (existing) or album_name (new)
  - [ ] Validate file types (jpg, png, webp, gif, bmp)
  - [ ] Generate thumbnails
  - [ ] Create Image and AlbumImage records
- [ ] Create `POST /api/images/bulk-upload` endpoint
  - [ ] Background Celery task for large uploads
  - [ ] Progress tracking
  - [ ] Return job_id for monitoring
- [ ] Add file size limits and validation
- [ ] Implement storage handling (save to configured directory)

**Acceptance Criteria:**
- Single file upload works
- Bulk upload works with progress tracking
- Images saved to correct album
- Thumbnails generated
- Error handling for invalid files

---

### B-P1-2: Enhanced Labeling Backend
**Source:** LORA_TRAINING_IMPLEMENTATION_PLAN.md Phase 3.1
**Status:** ⚠️ Basic structure exists, needs full implementation
**Effort:** 2-3 days
**Files:** `server/tasks/labeling.py`, `server/services/labeling_cli.py`

**Current State:**
- ✅ Claude CLI Docker integration exists
- ✅ Label database model exists
- ⚠️ Labeling task incomplete
- ❌ No batch album labeling
- ❌ NSFW detection not implemented

**Tasks:**
- [ ] Complete `label_image_task()` implementation
  - [ ] Enhanced Claude prompts for card imagery
  - [ ] Parse JSON response (caption, nsfw, tags, confidence)
  - [ ] Create multiple Label records per image
  - [ ] Set `image.is_nsfw` flag
- [ ] Implement `label_album_task()` for batch processing
  - [ ] Queue labeling for unlabeled images
  - [ ] Optional force re-label
  - [ ] Progress tracking
- [ ] Add `POST /api/images/<id>/label` endpoint
- [ ] Add `POST /api/albums/<id>/label` endpoint
- [ ] Add `GET /api/images/<id>/labels` endpoint
- [ ] Add `PATCH /api/images/<id>/labels/<id>` (edit label)
- [ ] Add `DELETE /api/images/<id>/labels/<id>` (remove label)
- [ ] Update Claude system prompt for better captions

**Acceptance Criteria:**
- Images can be labeled individually
- Albums can be batch-labeled
- NSFW detection working
- Tags/keywords extracted
- Labels can be manually edited/deleted
- Caption quality suitable for training

---

## 🟢 Priority P2 - Medium (Feature Priority 4: Training Pipeline)

### B-P2-1: Fix Training Dataset Preparation
**Source:** LORA_TRAINING_IMPLEMENTATION_PLAN.md Phase 4.1
**Status:** ⚠️ Bug - incorrect directory structure
**Effort:** 1 day
**Files:** `server/tasks/training.py:434-518`

**The Problem:**
Current implementation creates `images/` and `captions/` subdirectories, but SD 1.5 expects flat structure with paired files:
```
training_dir/
├── image_0001.jpg
├── image_0001.txt  # Caption file
├── image_0002.png
├── image_0002.txt
```

**Tasks:**
- [ ] Fix `prepare_training_data()` to create flat SD 1.5 format
- [ ] Use sequential naming (image_0001, image_0002, ...)
- [ ] Validate all images have captions before copying
- [ ] Add minimum image count validation (20 images)
- [ ] Add warning for small datasets (< 50 images)
- [ ] Test with `examples/train_lora.py`

**Acceptance Criteria:**
- Training dataset in correct SD 1.5 format
- Only captioned images included
- Validation prevents bad training runs
- Compatible with `examples/train_lora.py`

---

### B-P2-2: Remove is_training_source Flag
**Source:** LORA_TRAINING_IMPLEMENTATION_PLAN.md Phase 4.2
**Status:** ⏳ Not started
**Effort:** 1 day
**Files:** `server/database.py`, `server/routes/training.py`

**The Problem:**
Albums shouldn't have a pre-set "training source" flag. Training runs should directly select any albums with properly labeled images.

**Tasks:**
- [ ] Create database migration to drop `is_training_source` column
- [ ] Update `Album.to_dict()` to remove field
- [ ] Update `GET /api/training/albums` endpoint
  - [ ] Return ALL albums (not filtered by flag)
  - [ ] Add metadata: `total_images`, `labeled_images`, `ready_for_training`
  - [ ] Filter by source_type if desired
- [ ] Update frontend schemas to remove field
- [ ] Run migration in development
- [ ] Test training run creation

**Acceptance Criteria:**
- `is_training_source` column removed
- Training run can select any albums
- API shows labeling status per album
- Frontend updated

---

### B-P2-3: Enhanced Training Configuration
**Source:** LORA_TRAINING_IMPLEMENTATION_PLAN.md Phase 4.3
**Status:** ⏳ Not started
**Effort:** 1 day
**Files:** `server/routes/training.py`, `config.yaml`

**Tasks:**
- [ ] Add training parameter validation to `create_training_run()`
  - [ ] Validate albums have sufficient labeled images
  - [ ] Check minimum total image count (20)
  - [ ] Warn if < 50 images
- [ ] Support enhanced training config parameters:
  - [ ] steps (default: 1500, range: 500-5000)
  - [ ] rank (default: 8, range: 4-32)
  - [ ] alpha (default: 32)
  - [ ] learning_rate (default: 1e-4)
  - [ ] warmup_steps (default: 100)
  - [ ] gradient_accumulation_steps (default: 4)
  - [ ] random_flip (default: true)
  - [ ] center_crop (default: true)
- [ ] Add training config defaults to `config.yaml`
- [ ] Add cost/time estimation (optional)

**Acceptance Criteria:**
- Training runs validate album selection
- Enhanced parameters supported
- Defaults configurable in config.yaml
- Validation prevents bad configurations

---

### B-P2-4: Expand Shared Contract Coverage
**Source:** BACKEND_TASKS.md B-3
**Status:** ⏳ Not started
**Effort:** 2-3 days
**Files:** `shared/schema/`, `tests/backend/test_shared_contracts.py`

**Current State:**
- ✅ Contract tests exist for auth_status, job, jobs_response, bug_report
- ❌ Missing schemas for album_detail, queue_job, training_status, scraping_job

**Tasks:**
- [ ] Create JSON schemas for high-traffic payloads:
  - [ ] `album_detail_response.json`
  - [ ] `queue_job_response.json`
  - [ ] `training_status_response.json`
  - [ ] `scraping_job_response.json`
- [ ] Run `scripts/generate_shared_types.py`
- [ ] Update backend contract tests
- [ ] Update frontend contract tests

**Acceptance Criteria:**
- All major API responses have schemas
- Contract tests validate schemas
- Frontend types auto-generated from schemas

---

## 🔵 Priority P3 - Low

### B-P3-1: API Rate Limiting
**Source:** IMPROVEMENT_TASKS_2025Q1.md #10
**Status:** ⏳ Not started
**Effort:** 2-3 days
**Files:** `server/middleware/`, `server/utils/rate_limiter.py`

**Current State:**
- ✅ Rate limiter utility exists (`server/utils/rate_limiter.py`)
- ❌ Not applied to endpoints
- ❌ No per-user limits

**Tasks:**
- [ ] Apply rate limiting to generation endpoints
- [ ] Add per-user rate limits (not just IP)
- [ ] Add rate limit headers to responses
- [ ] Add rate limit exceeded responses
- [ ] Document rate limits
- [ ] Add admin bypass for rate limits

**Acceptance Criteria:**
- Generation endpoints rate limited
- Per-user limits enforced
- Rate limit info in responses

---

### B-P3-2: Performance Optimization
**Source:** IMPROVEMENT_TASKS_2025Q1.md #8
**Status:** ⏳ Not started
**Effort:** 1 week
**Files:** Various

**Tasks:**
- [ ] Add database indexes for common queries
- [ ] Implement Redis caching for expensive queries
- [ ] Add pagination to all list endpoints (verify current state)
- [ ] Profile and optimize slow endpoints
- [ ] Add database connection pooling
- [ ] Implement API response compression
- [ ] Add query optimization for album detail

**Acceptance Criteria:**
- All list endpoints paginated
- Common queries use indexes
- Response times improved

---

### B-P3-3: Enhanced Monitoring
**Source:** IMPROVEMENT_TASKS_2025Q1.md #9
**Status:** ⏳ Not started
**Effort:** 1 week

**Tasks:**
- [ ] Set up Prometheus metrics export
- [ ] Add structured logging (JSON format)
- [ ] Implement distributed tracing
- [ ] Add error tracking (Sentry)
- [ ] Create alerting rules
- [ ] Document monitoring setup

---

### B-P3-4: Legacy Import Observability
**Source:** BACKEND_TASKS.md B-4
**Status:** ⏳ Not started
**Effort:** 2-3 days
**Files:** `server/legacy_import/`, `scripts/import_legacy_media.py`

**Current State:**
- ✅ Legacy importer functional
- ✅ Summary files written
- ❌ No visibility into completed imports
- ❌ No reconciliation tools

**Tasks:**
- [ ] Add `/api/admin/legacy-imports` endpoint to list imports
- [ ] Add `/api/admin/legacy-imports/<id>/summary` for details
- [ ] Add CLI command to show import history
- [ ] Document import reconciliation procedure
- [ ] Add metrics/structured logs

**Acceptance Criteria:**
- Can view import history via API
- Reconciliation process documented
- Import metrics available

---

## 📋 Completed (Archive Ready)

### ✅ B-DONE-1: Bug Report Review & Retention Tooling
**Completed:** 2025-11-01
**Source:** BACKEND_TASKS.md B-1
**Move to:** `archive/2025-11-05/BUG_REPORT_IMPLEMENTATION_PLAN.md`

### ✅ B-DONE-2: Album Integration for Generated Images
**Completed:** 2025-11-03
**Source:** BACKEND_TASKS.md B-2
**Move to:** `archive/2025-11-05/ALBUM_INTEGRATION_COMPLETE.md`

---

## 📊 Summary

| Priority | Total | Not Started | In Progress | Completed | Blocked |
|----------|-------|-------------|-------------|-----------|---------|
| P0 (Critical) | 2 | 0 | 0 | **2** ✅ | 0 |
| P1 (High) | 2 | 2 | 0 | 0 | 0 |
| P2 (Medium) | 4 | 4 | 0 | 0 | 0 |
| P3 (Low) | 4 | 4 | 0 | 0 | 0 |
| **Total** | **12** | **10** | **0** | **2** | **0** |

**Recent Completions (2025-11-05):**
- ✅ B-P0-1: Web Scraping Internalization (7-8 days → completed in session)
- ✅ B-P0-2: Production/Dev Environment Enforcement (~2 hours)

**Next Priority:** B-P1-1 Image Upload Backend (1-2 days)

**Next Review:** After completing P1 tasks or 2025-11-12, whichever comes first

---

**Notes:**
- **Training-data dependency removed** - Scraping will be internal
- **Priority order reflects actual feature importance** - Scraping → Upload → Labeling → Training
- All tasks verified against codebase as of 2025-11-05
- See `LORA_TRAINING_IMPLEMENTATION_PLAN.md` for detailed implementation guide
- Solo developer context - focused on core feature completion

