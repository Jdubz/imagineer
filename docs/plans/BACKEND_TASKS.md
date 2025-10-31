# Backend Outstanding Tasks (Active)

**Last Updated:** 2025-10-30  
**Status:** 2 tasks remaining (both P3)

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

