# Backend Outstanding Tasks

**Last Updated:** 2025-10-30
**Status:** 5 tasks remaining (0 Critical, 0 P2, 5 P3) - ✅ Logging, automation, and label analytics shipped Oct 30
**Recent Update:** Delivered label analytics endpoints alongside log taxonomy/PII scrubbing and automated retention/disk telemetry (Oct 30, 2025)

## Overview

This document consolidates all outstanding backend tasks from comprehensive audits and status reports. The backend is now **production-ready** with all critical bugs resolved and performance optimizations underway! ✅

**Related Documents:**
- Source: `AUDIT_FINDINGS_SUMMARY.md` - Comprehensive backend audit
- Source: `BACKEND_AUDIT_TASKS.md` - Backend-specific task list
- Source: `CONSOLIDATED_STATUS.md` - Overall project status
- Archive: `AGENT_1_COMPLETION_REPORT.md` - Training/scraping verification

---

## Critical Priority (Blockers)

### ✅ CRITICAL: Register Album Blueprint (Completed Oct 30, 2025)
**Priority:** P0  
**Files:** `/home/jdubz/Development/imagineer/server/api.py`

**Resolution:** `albums_bp` is now imported and registered with the Flask app (`server/api.py:153-160`), restoring the analytics endpoint while eliminating the duplicated album routes. Verified in commit `7d9f03b`.

**Regression Test:**
```bash
curl http://localhost:10050/api/albums/1/labeling/analytics
```

**Reference:** AUDIT_FINDINGS_SUMMARY.md:213-236

---

## High Priority

**Status:** All P1 tasks completed! ✅

Recent completions (Oct 29, 2025):
- Rate-limiting for generation endpoints ✅
- Externalized training/scraping paths ✅
- Execution guards around long-running subprocesses ✅
- Hardened image uploads ✅
- Production-grade database configuration enforcement ✅
- Redacted filesystem paths from public API responses ✅
- Rescued mis-encoded Google OAuth callbacks ✅

---

## Medium Priority (2 tasks)

### ✅ Task #1: Cache Configuration Reads with Invalidation (COMPLETED)
**Priority:** P2
**Estimated Time:** 3-5 days
**Completed:** 2025-10-30
**Files:**
- `server/config_loader.py` - Updated with caching logic
- `server/api.py:793-841` - Added admin endpoints

**Problem:** `load_config()` was hitting disk on every request/task, which was wasteful and risked stale globals.

**Solution Implemented:**
- Thread-safe configuration cache with automatic mtime-based invalidation
- Manual cache clearing via `clear_config_cache()`
- Cache statistics via `get_cache_stats()`
- Deep copies returned to prevent cache pollution
- Admin endpoints for cache management

**New Admin Endpoints:**
- `GET /api/admin/config/cache` - View cache statistics
- `POST /api/admin/config/reload` - Force config reload from disk

**Testing:**
- ✅ Config loads on first request and caches
- ✅ Config auto-reloads when file modified (mtime check)
- ✅ Manual reload endpoint clears cache and reloads
- ✅ Deep copies prevent external mutations
- ✅ Thread-safe for concurrent requests

**Benefits:**
- Eliminates expensive disk I/O on every request
- Automatic invalidation keeps config fresh
- Admin control for manual reloads
- Thread-safe implementation

**Status:** ✅ COMPLETED (Commit: 2e21e09)
**Reference:** BACKEND_AUDIT_TASKS.md:43-46

---

### ✅ Task #2: Improve Log Taxonomy and Scrub Sensitive Payloads (Completed Oct 30, 2025)
**Priority:** P2  
**Files:** `server/logging_config.py`, `server/api.py`, `server/utils/logging_utils.py`

**Highlights:**
- Added `RequestContextFilter` to enrich every log line with trace IDs, request metadata, and authenticated user email.
- Centralised PII scrubbing via reusable helpers that redact prompts, payloads, and oversize strings before emission.
- Introduced environment-driven log levels and optional JSON console formatting for parity across environments.
- Normalised request lifecycle logging to emit structured `request.completed` events instead of free-form strings.

**Testing/Observability:** Manual verification via local API smoke tests; automated test suite currently blocked (Flask dependency missing in CI image).

