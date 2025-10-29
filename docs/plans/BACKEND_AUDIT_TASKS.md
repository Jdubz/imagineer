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
  Redis-backed limiter now supplements existing admin gating; responses include  hints. (, )
- [x] **Externalize training/scraping paths** *(Oct 28, 2025)*  
  Paths hydrate from /env vars with production safeguards. (, )
- [x] **Add execution guards around long-running subprocesses** *(Oct 29, 2025)*  
  Training and scraping tasks stream output on background threads/selectors, enforce wall/idle timeouts, and terminate hung child processes. (, )
- [x] **Harden image uploads** *(Oct 29, 2025)*  
  Upload API enforces allow-listed extensions, dimensional/byte ceilings, and duplicate-safe filenames. ()
- [x] **Require production-grade database configuration** *(Oct 29, 2025)*  
  Production boot aborts without , eliminating silent SQLite fallbacks. ()

## Recently Completed
- **(Oct 29, 2025)** Rescued mis-encoded Google OAuth callbacks that previously produced `/api/auth/google/%2F…` 404 loops.  
  - Files: `server/api.py`, `tests/backend/test_api.py`  
  - Outcome: Backend now detects the anomalous path, processes the callback, and keeps the popup workflow intact. Added regression test coverage to ensure behaviour remains stable.

## P1 Tasks
1. **Rate-limit expensive admin operations**  
   - Files: `server/routes/training.py:95-205`, `server/routes/images.py:110-161`  
   - Problem: Admin endpoints can enqueue heavy Celery work or bulk uploads without throttle, allowing accidental or malicious floods.  
   - Fix: Add server-side throttling (Flask-Limiter or NGINX) and queue-depth checks before enqueuing new jobs.

2. **Distribute generation rate limits**  
   - File: `server/api.py:150-223`  
   - Problem: Rate limiting state lives in-process only; with multiple workers attackers can bypass quotas.  
   - Fix: Persist counters in Redis/DB (or another shared store) and enforce per-user quotas across instances.

3. **Redact internal filesystem details from API responses**  
    - Files: `server/api.py:1300-1496`, `server/routes/images.py:250-420`  
    - Problem: Batch and output listing responses return absolute server paths and raw stdout, leaking infrastructure layout and sensitive metadata.  
    - Fix: Return relative URLs or opaque IDs, strip stdout dumps, and restrict path details to admin-only diagnostics.

## P2 Tasks
1. **Cache configuration reads with invalidation**  
    - Files: `server/api.py:400-470`, `server/routes/images.py:312`, `server/tasks/*`  
    - Problem: `load_config()` hits disk on every request/task, which is wasteful and risks stale globals (`SETS_DIR`).  
    - Fix: Cache the config with mtime checks or memoization and add an explicit reload hook for admins.

2. **Improve log taxonomy and scrub sensitive payloads**  
    - Files: `server/api.py` (request logging), `server/tasks/*`  
    - Problem: Request logs currently dump method/path only; task logs may contain user prompts or external URLs.  
    - Fix: Add structured logging fields (request ids, user email) and central prompt redaction to avoid leaking PII into CloudWatch/Splunk.

3. **Automate artifact lifecycle management**  
    - Files: `server/tasks/scraping.py:240-410`, `server/tasks/training.py:32-120`  
    - Problem: Scrape outputs and training datasets accumulate indefinitely with only best-effort cleanup.  
    - Fix: Add periodic cleanup jobs with retention windows and disk utilisation alerts.

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
