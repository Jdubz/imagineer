# Backend Outstanding Tasks

**Last Updated:** 2025-10-30
**Status:** 5 tasks remaining (0 Critical, 2 P2, 3 P3) - ✅ Critical + 1 P2 COMPLETED!

## Overview

This document consolidates all outstanding backend tasks from comprehensive audits and status reports. The backend is now **production-ready** with all critical bugs resolved and performance optimizations underway! ✅

**Related Documents:**
- Source: `AUDIT_FINDINGS_SUMMARY.md` - Comprehensive backend audit
- Source: `BACKEND_AUDIT_TASKS.md` - Backend-specific task list
- Source: `CONSOLIDATED_STATUS.md` - Overall project status
- Archive: `AGENT_1_COMPLETION_REPORT.md` - Training/scraping verification

---

## Critical Priority (Blockers)

### CRITICAL: Register Album Blueprint ❗
**Priority:** P0
**Estimated Time:** 5 minutes
**Files:** `/home/jdubz/Development/imagineer/server/api.py`

**Problem:** The `albums_bp` blueprint exists with full functionality (including analytics endpoint) but is never registered in the Flask application. This causes the album analytics endpoint to return 404 despite being fully implemented.

**Impact:**
- Analytics endpoint returns 404 despite being implemented
- 208 lines of duplicate album routes in api.py without analytics

**Location:**
- Endpoint exists: `server/routes/albums.py:84`
- Blueprint NOT imported in: `server/api.py`
- Duplicate routes in: `server/api.py:1418-1625` (without analytics)

**Fix:**
```python
# File: server/api.py

# Line ~156: Add import
from server.routes.albums import albums_bp  # noqa: E402

# Line ~162: Register blueprint
app.register_blueprint(albums_bp)

# Lines 1418-1625: Delete duplicate routes (208 lines)
```

**Testing:**
```bash
# After fix, test analytics endpoint
curl http://localhost:10050/api/albums/1/labeling/analytics
```

**Impact:** Enables analytics endpoint immediately, removes 208 lines of duplicate code, no breaking changes.

**Status:** Not Started
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

### Task #2: Improve Log Taxonomy and Scrub Sensitive Payloads
**Priority:** P2
**Estimated Time:** 1 week
**Files:**
- `server/api.py` (request logging)
- `server/tasks/*`
- `server/logging_config.py`

**Problem:** Request logs currently dump method/path only; task logs may contain user prompts or external URLs.

**Solution:**
- Add structured logging fields (request IDs, user email)
- Central prompt redaction to avoid leaking PII into CloudWatch/Splunk
- Implement log formatters for different environments
- Add log level controls via environment variables

**Tasks:**
- Create PII redaction utility
- Update all logging calls to use structured format
- Add request ID correlation across logs
- Document logging standards

**Status:** Not Started
**Reference:** BACKEND_AUDIT_TASKS.md:48-52

---

### Task #3: Automate Artifact Lifecycle Management
**Priority:** P2
**Estimated Time:** 1 week
**Files:**
- `server/tasks/scraping.py`
- `server/tasks/training.py`
- `server/routes/training.py`
- `server/routes/scraping.py`

**Problem:** Manual cleanup endpoints exist, but automated retention policy not scheduled.

**Current Status:**
- ✅ Retention-aware purge tasks exist
- ✅ Admin endpoints can queue cleanups
- ❌ Not wired into scheduled automation (Celery beat/crontab)
- ❌ No disk utilization alerts

**Solution:**
- Wire purge jobs into Celery beat schedule
- Add disk utilization monitoring
- Surface alerts when storage runs hot
- Document retention policies

**Tasks:**
- Configure Celery beat schedule for daily cleanup
- Add disk space monitoring endpoint
- Implement alerting (email/Slack) for low disk space
- Document cleanup policies in admin guide

**Status:** In Progress
**Reference:** BACKEND_AUDIT_TASKS.md:54-56