**Status:** ✅ Completed Oct 30, 2025
**Reference:** BACKEND_AUDIT_TASKS.md:48-52

---

### ✅ Task #3: Automate Artifact Lifecycle Management (Completed Oct 30, 2025)
**Priority:** P2  
**Files:** `server/celery_app.py`, `server/tasks/{training,scraping,maintenance}.py`, `server/utils/disk_stats.py`, `server/api.py`

**Highlights:**
- Daily Celery Beat entries now dispatch `purge_stale_training_artifacts` and `purge_stale_scrape_artifacts` with configurable windows.
- Added maintenance task `record_disk_usage` to log snapshots and emit warnings when utilisation breaches thresholds.
- New admin endpoint `GET /api/admin/disk-stats` surfaces live disk metrics for operations teams.
- Introduced reusable disk measurement helpers with `du` fallbacks for consistent reporting across mounts.

**Status:** ✅ Completed Oct 30, 2025
**Reference:** BACKEND_AUDIT_TASKS.md:54-56

---

## Low Priority (4 tasks total; 3 remaining)

### ✅ Task #4: Validation for Public Training Run Visibility (Completed Oct 30, 2025)
**Priority:** P3  
**Files:** `server/routes/training.py`, `tests/backend/test_phase5_training.py`

**Highlights:**
- Added `_serialize_training_run` helper to strip dataset/output paths, training configs, and checkpoints for non-admin responses while retaining full detail for admins.
- Sanitised `/api/training/loras` to hide checkpoint filesystem paths from public callers while still exposing filenames and sizes.
- Expanded training API tests covering both public and admin visibility to lock down the new policy.

**Reference:** BACKEND_AUDIT_TASKS.md:58-61

---

### ✅ Task #5: Split Monolithic server/api.py (Completed Oct 30, 2025)
**Priority:** P3  
**Files:** `server/api.py`, `server/routes/generation.py`, `server/routes/admin.py`, `tests/backend/test_api.py`

**Problem:** `server/api.py` exceeded 1,500 lines with interleaved queue/admin logic, creating merge pressure and opaque coupling.

**Solution:**
- Lifted generation queue + LoRA endpoints into `server/routes/generation.py` blueprint with `/api` prefix.
- Moved configuration/admin maintenance endpoints into `server/routes/admin.py`.
- Registered the new blueprints from `server/api.py`, keeping routing order identical for backwards compatibility.
- Added `/api/health` test coverage to confirm blueprint wiring and queue stats exposure.

**Impact:**
- Reduced `server/api.py` by ~430 lines; central file now focuses on auth/public routes.
- Blueprint separation lets future maintenance touch queue/admin code without risking unrelated merge conflicts.
- Tests cover the health check happy path and core generation/admin blueprint endpoints (`/api/batches`, `/api/loras/*`, `/api/admin/config/*`, `/api/admin/disk-stats`) to guard regressions.

**Reference:** BACKEND_AUDIT_TASKS.md:63-66

---

### ✅ Task #6: Document Celery Worker Expectations (Completed Oct 30, 2025)
**Priority:** P3  
**Files:** `docs/deployment/CELERY.md`, `README.md`

**Highlights:**
- Authored a Celery operations runbook covering queue roles, sizing envelopes, systemd/Kubernetes deployment templates, and monitoring guardrails.
- Captured environment knobs from `server/celery_app.py` (prefetch, time limits, beat schedules) with recommended overrides per environment.
- Added README cross-link under the production deployment section for visibility.

**Reference:** BACKEND_AUDIT_TASKS.md:68-70

---

### Task #7: Implement Sets → Albums Migration
**Priority:** P3
**Estimated Time:** 1-2 weeks
**Files:**
- `server/database.py` - Extend Album model
- New: `scripts/migrate_sets_to_albums.py`
- `server/api.py` - Update endpoints
- `server/routes/albums.py` - Add set template support

**Problem:** CSV-based "sets" system is separate from database-backed "albums" system. A set is conceptually just an album with a generation template.

**Benefits:**
- Set templates can be managed through the UI
- Generated images automatically link to their source album
- Training can use set-based albums directly
- Labeling and NSFW filtering work on set images
- No file system dependency for set configuration

