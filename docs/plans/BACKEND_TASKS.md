# Backend Task Backlog (Updated 2025-11-01)

Completed items from the previous backlog have been moved to `docs/plans/archive/BACKEND_TASKS_2025-10-31.md`. The list below reflects the remaining work discovered while reviewing the codebase on 2025-11-01.

## Priority P1

### B-1: Ship Bug Report Review & Retention Tooling
- **Why it matters:** Admins can submit detailed bug reports (`server/routes/bug_reports.py`), but there is no supported workflow to list, triage, or expire them. Reports will accumulate indefinitely on disk.
- **Current state:**
  - Only a POST handler exists; no CLI or API for listing or marking reports resolved.
  - No retention job deletes reports older than the configured window (`config.yaml` declares `retention_days`, but nothing consumes it).
- **Definition of done:**
  1. Provide either a CLI (`scripts/bug_reports.py`) or authenticated admin endpoints to list, filter, and update report status.
  2. Implement a retention process (Celery beat or cron-friendly CLI) that purges reports older than the configured threshold.
  3. Document the review workflow in `docs/guides/BUG_REPORT_WORKFLOW.md`.
  4. Add unit/contract tests covering the new endpoints or CLI helpers.

## Priority P2

### B-2: Finalise Sets → Albums Migration Operational Script
- **Why it matters:** The database schema and API already model set templates, but there is no runnable migration script to import existing CSV-based sets. Operators still rely on manual steps.
- **Current state:**
  - Docs describe `scripts/migrate_sets_to_albums.py`, yet no script exists in `scripts/`.
  - `server/database.py` and `server/routes/albums.py` expose the necessary fields.
- **Definition of done:**
  1. Implement the migration CLI that reads legacy CSV manifests and creates matching albums plus template rows.
  2. Provide dry-run and idempotent behaviour so the script can be re-run safely.
  3. Add integration coverage (or at minimum unit tests with a temporary SQLite database) to confirm data is imported as expected.
  4. Update operator docs with execution instructions and rollback guidance.

### B-3: Expand Shared Contract Coverage Beyond Core Auth/Jobs
- **Why it matters:** Contract tests currently cover `auth_status`, `job`, `jobs_response`, and bug-report submissions. High-traffic payloads such as album detail responses remain unchecked, increasing drift risk between backend and frontend.
- **Current state:**
  - `shared/schema/` lacks entries for album detail, queue job receipt, training status, etc.
  - `tests/backend/test_shared_contracts.py` only validates the four existing schemas.
- **Definition of done:**
  1. Author JSON Schemas for `album_detail`, `queue_job`, `training_status`, and other priority responses.
  2. Regenerate shared types (`scripts/generate_shared_types.py`) and ensure the frontend (`web/src/types/shared.ts`) consumes them.
  3. Extend backend contract tests to validate the new schemas against live endpoints.
  4. Update frontend contract tests (`web/src/__tests__/sharedContract.test.ts`) to assert parity.

## Priority P3

### B-4: Legacy Import Observability & Dashboards
- **Why it matters:** The legacy importer (`scripts/import_legacy_media.py`) can ingest assets, but there is no visibility into staging or ingestion runs once they complete.
- **Current state:**
  - `server/legacy_import/stager.py` writes summary files, yet nothing surfaces them to operators or Grafana/Prometheus.
  - No docs explain how to audit completed imports or reconcile staged assets with database rows.
- **Definition of done:**
  1. Add a CLI or admin endpoint to report the most recent import summary and discrepancies.
  2. Document the standard operating procedure for re-running imports and verifying album exposure in the UI.
  3. Optional: emit structured logs/metrics that can feed dashboards.

---

**Next review:** Revisit after delivering B-1 and B-2, or by 2025-11-22.
