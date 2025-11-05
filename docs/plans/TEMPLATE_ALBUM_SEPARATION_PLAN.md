# Template-Album Separation Implementation Plan

**Date:** 2025-11-04
**Status:** Ready for Implementation
**Priority:** High - Architectural Foundation

## Problem Statement

The current codebase conflates two distinct concepts:
1. **Batch Templates**: Instructions for generating a collection of images (INPUT)
2. **Albums**: Collections of generated images (OUTPUT)

This confusion manifests as:
- Albums having a `is_set_template` flag with template-specific fields
- "Template albums" that are neither true templates nor true albums
- Frontend code filtering albums by template status
- Incomplete source tracking for albums (manual vs. batch vs. scrape)
- No record of batch generation runs with their specific parameters

## Goals

1. **Separate Concerns**: Templates and Albums are different entities with different purposes
2. **Clear Source Tracking**: Every album knows its source (manual, batch generation, or scrape)
3. **Audit Trail**: Record batch generation runs and scrape jobs with full parameters
4. **Auto-create Albums**: Batch generations and successful scrapes automatically create albums
5. **Clean Schema**: Remove template pollution from Album model

## New Database Schema

### BatchTemplate (NEW)
```python
class BatchTemplate(db.Model):
    __tablename__ = "batch_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)

    # Template definition
    csv_path = db.Column(db.String(500), nullable=False)  # Path to CSV file
    csv_data = db.Column(db.Text)  # JSON: Cached CSV data for quick access
    base_prompt = db.Column(db.Text)
    prompt_template = db.Column(db.Text, nullable=False)
    style_suffix = db.Column(db.Text)
    example_theme = db.Column(db.Text)

    # Generation settings
    width = db.Column(db.Integer, default=512)
    height = db.Column(db.Integer, default=512)
    negative_prompt = db.Column(db.Text)
    lora_config = db.Column(db.Text)  # JSON: [{path, weight}]

    # Metadata
    created_by = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    generation_runs = db.relationship("BatchGenerationRun", backref="template")
```

### BatchGenerationRun (NEW)
```python
class BatchGenerationRun(db.Model):
    __tablename__ = "batch_generation_runs"

    id = db.Column(db.Integer, primary_key=True)

    # Links
    template_id = db.Column(db.Integer, db.ForeignKey("batch_templates.id"), nullable=False)
    album_id = db.Column(db.Integer, db.ForeignKey("albums.id"), nullable=True)  # Set when album created

    # User inputs
    album_name = db.Column(db.String(255), nullable=False)  # User-provided name
    user_theme = db.Column(db.Text, nullable=False)

    # Generation parameters (overrides)
    steps = db.Column(db.Integer)
    seed = db.Column(db.Integer)
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    guidance_scale = db.Column(db.Float)
    negative_prompt = db.Column(db.Text)

    # Status tracking
    status = db.Column(db.String(50), default="queued")  # queued, running, completed, failed
    total_items = db.Column(db.Integer)
    completed_items = db.Column(db.Integer, default=0)
    failed_items = db.Column(db.Integer, default=0)

    # Timing
    created_by = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    # Error tracking
    error_message = db.Column(db.Text)
```

### Album (UPDATED)
```python
class Album(db.Model):
    __tablename__ = "albums"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)

    # Source tracking
    source_type = db.Column(db.String(50), nullable=False)  # 'manual', 'batch_generation', 'scrape'
    source_id = db.Column(db.Integer)  # FK to BatchGenerationRun or ScrapeJob

    # Album metadata
    is_public = db.Column(db.Boolean, default=True)
    is_training_source = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.String(255))

    # Timestamps
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    album_images = db.relationship("AlbumImage", backref="album", cascade="all, delete-orphan")

    # REMOVED FIELDS:
    # - is_set_template
    # - csv_data
    # - base_prompt
    # - prompt_template
    # - style_suffix
    # - example_theme
    # - lora_config
    # - generation_prompt (redundant with source tracking)
    # - generation_config (redundant with source tracking)
    # - album_type (replaced by source_type)
```

### ScrapeJob (UPDATED)
```python
class ScrapeJob(db.Model):
    # ... existing fields ...
    album_id = db.Column(db.Integer, db.ForeignKey("albums.id"))  # ALREADY EXISTS
    album_name = db.Column(db.String(255))  # NEW: User-provided name for album
    auto_create_album = db.Column(db.Boolean, default=True)  # NEW: Whether to auto-create album on success
```

## Migration Steps

### Phase 1: Database Migration

**Script**: `scripts/migrate_template_album_separation.py`

1. **Create new tables**:
   - `batch_templates`
   - `batch_generation_runs`

2. **Add new columns to albums**:
   - `source_type` (default='manual' for existing albums)
   - `source_id` (nullable)