---

## Low Priority (4 tasks)

### Task #4: Validation for Public Training Run Visibility
**Priority:** P3
**Estimated Time:** 2-3 days
**File:** `server/routes/training.py:28-76`

**Problem:** Training metadata (names, album composition) is publicly readable; confirm this is intentional or add auth/field filtering.

**Solution:**
- Decide policy: should training runs be public or private?
- If private, wrap in `@require_admin` decorator
- If public, redact sensitive columns (email, album IDs)
- Document decision in API docs

**Status:** Not Started
**Reference:** BACKEND_AUDIT_TASKS.md:58-61

---

### Task #5: Split Monolithic server/api.py
**Priority:** P3
**Estimated Time:** 2-3 weeks
**Files:** `server/api.py` (1,871 lines)

**Problem:** File exceeds 1,500 lines with mixed responsibilities, making review/testing difficult.

**Solution:**
- Extract config loading to `server/config.py`
- Extract job queue to `server/queue.py`
- Extract auth handlers to `server/auth_handlers.py`
- Leave Flask app wiring minimal
- Ensure all imports work correctly
- Update tests to import from new locations

**Impact:**
- Easier code review
- Better test isolation
- Clearer separation of concerns
- Reduced merge conflicts

**Status:** Not Started
**Reference:** BACKEND_AUDIT_TASKS.md:63-66

---

### Task #6: Document Celery Worker Expectations
**Priority:** P3
**Estimated Time:** 1-2 days
**Files:**
- New: `docs/deployment/CELERY.md`
- `README.md` (add reference)

**Problem:** Worker concurrency/memory requirements are implicit. New environments guess at queue definitions.

**Solution:**
- Document queue names and routing
- Document prefetch limits per worker
- Document memory guardrails
- Add Helm values example
- Add systemd service examples
- Document scaling guidelines

**Contents:**
- Queue definitions (default, training, scraping, labeling)
- Recommended worker counts
- Memory requirements per queue
- Monitoring recommendations
- Troubleshooting guide

**Status:** Not Started
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

3. Update API endpoints to handle set-backed albums

4. Add UI for creating/editing set templates

**Status:** Not Started (migration plan documented)
**Reference:** SETS_TO_ALBUMS_MIGRATION.md

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
| P2 (Medium) | ~~3~~ → **2** | ~~3-4 weeks~~ → **2-3 weeks** (1 completed) ✅ |
| P3 (Low) | 3 | 4-6 weeks |
| ~~Additional~~ | ~~1~~ | ~~8-12 hours~~ ✅ VERIFIED Oct 30 |
| **Total** | **~~9~~ → 5** | **~~8-13~~ → 6-9 weeks** |

---

## Recommended Next Actions

### Immediate (This Hour)
1. **CRITICAL:** Register albums_bp blueprint - 5 minutes, unblocks analytics

### This Sprint (2 weeks)
1. **Task #1:** Configuration caching - Improves performance
2. **Bug Report Endpoint:** Complete implementation - Improves observability
3. **Task #3:** Automate artifact cleanup - Prevents disk space issues

### Next Sprint (2 weeks)
1. **Task #2:** Log taxonomy and PII redaction - Improves security
2. **Task #4:** Training run visibility policy - Security decision
3. **Task #6:** Celery documentation - Improves operations

### Long-term (Quarterly)
1. **Task #5:** Split api.py - Improves maintainability
2. **Task #7:** Sets → Albums migration - Feature consolidation

---

## Notes

- **Critical album blueprint bug** must be fixed immediately ❗
- All training/scraping systems verified working as of Oct 28, 2025
- Backend is production-ready except for the blueprint bug
- Most remaining tasks are optimizations and documentation
- Consider business priorities when scheduling P2/P3 work

---

**Document Owner:** Development Team
**Review Frequency:** Monthly for roadmap updates
**Last Audit:** 2025-10-30