**Solution:**
1. Extend Album model with set template fields:
   - `is_set_template` (boolean)
   - `csv_data` (JSON: list of template items)
   - `base_prompt`, `prompt_template`, `style_suffix`
   - `lora_config` (JSON: array of LoRA configurations)

2. Create migration script to import existing sets

3. **(✅ Oct 30)** Update API endpoints to handle set-backed albums

4. Add UI for creating/editing set templates

**Status:** In Progress (backend schema/API landed Oct 30, 2025)
**Reference:** SETS_TO_ALBUMS_MIGRATION.md

**Progress (Oct 30, 2025):**
- Added set-template columns (`is_set_template`, `csv_data`, `base_prompt`, `prompt_template`, `style_suffix`, `example_theme`, `lora_config`) to `server/database.py` with serialization helpers.
- `/api/albums` now accepts and returns set-template metadata, including filtering via `?is_set_template=` and `album_type`.
- Backend tests (`tests/backend/test_api.py`) cover set-template creation/update flows and ensure normalization of JSON payloads.

---

### Task #8: Legacy Image Import System
**Priority:** P3
**Estimated Time:** 1-2 weeks
**Files:**
- New: `scripts/import_legacy_media.py`
- `server/database.py` - May need manifest table
- `server/routes/albums.py` - Existing album endpoints

**Problem:**
- 181 legacy images in `/mnt/speedy/imagineer/outputs` not in database
- 243 images in `/mnt/speedy/image packs/` reference datasets
- Images not visible in UI, not linked to albums
- Historic generated art and training datasets are orphaned

**Solution:**
1. Build unit-testable import pipeline with collectors/stagers
2. Create manifest system for tracking legacy assets (YAML-based)
3. Implement `scripts/import_legacy_media.py` CLI with stages:
   - Collectors: Scan source folders, emit `LegacyImage` dataclass
   - Stagers: Copy/symlink to `data/legacy/` with deterministic naming
   - Album Resolver: Map to albums (create if missing)
   - Ingest Command: Write DB rows, attach metadata, enqueue thumbnails
4. Map legacy images to albums with metadata preservation
5. Import prompts, LoRA configs, and labels from JSON sidecars

**Target Organization:**
```
data/legacy/
  ├─ singles/           # 55 single-shot generations
  ├─ decks/<slug>/      # Card/tarot deck batches (65 images)
  ├─ zodiac/<slug>/     # Zodiac themed sets (20 images)
  ├─ lora-experiments/  # LoRA test renders (6 images)
  └─ reference-packs/   # Training datasets (243 images)
```

**Album Taxonomy:**
- `Legacy Singles/<YYYY-MM>` - Ad-hoc generations
- `Decks/<deck_slug>` - Card & tarot sets
- `Zodiac/<set_slug>` - Zodiac collections
- `LoRA Experiments/<experiment_slug>` - Test results
- `Reference Packs/<pack_slug>` - Training datasets

**Benefits:**
- Restore historic image visibility in UI
- Enable training on legacy datasets
- Proper album organization for old content
- Preserve generation metadata and provenance
- 424 total images restored to database

**Testing:**
- Unit tests for collectors/stagers/resolvers (no DB I/O)
- Integration tests with test database
- Manifest validation (no orphaned files)
- Duplicate detection via hash or prompt+timestamp

**Status:** Not Started (plan documented)
**Reference:** LEGACY_IMAGE_IMPORT_PLAN.md

---

### ✅ Task #9: Label Analytics Endpoints (Completed Oct 30, 2025)
**Priority:** P2-P3  
**Files:** `server/routes/labels.py`, `server/api.py`, `tests/backend/test_label_analytics.py`

**Highlights:**
- Added dedicated blueprint with `/api/labels/stats`, `/api/labels/top-tags`, and `/api/labels/distribution` endpoints, all admin-gated.
- Each endpoint supports `label_type`, `album_id`, pagination, and public-only filters to mirror UI needs.
- Aggregations expose total/unique label counts, per-image averages, tag frequency percentages, and per-album coverage metrics ready for dashboards.
- New backend tests cover summary stats, tag filtering, and distribution logic with mocked admin auth.

**Status:** ✅ Completed Oct 30, 2025

**Benefits:**
- Better insights for training data quality
- Tag cloud visualizations for frontend
- Label coverage metrics for dataset completeness
- Identify under-labeled or over-labeled images
- Support data-driven labeling workflows

