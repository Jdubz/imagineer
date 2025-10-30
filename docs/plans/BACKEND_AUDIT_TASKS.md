# Backend Audit Task List

Generated: October 29, 2025  
Owner: Backend Platform · Status: Draft

## Priority Legend
- **P0 – Critical / shipping blocker**: Must fix before the next production deploy.
- **P1 – High**: Should be scheduled immediately after P0s; meaningful risk or stability impact.
- **P2 – Medium**: Improves resilience or maintainability; schedule in the next cycle.
- **P3 – Low**: Nice-to-haves or follow-up hygiene.

## P0 Tasks
- [x] **Lock down image generation endpoints** *(Oct 29, 2025)*  
  Redis-backed limiter now supplements existing admin gating; responses include `Retry-After` hints. (`server/api.py`, `server/utils/rate_limiter.py`)
- [x] **Externalize training/scraping paths** *(Oct 28, 2025)*  
  Paths hydrate from `config.yaml`/env vars with production safeguards. (`server/tasks/training.py`, `server/tasks/scraping.py`)
- [x] **Add execution guards around long-running subprocesses** *(Oct 29, 2025)*  
  Training and scraping tasks stream output on background threads/selectors, enforce wall/idle timeouts, and terminate hung child processes. (`server/tasks/training.py`, `server/tasks/scraping.py`)
- [x] **Harden image uploads** *(Oct 29, 2025)*  
  Upload API enforces allow-listed extensions, dimensional/byte ceilings, and duplicate-safe filenames. (`server/routes/images.py`)
- [x] **Require production-grade database configuration** *(Oct 29, 2025)*  
  Production boot aborts without `DATABASE_URL`, eliminating silent SQLite fallbacks. (`server/api.py`)

## Recently Completed
- **(Oct 29, 2025)** Rescued mis-encoded Google OAuth callbacks that previously produced `/api/auth/google/%2F…` 404 loops.  
  - Files: `server/api.py`, `tests/backend/test_api.py`  
  - Outcome: Backend now detects the anomalous path, processes the callback, and keeps the popup workflow intact. Added regression test coverage to ensure behaviour remains stable.

## P1 Tasks
1. [x] **Rate-limit expensive admin operations** *(Oct 29, 2025)*  
   - Files: `server/utils/rate_limiter.py`, `server/routes/training.py`, `server/routes/images.py`  
   - Outcome: Introduced reusable Redis-aware helper and enforced limits/concurrency guards on training starts and image uploads, returning consistent 429s with retry hints.

- [x] **Distribute generation rate limits** *(Oct 29, 2025)*  
  - Files: `server/api.py:150-223`, `server/utils/rate_limiter.py`  
  - Status: Completed for `/api/generate` (Redis-backed with local fallback). **Follow-up:** extend limiter helpers to other heavy admin endpoints (`/api/training`, `/api/images/upload`) during the next pass.

3. [x] **Redact internal filesystem details from API responses** *(Oct 29, 2025)*  
    - Files: `server/database.py`, `server/routes/{images,albums,training,scraping}.py`, `server/api.py`  
    - Outcome: Public payloads now expose stable download URLs and storage names while suppressing absolute paths; admin sessions continue to see full locations for operations.

## P2 Tasks
1. **Cache configuration reads with invalidation**  
    - Files: `server/api.py:400-470`, `server/routes/images.py:312`, `server/tasks/*`  
    - Problem: `load_config()` hits disk on every request/task, which is wasteful and risks stale globals (`SETS_DIR`).  
    - Fix: Cache the config with mtime checks or memoization and add an explicit reload hook for admins.

2. **Improve log taxonomy and scrub sensitive payloads**  
    - Files: `server/api.py` (request logging), `server/tasks/*`  
    - Problem: Request logs currently dump method/path only; task logs may contain user prompts or external URLs.  
    - Fix: Add structured logging fields (request ids, user email) and central prompt redaction to avoid leaking PII into CloudWatch/Splunk.

- **Automate artifact lifecycle management** *(in progress)*  
    - Files: `server/tasks/scraping.py`, `server/tasks/training.py`, `server/routes/training.py`, `server/routes/scraping.py`  
    - Status: Added retention-aware purge tasks and admin endpoints to queue cleanups. **Remaining:** wire purge jobs into scheduled automation (Celery beat/crontab) and surface disk utilisation alerts.

4. **Validation for public training run visibility**  
    - File: `server/routes/training.py:28-76`  
    - Problem: Training metadata (names, album composition) is publicly readable; confirm this is intentional or add auth/field filtering.  
    - Fix: Decide policy; if private, wrap in `@require_admin` or redact sensitive columns.

## P3 Tasks
1. **Split monolithic `server/api.py`**  
    - Problem: File exceeds 1,500 lines with mixed responsibilities, making review/testing difficult.  
    - Fix: Extract config, job queue, and auth handlers into dedicated modules and leave Flask app wiring minimal.

2. **Document Celery worker expectations**  
    - Problem: Worker concurrency/memory requirements are implicit. New environments guess at queue definitions.  
    - Fix: Add deployment docs (or Helm values) specifying queue names, prefetch limits, and memory guardrails.