3. **Migrate template albums**:
   - Query: `SELECT * FROM albums WHERE is_set_template = 1`
   - Current state: 3 template albums (Card Deck, Zodiac, Tarot) with 0 images
   - Action: **DELETE** these albums (no images to preserve)

4. **Seed batch templates from config**:
   - Read `/mnt/speedy/imagineer/sets/config.yaml`
   - Create BatchTemplate records for: card_deck, tarot_deck, zodiac
   - Store CSV paths: `data/sets/card_deck.csv`, etc.

5. **Import orphaned batch generation images**:
   - Scan `/mnt/speedy/imagineer/outputs/` for batch directories
   - Identify directories with naming pattern: `{template_name}_{timestamp}/`
   - For each directory with images:
     - Create Album record (source_type='batch_generation', name from directory)
     - Import all images from directory into database (if not already imported)
     - Link images to album via album_images table
   - Directories found:
     - `card_deck_20251013_213149/`
     - `card_deck_20251013_213519/`
     - `tarot_deck_20251014_223846/`
     - `tarot_deck_20251014_224018/`
     - `test_card_set_20251103_115513/`
     - `test_card_set_20251103_115538/`
     - `zodiac_20251013_204136/`
     - `zodiac_20251013_210029/`

6. **Import orphaned scrape images**:
   - Scan `/mnt/speedy/imagineer/outputs/scraped/` for images
   - Group by subdirectory or scrape session
   - Create Album records (source_type='scrape')
   - Import and link images

7. **Import orphaned single-generation images**:
   - Scan `/mnt/speedy/imagineer/outputs/*.png` (root level)
   - These are single ad-hoc generations
   - Option A: Create one "Ad-hoc Generations" album for all
   - Option B: Skip (these are test/dev generations)
   - Recommended: **Option A** for completeness

8. **Add new column to scrape_jobs**:
   - `album_name` (nullable for now)

9. **Remove deprecated columns from albums** (in separate migration for safety):
   - `is_set_template`
   - `csv_data`
   - `base_prompt`
   - `prompt_template`
   - `style_suffix`
   - `example_theme`
   - `lora_config`
   - `generation_prompt`
   - `generation_config`
   - `album_type` (keep temporarily, remove later)

### Phase 2: Backend Implementation

#### 2.1 Create New Models
- `server/database.py`: Add BatchTemplate, BatchGenerationRun
- Update Album model (add source_type, source_id)
- Update ScrapeJob model (add album_name)

#### 2.2 Create Batch Template Endpoints
**NEW**: `server/routes/batch_templates.py`

```
GET    /api/batch-templates              List all templates
GET    /api/batch-templates/{id}         Get template details
POST   /api/batch-templates              Create template (admin)
PUT    /api/batch-templates/{id}         Update template (admin)
DELETE /api/batch-templates/{id}         Delete template (admin)
POST   /api/batch-templates/{id}/generate Generate batch from template
GET    /api/batch-templates/{id}/runs    List generation runs for template
```

#### 2.3 Update Generation Endpoints
**File**: `server/routes/generation.py`

- **REMOVE**: `/api/albums/{id}/generate/batch`
- **UPDATE**: Batch generation flow:
  1. User selects BatchTemplate
  2. User provides: album_name, user_theme, optional overrides
  3. Create BatchGenerationRun record (status='queued')
  4. Queue generation jobs with run_id
  5. When all jobs complete: Create Album with source tracking
  6. Update BatchGenerationRun (album_id, status='completed')

#### 2.4 Update Scraping Endpoints
**File**: `server/routes/scraping.py`

- Add `album_name` parameter to scrape job creation
- On successful completion (status='completed', images > 0):
  1. Create Album record (source_type='scrape', source_id=scrape_job.id)
  2. Link scraped images to album
  3. Update scrape_job.album_id

#### 2.5 Update Albums Endpoints
**File**: `server/routes/albums.py`

- **REMOVE**: `is_set_template` filtering logic (lines 54-58)
- **ADD**: Optional `source_type` filter
- Update `to_dict()` to include source information

#### 2.6 Update Shared Types
**File**: `server/shared_types.py`

- Remove template fields from Album types
- Add BatchTemplate types
- Add BatchGenerationRun types
- Update Album to include source_type, source_id

### Phase 3: Frontend Implementation

#### 3.1 Create Batch Templates Page
**NEW**: `web/src/pages/BatchTemplatesPage.tsx`

- List all batch templates
- Show template details (CSV preview, prompts, LoRAs)
- "Generate Batch" button → Form modal:
  - Required: Album name, User theme
  - Optional: Steps, Seed, overrides
- Show recent generation runs for each template

#### 3.2 Update Albums Tab
**File**: `web/src/components/AlbumsTab.tsx`

**REMOVE**:
- Line 112: `is_set_template: false` filter
- All template-related logic