**Status:** Not Started
**Reference:** CONSOLIDATED_STATUS.md Phase 3

---

### ✅ Task #10: Local Disk Usage Statistics (Completed Oct 30, 2025)
**Priority:** P3  
**Files:** `server/utils/disk_stats.py`, `server/api.py`, `server/tasks/maintenance.py`

**Highlights:**
- Delivered admin endpoint `/api/admin/disk-stats` exposing mount utilisation, per-target byte counts, and alert thresholds.
- Added disk measurement helpers with `du -sb` fallbacks to keep reporting accurate across mounted volumes.
- Scheduled `record_disk_usage` maintenance task to log snapshots and emit warnings once utilisation exceeds the configurable 85% threshold.

**Status:** ✅ Completed Oct 30, 2025
**Reference:** CONSOLIDATED_STATUS.md Section 6.4 (simplified)

---

## Additional Backend Tasks (From Other Documents)

### ✅ Bug Report Endpoint Implementation (COMPLETED)
**Source:** BUG_REPORT_IMPLEMENTATION_PLAN.md, BUG_REPORT_TOOL_PLAN.md
**Priority:** Medium
**Verified:** 2025-10-30

**Implementation Status:**
- ✅ Backend `/api/bug-reports` endpoint EXISTS and REGISTERED
- ✅ Trace ID middleware implemented (`server/middleware/trace_id.py`)
- ✅ Structured error responses implemented (`server/utils/error_handler.py`)
- ✅ Frontend components ready to integrate

**Verified Components:**
1. **Trace ID Middleware** - ✅ EXISTS
   - File: `server/middleware/trace_id.py` (1,050 bytes)
   - Adds trace ID to every request/response
   - Included in error responses

2. **Structured Error Responses** - ✅ EXISTS
   - File: `server/utils/error_handler.py` (3,451 bytes)
   - Formats errors with trace_id, error_code, timestamp
   - Consistent error handling across application

3. **Bug Report Endpoint** - ✅ EXISTS and REGISTERED
   - File: `server/routes/bug_reports.py` (204 lines)
   - Endpoint: `POST /api/bug-reports`
   - JSON schema validation implemented
   - File-based storage configured
   - Admin-only restriction enforced
   - Registered in `server/api.py:152,162`

**Status:** ✅ FULLY IMPLEMENTED (verified Oct 30, 2025)
**Reference:** AUDIT_FINDINGS_SUMMARY.md:118-128

---

### NSFW Filter Status Review
**Source:** NSFW_FILTER_STATUS.md
**Status:** Implemented and working ✅

**Components:**
- ✅ Image model has `is_nsfw` flag
- ✅ Public API filters NSFW images
- ✅ Admin API shows all images
- ✅ Claude labeling detects NSFW content
- ✅ Frontend respects NSFW flags

**No action required** - system is complete and operational.

**Reference:** NSFW_FILTER_STATUS.md

---

### Contract Testing Verification
**Source:** CONTRACT_TESTING_INSPECTION_REPORT.md
**Status:** Tests passing, types aligned ✅

**Summary:**
- ✅ Backend/frontend type contracts aligned
- ✅ Contract tests passing
- ✅ Shared schema system working

**No action required** - validation system is working correctly.

**Reference:** CONTRACT_TESTING_INSPECTION_REPORT.md

---

## Completed Tasks (Reference)

### Recently Completed (Oct 28-29, 2025)
1. ✅ **Training Album Persistence Fix**
   - Issue: "No albums specified" error resolved
   - Status: Was already working, just needed verification
   - Reference: AGENT_1_COMPLETION_REPORT.md

2. ✅ **SCRAPED_OUTPUT_PATH Initialization**
   - Issue: Path not initialized properly
   - Status: Was already implemented with fallback logic
   - Reference: AGENT_1_COMPLETION_REPORT.md

3. ✅ **Training Logs Streaming**
   - Issue: Log streaming not working
   - Status: Was already implemented with real-time updates
   - Reference: AGENT_1_COMPLETION_REPORT.md

4. ✅ **LoRA Auto-Registration**
   - Issue: Trained LoRAs not automatically registered
   - Status: Was already implemented with index.json updates
   - Reference: AGENT_1_COMPLETION_REPORT.md

