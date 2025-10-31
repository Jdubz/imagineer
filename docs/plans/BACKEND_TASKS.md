# Backend Outstanding Tasks (Active)

**Last Updated:** 2025-10-31  
**Status:** 5 tasks remaining (1 P2, 4 P3)

All previously completed backend tasks have been archived in `docs/plans/archive/BACKEND_TASKS_2025-10-30.md`. This document now tracks only the remaining work still in flight.

---

## Remaining Task List

### Task #7: Implement Sets → Albums Migration
**Priority:** P3  
**Estimated Time:** 1-2 weeks  
**Files:**  
- `server/database.py` – Extend Album model  
- New: `scripts/migrate_sets_to_albums.py`  
- `server/api.py` – Update endpoints  
- `server/routes/albums.py` – Add set template support

**Problem:** CSV-based "sets" are disconnected from the database-backed album system.

**Benefits:**  
- Set templates manageable via UI  
- Generated images tied to source album  
- Training can reuse set-based albums  
- NSFW filtering/labeling operate on set images  
- Eliminates filesystem dependency for set metadata

**Plan:**  
1. Extend Album model with set-template fields (`is_set_template`, `csv_data`, `base_prompt`, `prompt_template`, `style_suffix`, `lora_config`).  
2. Create migration script to import existing sets.  
3. Update API endpoints to read/write set-template metadata.  
4. Add UI for creating/editing set templates.

**Current Status (Oct 30, 2025):**  
- Backend schema and serialization completed (`server/database.py`).  
- `/api/albums` exposes template metadata and filtering.  
- Tests cover set-template CRUD and filtering paths (`tests/backend/test_api.py`).  
- Migration script + UI backlog remains.

**Reference:** `docs/plans/SETS_TO_ALBUMS_MIGRATION.md`

---

### Task #8: Legacy Image Import System
**Priority:** P3  
**Estimated Time:** 1-2 weeks  
**Files:**  
- New: `scripts/import_legacy_media.py`  
- `server/database.py` – Manifest/table updates  
- `server/routes/albums.py` – Album endpoints

**Problem:** Hundreds of historic images live outside the database, invisible to the UI and downstream pipelines.

**Plan:**  
1. Build collectors/stagers to discover assets and normalise metadata.  
2. Create YAML manifest tracking for legacy assets.  
3. Implement CLI that stages, resolves albums, ingests DB rows, and queues thumbnails.  
4. Preserve prompts, LoRA configs, labels from sidecars; organise output under `data/legacy/`.

**Target Layout:**
```
data/legacy/
  ├─ singles/
  ├─ decks/<slug>/
  ├─ zodiac/<slug>/
  ├─ lora-experiments/
  └─ reference-packs/
```

**Benefits:** Restores historic visibility, enables model retraining on legacy sets, and centralises provenance data.

**Open Work:** Finalise ingestion CLI, backfill database rows, and wire UI discovery once the data import lands.

---

### Task #9: Automate Scrape & Training Maintenance Jobs
**Priority:** P3  
**Estimated Time:** 1-2 days  
**Files:**  
- New/updated: `server/tasks/maintenance.py`, Celery beat schedule  
- `server/tasks/scraping.py`, `server/tasks/training.py` – Hook purge helpers  
- Ops docs for disk alerting

**Problem:** Scrape artifact cleanup and training directory purges are manual. Without automation, NVMe volumes can fill up and there is no proactive alerting.

**Plan:**  
1. Schedule Celery beat tasks that call the existing purge helpers for scraping outputs and stale training runs.  
2. Emit disk utilisation metrics/log lines so monitoring can alert when free space thresholds are breached.  
3. Provide configuration toggles/dry-run mode for staging environments.

**Reference:** `docs/plans/CONSOLIDATED_STATUS.md`

---

### Task #10: Build Bug Report Review Tooling & Retention
**Priority:** P2  
**Estimated Time:** 2 days  
**Files:**  
- New: `scripts/bug_reports.py` (CLI) or admin-only Flask endpoints  
- `server/routes/bug_reports.py` – Status mutation + pagination  
- `docs/guides/BUG_REPORT_WORKFLOW.md`

**Problem:** Bug reports are written to disk but there is no supported workflow to list, triage, or expire them; retention is manual and prone to drift.

**Plan:**  
1. Provide a CLI/admin endpoint to list reports, filter by status, and mark them resolved.  
2. Implement optional automated retention (nightly deletion of reports older than 30 days, respecting configuration).  
3. Update operations docs with the review/cleanup process.

**Reference:** `docs/plans/BUG_REPORT_IMPLEMENTATION_PLAN.md`, `docs/plans/BUG_REPORT_TOOL_PLAN.md`

---

### Task #11: Expand Shared Contract Coverage
**Priority:** P3  
**Estimated Time:** 2 days  
**Files:**  
- `shared/schema/*.json` – Add schemas (`album_detail`, `queue_job`, `bug_report_receipt`, `training_status`)  
- `scripts/generate_shared_types.py` – Regenerate types  
- `tests/backend/test_shared_contracts.py` – Additional contract cases

**Problem:** Only the `auth_status` contract is enforced end-to-end. High-value responses (albums, queue jobs, analytics) lack schema coverage, risking divergence between backend and frontend.

**Plan:**  
1. Author JSON Schemas for the next bundle of endpoints highlighted in the inspection report.  
2. Regenerate Python/TypeScript bindings and update import paths.  
3. Extend backend contract tests and wire into CI.

**Reference:** `docs/plans/CONTRACT_TESTING_INSPECTION_REPORT.md`

---
