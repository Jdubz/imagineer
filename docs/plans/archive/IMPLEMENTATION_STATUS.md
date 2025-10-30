# Implementation Status – 2025-10-28

> **⚠️ SUPERSEDED:** This document has been replaced by **[CONSOLIDATED_STATUS.md](./CONSOLIDATED_STATUS.md)** which provides a complete, up-to-date reconciliation of all planning documents against the current codebase.
>
> This file remains for historical reference.

---

This document tracks the remaining gaps between the **Revised Comprehensive Improvement Plan** and the current codebase.

## Phase 1 – Foundation & Security
- ✅ Runtime secret enforcement, PasswordGate removal, CORS/Talisman configuration, structured logging, and SQLite integration are in place.
- ❓ Migration scripts (`scripts/migrate_to_database.py`, `scripts/index_images.py`) exist, but there is no recorded migration history or marker to confirm they have been executed in each environment. Consider adding an Alembic revision or a one-time migration flag.
- 📝 Decision: keep `users.json` for admin roles. The plan’s `ADMIN_EMAILS` constant is superseded; no change required unless we want the hard-coded list later.

## Phase 2 – Album System & Image Management
- ✅ Album CRUD, upload endpoints, thumbnails, NSFW filtering, and the Albums UI shipped.
- ⚠️ Duplicate endpoints: both `server/api.py` and `server/routes/images.py` expose image/thumbnail logic. The blueprint version contains the latest safety checks; consolidate to avoid drift.
- ⚠️ Album analytics/search promised in the plan are not implemented (only basic pagination).

## Phase 3 – AI Labeling System
- ✅ Claude integration works through `server/services/labeling.py`; new Celery tasks (`server/tasks/labeling.py`) queue `/api/labeling/*` requests and persist results.
- ⚠️ Backend/tests mismatch: API now returns `202 + task_id` but `tests/backend/test_phase3_labeling.py` (and Celery routing config expecting `server.tasks.labeling.*`) still assume synchronous execution. Align task names/routes, update tests, and add task-status coverage.
- ❌ Frontend labeling experience (LabelingPanel, batch dialogs, manual tag UI) is still pending; no `/api/labeling` calls exist in React.
- ⚠️ No label analytics/stats endpoints.

## Phase 4 – Web Scraping Integration
- ✅ Scraping blueprint, tasks, and admin UI exist.
- ❌ `SCRAPED_OUTPUT_PATH` remains `None` at runtime (`server/tasks/scraping.py:22`); initialize it from configuration before launching the scraper.
- ⚠️ Scrape job progress exposed to the UI is minimal compared to the roadmap.

## Phase 5 – Training Pipeline
- ✅ Training endpoints, Celery worker, runtime UI, and task scaffolding deployed.
- ❌ Training run creation doesn’t persist selected album IDs; `train_lora_task` expects them inside the config and fails with “No albums specified” when invoked.
- ⚠️ Training logs endpoint returns placeholder text; planned log storage/streaming unimplemented.
- ⚠️ Trained LoRA registration (auto-adding to `/api/loras`) is missing.
- ⚠️ No cleanup of `/tmp/training_*` directories after runs complete.

## Cross-Cutting
- ⚠️ Celery routing still points to `server.tasks.labeling.*` while task names are registered as `tasks.*`; update names to ensure queue affinity once async flow is finalized.
- ⚠️ OpenAPI docs/monitoring integrations mentioned later in the plan are still outstanding.
- ✅ Testing has broad coverage, but new admin UIs (Labeling, Scraping dashboards) lack Vitest cases.
- ✅ Shared schema/types pipeline exists (`shared/schema`, `scripts/generate_shared_types.py`, generated TS/Python types); ensure future schemas are added through the generator.

### Next Actions
1. Finish aligning asynchronous labeling (task naming, API tests) and React integration.
2. Initialize `SCRAPED_OUTPUT_PATH` from configuration and verify scraped imports.
3. Persist training album selections and surface trained LoRAs/logs as planned.