5. ✅ **Training Directory Cleanup**
   - Issue: Temporary files not cleaned up
   - Status: Was already implemented in finally block
   - Reference: AGENT_1_COMPLETION_REPORT.md

6. ✅ **Database Migration Fix**
   - Issue: SQLite database tracked in git causing dirty status
   - Status: Removed from git, added to .gitignore
   - Reference: DATABASE_MIGRATION_FIX.md (archived)

7. ✅ **OAuth HTTPS Fix**
   - Issue: OAuth callbacks using http:// instead of https://
   - Status: Added ProxyFix middleware, fixed production URLs
   - Reference: PRODUCTION_FIXES.md (archived)

8. ✅ **Rate Limiting Implementation**
   - Issue: No rate limits on expensive operations
   - Status: Redis-backed limiter with local fallback
   - Reference: BACKEND_AUDIT_TASKS.md

9. ✅ **Execution Guards for Subprocesses**
   - Issue: Long-running processes could hang
   - Status: Timeouts and termination implemented
   - Reference: BACKEND_AUDIT_TASKS.md

10. ✅ **Image Upload Hardening**
    - Issue: Insufficient validation on uploads
    - Status: Extension whitelist, size limits, duplicate-safe filenames
    - Reference: BACKEND_AUDIT_TASKS.md

---

## Summary by Priority

| Priority | Count | Estimated Time |
|----------|-------|----------------|
| ~~P0 (Critical)~~ | ~~1~~ | ~~5 minutes~~ ✅ COMPLETED Oct 30 |
| P2 (Medium) | ~~3~~ → ~~1~~ → 0 | ✅ Completed Oct 30 |
| P3 (Low) | ~~3~~ → ~~4~~ → ~~3~~ → **2** | **2-3 weeks** (Tasks #7-#8) |
| ~~Additional~~ | ~~1~~ | ~~8-12 hours~~ ✅ VERIFIED Oct 30 |
| **Total** | **~~9~~ → ~~5~~ → 4 → 3 → 2** | **~~8-13~~ → ~~6-9~~ → ~~4-6~~ → ~~3-4~~ → 2-3 weeks** |

**Note:** 3 additional tasks discovered from docs/plans review (Oct 30, 2025). OpenAPI/Swagger and complex monitoring removed per requirements.

---

## Recommended Next Actions

### ✅ Completed This Session
1. ~~**Task #2:** Log taxonomy & PII scrubbing~~ - DONE (Oct 30, 2025)
2. ~~**Task #3:** Automate artifact lifecycle~~ - DONE (Oct 30, 2025)
3. ~~**Task #9:** Label analytics endpoints~~ - DONE (Oct 30, 2025)
4. ~~**Task #10:** Local disk usage statistics~~ - DONE (Oct 30, 2025)
5. ~~**Task #6:** Celery worker expectations~~ - DONE (Oct 30, 2025)

### Upcoming Focus - High-value P3 Tasks
1. **Task #7:** Sets → Albums migration - Feature consolidation
2. **Task #8:** Legacy image import - Restore 424 historic images

## Notes

- ✅ **Critical album blueprint bug FIXED** (Oct 30, 2025 - Commit: 7d9f03b)
- ✅ **Configuration caching implemented** (Oct 30, 2025 - Commit: 2e21e09)
- All training/scraping systems verified working as of Oct 28, 2025
- Backend is **production-ready** with all P0/P1 tasks completed
- 2 remaining tasks: both P3 (2-3 weeks)
- Recent additions (Oct 30, 2025):
  - Legacy image import (424 images to restore)
- Removed unnecessary tasks:
  - OpenAPI/Swagger documentation (not needed)
- Completed Oct 30, 2025: Generation + admin blueprints extracted (`server/routes/{generation,admin}.py`) with `/api/health` regression tests covering queue stats.
- Completed Oct 30, 2025: Celery runbook added (`docs/deployment/CELERY.md`) with README linkage and operations guidance.
- Disk telemetry now lives in `/api/admin/disk-stats`; consider extending to alerting integrations if needed
- Consider business priorities when scheduling remaining P3 work

---

**Document Owner:** Development Team
**Review Frequency:** Monthly for roadmap updates
**Last Audit:** 2025-10-30
