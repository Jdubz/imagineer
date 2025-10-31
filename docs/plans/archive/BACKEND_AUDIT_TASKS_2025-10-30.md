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
1. **Cache configuration reads with invalidation** ✅ *(Completed Oct 30, 2025)*  
    - Files: `server/api.py:400-470`, `server/routes/images.py:312`, `server/tasks/*`  
    - Problem: `load_config()` hits disk on every request/task, which is wasteful and risks stale globals (`SETS_DIR`).  
    - Fix: Cache the config with mtime checks or memoization and add an explicit reload hook for admins.

2. **Improve log taxonomy and scrub sensitive payloads** ✅ *(Completed Oct 30, 2025)*  
    - Files: `server/api.py` (request logging), `server/tasks/*`  
    - Problem: Request logs currently dump method/path only; task logs may contain user prompts or external URLs.  
    - Fix: Add structured logging fields (request ids, user email) and central prompt redaction to avoid leaking PII into CloudWatch/Splunk.

- **Automate artifact lifecycle management** ✅ *(Completed Oct 30, 2025)*  
    - Files: `server/tasks/scraping.py`, `server/tasks/training.py`, `server/routes/training.py`, `server/routes/scraping.py`  
    - Status: Daily Celery beat schedule now dispatches purge tasks; maintenance job records disk usage and emits alerts via logging.

4. **Validation for public training run visibility** ✅ *(Completed Oct 30, 2025)*  
    - File: `server/routes/training.py:28-220`  
    - Outcome: Added sanitisation layer that hides dataset/output paths, training configs, and checkpoints for non-admin users while retaining full detail for administrators. `/api/training/loras` now omits filesystem paths for public callers.

## P3 Tasks
1. [x] **Split monolithic `server/api.py`** *(Completed Oct 30, 2025)*  
   - Files: `server/routes/generation.py`, `server/routes/admin.py`, `server/api.py`, `tests/backend/test_api.py`  
   - Outcome: Queue/admin endpoints now live in dedicated blueprints with preserved routing order; `/api/health` test verifies registration and queue stats wiring.

2. [x] **Document Celery worker expectations** *(Completed Oct 30, 2025)*  
    - Files: `docs/deployment/CELERY.md`, `README.md`  
    - Outcome: Published queue sizing & deployment runbook with systemd/Helm examples and linked it from the deployment docs for operators.

- **Update Oct 30, 2025:** Album schema/API now exposes set-template metadata (`server/database.py`, `server/routes/albums.py`, `tests/backend/test_api.py`) with migration tooling still pending.
