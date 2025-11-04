# Terminology Fix Summary

## Problem Identified

The Albums page was showing 3 empty "albums" which were actually **batch generation templates**, not output albums. This caused confusion because:

1. **Templates** (input) were being displayed as if they were **Albums** (output)
2. Actual generated image collections had no representation in the Albums page
3. Users couldn't browse their generated batches

## Terminology Clarification

### Before (Confusing)
- "Sets" = unclear if input or output
- Albums mixed templates and outputs

### After (Clear)
- **Batch Generation Template**: A CSV file + configuration (prompts, LoRAs, dimensions) that defines HOW to generate images. Stored as `Album` records with `is_set_template=True`.
- **Album**: An output collection of generated images. Created when a batch template is executed.
- **Batch**: A single execution of a template that creates an album.

## Changes Made

### 1. Documentation Updates ✅

**ARCHITECTURE.md:**
- Added terminology section clarifying templates vs albums
- Updated all references from "set-based" to "template-based"
- Updated data flow diagram to show template → album relationship
- Clarified that CSV files contain prompt definitions, not just data

**CLAUDE.md:**
- Added terminology section
- Updated all API examples
- Clarified that templates are inputs, albums are outputs

### 2. Frontend Updates ✅

**web/src/lib/api.ts:**
- Added `filters` parameter to `albums.getAll()` to support `is_set_template` filtering

**web/src/components/AlbumsTab.tsx:**
- Changed default behavior to fetch only non-template albums (`is_set_template=false`)
- Updated filter buttons from "Set Templates/Regular Albums" to "Batch Generated/Manual Collections"
- Removed "Set Template" badge from album cards
- Removed batch generation dialog (will be moved to dedicated Templates page)
- Updated UI text to clarify albums are output collections

### 3. API Endpoints (No changes needed) ✅

The API already supports the `is_set_template` query parameter via:
- `GET /api/albums?is_set_template=false` - Get output albums
- `GET /api/albums?is_set_template=true` - Get batch templates

## Current State

### Database State
- ✅ 3 batch templates exist (Card Deck, Zodiac, Tarot) with `is_set_template=True`
- ❌ 0 output albums in database

### File System State
- ✅ Multiple batch output directories exist in `/mnt/speedy/imagineer/outputs/`:
  - `card_deck_20251013_213519/`
  - `tarot_deck_20251014_223846/`
  - `zodiac_20251013_204136/`
  - `test_card_set_20251103_115513/`
  - And more...

### The Issue
Generated images exist on disk but are **not imported into the database as Album records**, so they don't appear in the Albums page.

## Next Steps Required

### Option 1: Create Import Script (Recommended for existing data)

Create `server/scripts/import_batch_albums.py` to:
1. Scan `/mnt/speedy/imagineer/outputs/` for batch directories
2. For each directory with images:
   - Create Album record (name from directory, `is_set_template=False`, `album_type='batch'`)
   - Create Image records for each .png file
   - Create AlbumImage associations
   - Generate thumbnails if missing

### Option 2: Fix Generation Process (Required for future batches)

Update `server/routes/generation.py` batch generation endpoint to:
1. When starting a batch, create Album record immediately
2. As images are generated, create Image and AlbumImage records
3. Update Album.image_count as generation progresses

### Option 3: Both (Best Solution)

1. Run import script to recover existing batches as albums
2. Fix generation process so future batches automatically create albums
3. Create dedicated "Batch Templates" page for template selection and generation

## Testing Plan

1. ✅ Documentation is updated and consistent
2. ✅ Frontend filters templates by default
3. ⏳ Build and deploy frontend
4. ⏳ Run import script to create album records
5. ⏳ Verify Albums page shows generated collections
6. ⏳ Test batch generation creates albums automatically
7. ⏳ Create Batch Templates page for template management

## Files Changed

- `docs/ARCHITECTURE.md` - Terminology and architecture clarification
- `CLAUDE.md` - Project instructions with correct terminology
- `web/src/lib/api.ts` - Added template filtering support
- `web/src/components/AlbumsTab.tsx` - Shows only output albums, not templates
- `TERMINOLOGY_FIX_SUMMARY.md` (this file) - Documentation of changes

## Deployment Notes

After deploying these changes:
1. Albums page will initially appear empty (expected - no albums imported yet)
2. The 3 templates will no longer appear (they're filtered out)
3. Run import script to populate albums from existing batch outputs
4. Albums page will then show actual generated collections with images