**ADD**:
- Source badge on album cards (Manual, Batch, Scrape)
- Optional filter by source_type
- Click source badge → Navigate to source details:
  - Batch: Show BatchGenerationRun details
  - Scrape: Show ScrapeJob details

#### 3.3 Update Generate Form
**File**: `web/src/components/GenerateForm.tsx`

**REMOVE**:
- Lines 44-52: Batch generation state
- Lines 54-77: Template fetching logic
- Batch generation form UI

**KEEP**:
- Single image generation (this is separate from batch templates)

#### 3.4 Update API Client
**File**: `web/src/lib/api.ts`

**ADD**:
```typescript
batchTemplates: {
  getAll: () => Promise<BatchTemplate[]>
  getById: (id: string) => Promise<BatchTemplate>
  create: (data: CreateBatchTemplateParams) => Promise<BatchTemplate>
  update: (id: string, data: UpdateBatchTemplateParams) => Promise<BatchTemplate>
  delete: (id: string) => Promise<void>
  generate: (id: string, params: GenerateBatchParams) => Promise<BatchGenerationRun>
  getRuns: (id: string) => Promise<BatchGenerationRun[]>
}
```

**UPDATE**:
```typescript
albums: {
  // Remove is_set_template parameter
  getAll: (signal?, filters?: { source_type?: string }) => Promise<Album[]>
}
```

#### 3.5 Update Types
**File**: `web/src/types/models.ts`

- Remove template fields from Album interface
- Add BatchTemplate interface
- Add BatchGenerationRun interface
- Add source_type and source_id to Album

### Phase 4: Documentation Updates

#### 4.1 Update CLAUDE.md
- Remove all "template album" references
- Add clear distinction: Templates vs. Albums
- Update terminology section
- Update architecture overview

#### 4.2 Update ARCHITECTURE.md
- Add BatchTemplate entity
- Add BatchGenerationRun entity
- Update Album entity (remove template fields)
- Update data flow diagrams
- Add source tracking explanation

#### 4.3 Create Migration Documentation
**NEW**: `docs/migrations/TEMPLATE_ALBUM_SEPARATION.md`

- Why the change was made
- What changed
- How to use the new system
- Migration checklist

#### 4.4 Update API Documentation
- Document new `/api/batch-templates` endpoints
- Update `/api/albums` endpoint docs
- Add source tracking explanation

### Phase 5: Testing & Validation

#### 5.1 Database Migration Test
```bash
# Backup database
cp instance/imagineer.db instance/imagineer.db.backup

# Run migration
python scripts/migrate_template_album_separation.py

# Verify:
# - batch_templates table has 3 records
# - Template albums deleted
# - Existing albums have source_type='manual'
# - No orphaned records
```

#### 5.2 Backend Tests
- Test batch template CRUD operations
- Test batch generation creates album + run record
- Test scrape creates album on success
- Test album source tracking
- Test filtering by source_type

#### 5.3 Frontend Tests
- Test batch templates page loads
- Test batch generation form
- Test albums show all sources
- Test source badges display correctly

#### 5.4 Integration Tests
- End-to-end batch generation
- End-to-end scrape with album creation
- Manual album creation

## Implementation Order

1. ✅ **Planning** (This document)
2. **Database Migration** (Phase 1)
   - Create migration script
   - Test on development database
   - Run migration
3. **Backend Models** (Phase 2.1)
   - Add new models
   - Update existing models
4. **Backend Endpoints** (Phase 2.2-2.5)
   - Batch template endpoints
   - Update generation logic
   - Update scraping logic
   - Update album endpoints
5. **Frontend Types** (Phase 3.5)
   - Update TypeScript types
   - Update API client
6. **Frontend UI** (Phase 3.1-3.4)
   - Batch templates page
   - Update albums tab
   - Update generate form
7. **Documentation** (Phase 4)
   - Update all docs
8. **Testing** (Phase 5)
   - Comprehensive testing
9. **Deployment**
   - Backup production DB
   - Run migration on production
   - Deploy updated code

## Rollback Plan

If issues are discovered:

1. **Before column removal**: Simply revert code, keep database as-is
2. **After column removal**: Restore from backup
3. **Keep backups** for 30 days after migration

## Success Criteria

- ✅ No albums with `is_set_template=True`
- ✅ All albums have valid `source_type`
- ✅ All orphaned batch generation images imported as albums
- ✅ All orphaned scrape images imported as albums
- ✅ All filesystem images accounted for in database
- ✅ Batch generation creates albums automatically
- ✅ Successful scrapes create albums automatically
- ✅ Frontend shows all albums in one view
- ✅ Batch templates accessible via separate page
- ✅ All documentation updated
- ✅ No references to "template albums" in codebase

## Future Enhancements (Post-Migration)

- Extensible batch template schema for different template types
- Template marketplace/sharing
- Template versioning
- Batch generation job queue improvements
- Better error handling and retry logic

---

**Next Steps**: Begin Phase 1 (Database Migration)
