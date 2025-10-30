# Legacy Image Import Plan

**Date:** 2025-10-30  
**Owner:** Data & Media Platform

---

## 1. Context & Goal

We need to restore legacy images and albums that were generated outside the current application flow. Today, the UI loads almost no historic media because those assets live in ad‑hoc folders (often on a mounted volume) and are not registered with the database or album services. This plan inventories every known image source in the repository and proposes a maintainable import pipeline that prioritises unit-testable components over brittle end-to-end scripts.

## 2. Exhaustive Source Inventory

All directories were scanned with:

```bash
find -L <root> -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.webp' -o -iname '*.gif' -o -iname '*.bmp' -o -iname '*.tiff' -o -iname '*.svg' \)
```

| Scope | Path | Notes | Image Count |
| --- | --- | --- | ---: |
| **Application public assets** | `public/` | Only `vite.svg` placeholder. No legacy data. | 1 |
| **Web front-end assets** | `web/public/` | Mirrored `vite.svg`. No legacy content. | 1 |
| **Generated outputs (symlink)** | `outputs/ -> /mnt/speedy/imagineer/outputs` | Primary repository for historic images & metadata (`.png` + paired `.json`). | **181** |
| ├─ Singles | `outputs/*.png` | 55 single-shot generations at root. | 55 |
| ├─ Card decks | `outputs/card_deck_20251013_213149` | Early “card deck” batch (metadata present). | 9 |
| ├─ Card decks | `outputs/card_deck_20251013_213519` | Larger batch with metadata. | 34 |
| ├─ Tarot deck | `outputs/tarot_deck_20251014_223846` | Metadata only, PNGs missing – requires investigation. | 0 |
| ├─ Tarot deck | `outputs/tarot_deck_20251014_224018` | Complete set with art + JSON. | 22 |
| ├─ Zodiac sets | `outputs/zodiac_20251013_204136` | Contains themed PNGs + JSON. | 8 |
| ├─ Zodiac sets | `outputs/zodiac_20251013_210029` | Additional zodiac batch. | 12 |
| ├─ LoRA tests | `outputs/lora_tests/` | LoRA experiment renders. | 6 |
| ├─ Uploads, thumbnails, scraped | Various | Currently empty or JSON-only; keep reserved for future ingestion. | 0 |
| **Legacy packs (mounted)** | `/mnt/speedy/image packs/1987399_training_data` | Curated dataset likely used for early training. | 77 |
| ├─ | `/mnt/speedy/image packs/marytcusack` | Artist-specific reference set. | 32 |
| ├─ | `/mnt/speedy/image packs/Playing Cards` | Source art for card decks. | 67 |
| ├─ | `/mnt/speedy/image packs/PNG-cards-1.3` | Additional card PNG bundle. | 67 |
| **Mounted storage** | `/mnt/storage/imagineer/scraped` | Currently image-empty, but reserved for long-term scraped archives. | 0 |
| **Coverage & tooling artifacts** | `web/coverage/`, `web/node_modules/**`, `venv/**` | Static assets from tooling; explicitly **excluded** from import. | n/a |

## 3. Target Organisation

1. **Create a canonical legacy staging area** at `data/legacy/` inside the repo (gitignored) with the structure:
   ```
   data/legacy/
     ├─ singles/
     ├─ decks/<deck_slug>/
     ├─ zodiac/<set_slug>/
     ├─ lora-experiments/<experiment_slug>/
     ├─ reference-packs/<pack_slug>/  # from /mnt/speedy/image packs/*
     └─ uploads/<yyyy-mm>/ (future user uploads)
   ```
2. **Mirror JSON metadata** alongside each image by copying (or symlinking) the paired `.json`.
3. Store a manifest (`manifest.yaml`) per subfolder capturing:
   - Relative image path
   - Prompt text (or source description for reference packs)
   - Timestamp (from filename or JSON)
   - Target album name & visibility flags
   - Any LoRA/model metadata

## 4. Import Pipeline (Unit-Test Focused)

| Stage | Description | Owner |
| --- | --- | --- |
| **Collectors** | Write small collectors (one per source folder) that scan the original directories (`outputs/…`) and emit a normalized `LegacyImage` dataclass + manifest entry. Pure functions = easy unit tests. | Backend |
| **Stagers** | Copy or symlink assets into `data/legacy` according to manifest, ensuring deterministic filenames (e.g., `<timestamp>-<slug>.png` for generated art, `<pack>/<original_name>` for reference packs). Unit tests verify idempotency & path rules. | Backend |
| **Album Resolver** | Map each record to an album ID (create if missing). Implement as a service layer function with dependency-injected repositories so we can unit test without DB I/O. | Backend |
| **Ingest Command** | Build a CLI `scripts/import_legacy_media.py` which reads manifests, writes DB rows, and enqueues thumbnails. Cover logic with unit tests using in-memory stubs; integration with real DB can be optional/manual. | Backend |
| **Verification Suite** | Add tests that validate manifest completeness (no orphaned JSON/PNG), and ensure the importer skips duplicates based on hash or prompt+timestamp. | QA |

CI Impact: collectors/stagers/importer should expose pure Python modules with comprehensive unit tests. Avoid adding long-running end-to-end gallery rebuilds to CI; keep those as manual ops runbooks.

## 5. Operational Checklist

1. **Snapshot mounted volumes** (`/mnt/speedy/imagineer/outputs`, `/mnt/speedy/image packs`, optional `/mnt/storage/imagineer`) before moving files.
2. Run collectors to generate manifests; review YAML diffs for accuracy.
3. Execute stager script to populate `data/legacy`.
4. Dry-run importer in staging (use feature flag to disable thumbnail writes during test).
5. Validate in UI (filter by new “Legacy” album tag) and confirm counts match manifest.
6. Once verified, archive raw outputs folders (rename to `.legacy-archive`) to prevent double imports.

## 6. Open Questions

- Should we deduplicate images by perceptual hash or rely on filename uniqueness?
- How do we map NSFW / restricted images (e.g., `_voluptuous_` renders) – mark as private album?
- Do we need to import associated LoRA weight files, or only preserve references?
- What retention policy should apply to the JSON metadata after ingestion (keep or archive)?

## 7. Next Steps

1. Approve this plan.
2. Implement manifest generators + unit tests.
3. Schedule a maintenance window to run the import pipeline and verify in production/staging.
4. Update the runbook with lessons learned and mark legacy ingestion as complete.
