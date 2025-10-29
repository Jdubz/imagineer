# Backend Audit Task List

Generated: October 29, 2025  
Owner: Backend Platform · Status: Draft

## Priority Legend
- **P0 – Critical / shipping blocker**: Must fix before the next production deploy.
- **P1 – High**: Should be scheduled immediately after P0s; meaningful risk or stability impact.
- **P2 – Medium**: Improves resilience or maintainability; schedule in the next cycle.
- **P3 – Low**: Nice-to-haves or follow-up hygiene.

## P0 Tasks
1. **Lock down image generation endpoints**  
   - Files: `server/api.py:873`, `server/api.py:1087`  
   - Problem: `/api/generate` and `/api/generate/batch` accept unauthenticated traffic and only rely on client-side gating. This exposes GPU capacity to anonymous abuse and allows quota bypass.  
   - Fix: Require `@require_admin` (or comparable auth), add CSRF/session checks for embedded UI, and enforce basic rate limiting/server-side quotas.

2. **Externalize training/scraping paths**  
   - Files: `server/tasks/scraping.py:17-27`, `server/tasks/training.py:14-33`  
   - Problem: Hard-coded paths (`/home/jdubz/Development/...` and `/tmp/...`) break outside the original workstation and silently fall back to insecure temp dirs.  
   - Fix: Drive all paths through `config.yaml` + environment overrides, validate existence on startup, and fail fast if misconfigured.

3. **Add execution guards around long-running subprocesses**  
   - Files: `server/tasks/scraping.py:126-214`, `server/tasks/training.py:82-170`  
   - Problem: Celery tasks spawn `python ...` without timeouts, stdout back-pressure handling, or kill-on-failure. Hung processes tie up workers indefinitely.  
   - Fix: Wrap `subprocess.Popen` with explicit timeouts, propagate non-zero exits, and ensure `process.terminate()`/`kill()` executes during cancellation or worker shutdown.

4. **Harden image uploads**  
   - File: `server/routes/images.py:308-361`  
   - Problem: Admin upload accepts arbitrary files with no size cap, mime/extension validation, or content scanning and writes them directly to disk. This is a DoS & storage risk.  
   - Fix: Enforce per-file and aggregate size limits, validate MIME via Pillow before persisting, guard against duplicate filenames, and ensure cleanup on partial failures.

5. **Require production-grade database configuration**  
   - File: `server/api.py:40-52`  
   - Problem: Production silently falls back to SQLite if `DATABASE_URL` is missing. This yields data loss risk and masks misconfiguration.  
   - Fix: On `FLASK_ENV=production`, refuse to boot without an explicit DB URL and document migration path in deployment automation.

## P1 Tasks
6. **Make `users.json` updates atomic**  
   - File: `server/auth.py:52-74`  
   - Problem: Concurrent admin edits rewrite the JSON file without locking, risking corruption.  
   - Fix: Introduce file locks (e.g., `portalocker`) or move roles into the database with proper transactions.

7. **Improve OAuth session integrity**  
   - Files: `server/api.py:210-282`, `server/auth.py:94-141`  
   - Problem: `login_redirect` is stored but never consumed; stale session data lingers, and there is no replay protection on the stored target.  
   - Fix: Remove unused session keys, add nonce/state binding checks, and introduce session rotation after login/logout.

8. **Add structured health and readiness checks**  
   - File: `server/api.py:1500-1588`  
   - Problem: `/api/health` returns minimal info and does not verify DB or Celery connectivity. Observability gaps slow incident response.  
   - Fix: Extend health endpoint (or add `/readyz`) to ping database, Celery broker, and filesystem permissions; integrate with deployment probes.

9. **Rate-limit expensive admin operations**  
   - Files: `server/routes/training.py:95-205`, `server/routes/images.py:308-371`  
   - Problem: Admin endpoints can be spammed (intentional or accidental), queuing large Celery jobs.  
   - Fix: Add server-side throttling (Flask-Limiter or NGINX) and queue-depth checks before enqueuing new jobs.

## P2 Tasks
10. **Cache configuration reads with invalidation**  
    - Files: `server/api.py:400-470`, `server/routes/images.py:312`, `server/tasks/*`  
    - Problem: `load_config()` hits disk on every request/task, which is wasteful and risks stale globals (`SETS_DIR`).  
    - Fix: Cache the config with mtime checks or memoization and add an explicit reload hook for admins.

11. **Improve log taxonomy and scrub sensitive payloads**  
    - Files: `server/api.py` (request logging), `server/tasks/*`  
    - Problem: Request logs currently dump method/path only; task logs may contain user prompts or external URLs.  
    - Fix: Add structured logging fields (request ids, user email) and central prompt redaction to avoid leaking PII into CloudWatch/Splunk.

12. **Automate artifact lifecycle management**  
    - Files: `server/tasks/scraping.py:240-410`, `server/tasks/training.py:32-120`  
    - Problem: Scrape outputs and training datasets accumulate indefinitely with only best-effort cleanup.  
    - Fix: Add periodic cleanup jobs with retention windows and disk utilisation alerts.

13. **Validation for public training run visibility**  
    - File: `server/routes/training.py:28-76`  
    - Problem: Training metadata (names, album composition) is publicly readable; confirm this is intentional or add auth/field filtering.  
    - Fix: Decide policy; if private, wrap in `@require_admin` or redact sensitive columns.

## P3 Tasks
14. **Split monolithic `server/api.py`**  
    - Problem: File exceeds 1,500 lines with mixed responsibilities, making review/testing difficult.  
    - Fix: Extract config, job queue, and auth handlers into dedicated modules and leave Flask app wiring minimal.

15. **Document Celery worker expectations**  
    - Problem: Worker concurrency/memory requirements are implicit. New environments guess at queue definitions.  
    - Fix: Add deployment docs (or Helm values) specifying queue names, prefetch limits, and memory guardrails.

