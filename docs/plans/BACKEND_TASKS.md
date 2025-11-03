# Backend Task Backlog (Updated 2025-11-01)

Completed items from the previous backlog have been moved to `docs/plans/archive/BACKEND_TASKS_2025-10-31.md`. The list below reflects the remaining work discovered while reviewing the codebase on 2025-11-01.

## Priority P1

### B-1: Ship Bug Report Review & Retention Tooling ✅ (Delivered 2025-11-01)
- Admin REST endpoints + CLI now cover listing, detail, status updates, deletion, and retention purges.
- Celery task `server.tasks.bug_reports.purge_stale_reports` honours `bug_reports.retention_days`.
- Documentation updated (`docs/guides/BUG_REPORT_WORKFLOW.md`) with new workflow and CLI usage.
- Tests added in `tests/backend/test_bug_reports.py` to cover list/detail/update/delete/purge paths.

## Priority P2

### B-2: Album Integration for Generated Images ✅ (Delivered 2025-11-03)
- **Status:** Complete - All generated images now automatically link to albums, legacy images imported
- **What was delivered:**
  1. **Automatic Album Linking** - Added `_create_image_record()` in `server/routes/generation.py` that creates Image and AlbumImage records after successful generation
  2. **Legacy Import Script** - Created `scripts/import_legacy_generations.py` with dry-run mode, idempotent operation, and metadata preservation
  3. **Test Coverage** - Added `tests/backend/test_album_integration.py` with 4 comprehensive tests (all passing)
  4. **Data Migration Complete** - Verified 165 legacy images already imported into 8 albums with full metadata
- **Files modified:**
  - `server/routes/generation.py` (+107 lines) - Album integration logic
  - `scripts/import_legacy_generations.py` (new, 312 lines) - Import utility
  - `tests/backend/test_album_integration.py` (new, 190 lines) - Test coverage
- **Database state:** 166 total images, 11 albums, 165 album-image links
- **Architecture clarification:** CSV sets remain as generation templates; albums are the OUTPUT of batch generation

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
