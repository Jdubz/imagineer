# LoRA Training Implementation Plan

**Created:** 2025-11-05
**Status:** Ready for Implementation
**Priority:** Critical - Core Feature Completion

## Executive Summary

This document outlines the complete implementation plan for Imagineer's LoRA training pipeline, organized by feature priority:

1. **Web Scraping** - Copy scraping logic from training-data repo into this project
2. **Image Upload** - Bulk image upload to albums
3. **Labeling System** - Automated Claude labeling + manual editing with NSFW detection
4. **Training Pipeline** - Fix existing training implementation and build UI

## Current State Analysis

### ✅ What Already Works
- `TrainingRun` database model (database.py:494-551)
- Training task implementation (server/tasks/training.py)
- Training API endpoints (server/routes/training.py)
- `examples/train_lora.py` script for LoRA training
- Album system with source tracking
- Basic labeling infrastructure (Claude CLI in Docker)

### ❌ What's Broken
- **Scraping depends on external training-data repo** (completely non-functional)
- Training dataset preparation has directory structure mismatch
- No frontend UI for any training features
- `is_training_source` flag is incorrect architecture (should be per-training-run album selection)
- Labeling system incomplete

---

## Phase 1: Web Scraping (Priority 1)

**Goal:** Copy scraping functionality from training-data into this project, removing external dependency.

### 1.1 Copy Dependencies

Add to `requirements.txt`:
```python
# Web Scraping
playwright>=1.40.0
httpx>=0.25.0
beautifulsoup4>=4.12.0
lxml>=4.9.3
imagehash>=4.3.1
aiofiles>=23.2.1
anthropic>=0.34.0  # For captioning
pydantic>=2.5.0
pydantic-settings>=2.1.0
```

### 1.2 Copy Code Structure

Create new package structure:
```
server/
├── scraping/
│   ├── __init__.py
│   ├── config.py           # Pydantic config models
│   ├── models.py           # ImageMetadata, ScrapingSession
│   ├── crawler.py          # WebCrawler class (Playwright + BeautifulSoup)
│   ├── downloader.py       # ImageDownloader class (httpx async)
│   ├── validator.py        # ImageValidator (dimensions, format)
│   ├── deduplicator.py     # ImageDeduplicator (perceptual hashing)
│   └── captioner.py        # ClaudeCaptioner (vision API)
```

### 1.3 Adapt Code for Imagineer

**Key changes from training-data:**
1. Remove CLI/terminal UI (Rich library)
2. Integrate with existing `ScrapeJob` database model
3. Use Celery tasks instead of standalone script
4. Save images directly to album structure
5. Store captions as `Label` records, not `.txt` files
6. Import any existing captions/labels from scraped sites

### 1.4 Implementation Steps

#### Step 1: Copy Core Classes (1 day)

**Files to copy (adapted):**
- `training_data/config.py` → `server/scraping/config.py`
  - Use Pydantic for configuration
  - Load from config.yaml `scraping:` section

- `training_data/models.py` → `server/scraping/models.py`
  - `ImageMetadata`, `ScrapingSession`, `ImageStatus` enums

- `training_data/scraper/crawler.py` → `server/scraping/crawler.py`
  - `WebCrawler` class (Playwright + BeautifulSoup)
  - Async crawling with depth limits
  - JavaScript rendering support

- `training_data/scraper/downloader.py` → `server/scraping/downloader.py`
  - `ImageDownloader` class (httpx async)
  - Concurrent downloads with semaphore
  - Retry logic

#### Step 2: Validation & Deduplication (1 day)

- `training_data/processor/validator.py` → `server/scraping/validator.py`
  - Image format validation
  - Dimension checks (configurable minimums)
  - Aspect ratio filtering

- `training_data/processor/deduplicator.py` → `server/scraping/deduplicator.py`
  - Perceptual hashing (imagehash library)
  - Similarity threshold configuration

#### Step 3: Captioning Integration (1 day)

- `training_data/captioner/claude_captioner.py` → `server/scraping/captioner.py`
  - `ClaudeCaptioner` class
  - Uses Anthropic Python SDK
  - Batch processing for efficiency
  - Option to skip captioning (label manually later)

**Integration points:**
- Load `ANTHROPIC_API_KEY` from environment
- Create `Label` records with `label_type='scrape_caption'`
- Also extract any existing alt text/captions from HTML as separate labels

#### Step 4: Refactor server/tasks/scraping.py (2 days)

**Current:** Calls external training-data subprocess
**New:** Uses internal scraping package

```python
# server/tasks/scraping.py (NEW IMPLEMENTATION)

from server.scraping import WebCrawler, ImageDownloader, ImageValidator
from server.scraping import ImageDeduplicator, ClaudeCaptioner
from server.scraping.config import ScrapingConfig

@celery.task
async def scrape_site_task(scrape_job_id):
    """Execute web scraping using internal scraping engine."""

    # Load config
    config = ScrapingConfig.from_config_file()

    # Initialize components
    crawler = WebCrawler(config.crawler)
    downloader = ImageDownloader(config.downloader)
    validator = ImageValidator(config.validator)
    deduplicator = ImageDeduplicator(config.deduplicator)
    captioner = ClaudeCaptioner(config.captioner, api_key=os.getenv('ANTHROPIC_API_KEY'))

    # Execute pipeline
    image_urls = await crawler.crawl(job.source_url, max_images=job.max_images)

    metadata_list = await downloader.download_images(image_urls, temp_dir)

    valid_metadata = validator.validate_batch(metadata_list)

    unique_metadata = deduplicator.deduplicate_batch(valid_metadata)

    # Optional captioning (can be done later via labeling feature)
    if config.caption_on_scrape:
        captioned_metadata = await captioner.caption_batch(unique_metadata)
    else:
        captioned_metadata = unique_metadata

    # Import to database and create album
    album = create_album_from_scrape(job, captioned_metadata)

    return {"album_id": album.id, "images_imported": len(captioned_metadata)}
```

#### Step 5: Extract Existing Captions from HTML (1 day)

Many card/image sites include metadata:
```python
# server/scraping/metadata_extractor.py

class MetadataExtractor:
    """Extract existing captions/labels from HTML."""

    def extract_from_html(self, soup, image_url):
        """Find alt text, titles, captions near images."""
        # Check <img alt="">
        # Check <figcaption>
        # Check nearby <p> or <div> text
        # Check meta tags
        # Check structured data (JSON-LD)

        return {
            'alt_text': ...,
            'caption': ...,
            'title': ...,
            'description': ...
        }
```

Store each piece as separate `Label` records with appropriate `label_type`.

#### Step 6: Testing (1 day)

- Test with sites from `docs/card_sites.json`
- Verify JS rendering works (Playwright)
- Test duplicate detection
- Test caption extraction
- End-to-end scraping → album creation

**Total Effort:** 7-8 days

---

## Phase 2: Image Upload (Priority 2)

**Goal:** Allow admins to upload images directly to albums.

### 2.1 Backend Implementation (1-2 days)

#### New API Endpoints

```python
# server/routes/images.py

@images_bp.route('/upload', methods=['POST'])
@require_admin
def upload_images():
    """
    Upload one or more images.

    Form data:
        - files[]: Multiple image files
        - album_id: Optional existing album ID
        - album_name: Optional new album name
        - album_description: Optional description
    """
    files = request.files.getlist('files[]')
    album_id = request.form.get('album_id')
    album_name = request.form.get('album_name')

    # Create or get album
    if album_id:
        album = Album.query.get_or_404(album_id)
    elif album_name:
        album = Album(
            name=album_name,
            description=request.form.get('album_description'),
            source_type='manual',
            album_type='uploaded'
        )
        db.session.add(album)
        db.session.commit()
    else:
        return jsonify({'error': 'Must specify album_id or album_name'}), 400

    # Process each file
    uploaded_images = []
    for file in files:
        if not allowed_file(file.filename):
            continue

        # Save file
        image_path = save_uploaded_image(file)

        # Create Image record
        image = Image(
            filename=file.filename,
            file_path=str(image_path),
            # Generate thumbnail
            thumbnail_path=generate_thumbnail(image_path)
        )
        db.session.add(image)
        db.session.flush()

        # Add to album
        album_image = AlbumImage(album_id=album.id, image_id=image.id)
        db.session.add(album_image)

        uploaded_images.append(image.id)

    db.session.commit()

    return jsonify({
        'album_id': album.id,
        'images_uploaded': len(uploaded_images),
        'image_ids': uploaded_images
    })
```

#### Bulk Upload Endpoint

```python
@images_bp.route('/bulk-upload', methods=['POST'])
@require_admin
def bulk_upload_images():
    """
    Upload many images at once with progress tracking.
    Creates a background Celery task for processing.
    """
    # Similar to scraping - create UploadJob record
    # Process files in background task
    # Return job_id for progress tracking
```

### 2.2 Frontend Implementation (2-3 days)

#### Component: ImageUploadModal.tsx

```typescript
// web/src/components/ImageUploadModal.tsx

interface ImageUploadModalProps {
  existingAlbumId?: number;
  onComplete: (albumId: number) => void;
}

export function ImageUploadModal({ existingAlbumId, onComplete }: ImageUploadModalProps) {
  // File input with drag-and-drop
  // Preview thumbnails
  // Album selection dropdown OR new album form
  // Upload progress bars
  // Error handling
}
```

#### Integration Points

- Add "Upload Images" button to Albums page
- Add "Add Images" button to Album detail page
- Support drag-and-drop anywhere on album page

**Total Effort:** 3-5 days

---

## Phase 3: Labeling System (Priority 3)

**Goal:** Automated and manual labeling with NSFW detection.

### 3.1 Backend Implementation

#### 3.1.1 Enhance Existing Labeling (2 days)

Current: `server/tasks/labeling.py` has basic structure
Needs: Full implementation with batch processing

```python
# server/tasks/labeling.py (ENHANCED)

@celery.task
def label_image_task(image_id, prompt_context=None):
    """Label a single image using Claude."""
    image = Image.query.get(image_id)

    # Call Claude CLI in Docker (existing implementation)
    result = call_claude_cli_for_labeling(image.file_path, prompt_context)

    # Parse result
    caption = result['caption']
    is_nsfw = result['nsfw_detected']
    tags = result['tags']  # List of keywords

    # Create Label records
    Label(
        image_id=image.id,
        label_text=caption,
        label_type='caption',
        source_model='claude-sonnet-4-5',
        confidence=result.get('confidence', 0.9)
    )

    # NSFW label
    if is_nsfw:
        Label(
            image_id=image.id,
            label_text='NSFW',
            label_type='nsfw',
            source_model='claude-sonnet-4-5'
        )
        image.is_nsfw = True

    # Tag labels
    for tag in tags:
        Label(
            image_id=image.id,
            label_text=tag,
            label_type='tag',
            source_model='claude-sonnet-4-5'
        )

    db.session.commit()
```

#### 3.1.2 Batch Album Labeling (1 day)

```python
@celery.task
def label_album_task(album_id, prompt_context=None):
    """Label all unlabeled images in an album."""
    album = Album.query.get(album_id)

    unlabeled_images = [
        img for img in album.images
        if not any(label.label_type == 'caption' for label in img.labels)
    ]

    for image in unlabeled_images:
        label_image_task.delay(image.id, prompt_context)

    return {
        'album_id': album_id,
        'images_queued': len(unlabeled_images)
    }
```

#### 3.1.3 Enhanced Claude Prompting (1 day)

Update `server/services/labeling_cli.py` with better prompts:

```python
def get_labeling_system_prompt():
    return """You are an expert image analyzer specializing in card imagery (playing cards, tarot, oracle cards, etc.).

Your task is to analyze images and provide:
1. A detailed caption describing the image
2. NSFW detection (explicit content, gore, inappropriate)
3. Relevant tags/keywords

For card images, focus on:
- Card type (playing card, tarot, oracle, etc.)
- Suit, rank, or name if visible
- Art style (vintage, modern, art nouveau, etc.)
- Color palette
- Decorative elements
- Condition (if relevant)

Return JSON format:
{
  "caption": "Detailed description...",
  "nsfw_detected": false,
  "tags": ["playing-card", "spade", "vintage", "ornate"],
  "confidence": 0.95
}
"""

def get_labeling_user_prompt(context=None):
    base = "Analyze this image and provide a caption, NSFW detection, and tags."
    if context:
        return f"{base}\n\nAdditional context: {context}"
    return base
```

### 3.2 API Endpoints (1 day)

```python
# server/routes/images.py

@images_bp.route('/<int:image_id>/label', methods=['POST'])
@require_admin
def label_image(image_id):
    """Trigger labeling for a single image."""
    data = request.json or {}
    prompt_context = data.get('context')

    task = label_image_task.delay(image_id, prompt_context)

    return jsonify({
        'message': 'Labeling started',
        'task_id': task.id
    })

@images_bp.route('/<int:image_id>/labels', methods=['GET', 'POST', 'PATCH', 'DELETE'])
def manage_labels(image_id):
    """CRUD operations for image labels."""
    if request.method == 'GET':
        # Return all labels for image
        pass
    elif request.method == 'POST':
        # Create new label (manual)
        pass
    elif request.method == 'PATCH':
        # Update existing label
        pass
    elif request.method == 'DELETE':
        # Delete label
        pass

# server/routes/albums.py

@albums_bp.route('/<int:album_id>/label', methods=['POST'])
@require_admin
def label_album(album_id):
    """Trigger labeling for entire album."""
    data = request.json or {}
    prompt_context = data.get('context')
    force_relabel = data.get('force', False)  # Re-label already labeled images

    task = label_album_task.delay(album_id, prompt_context, force_relabel)

    return jsonify({
        'message': 'Album labeling started',
        'task_id': task.id
    })
```

### 3.3 Frontend Implementation (3-4 days)

#### Component: ImageLabelsPanel.tsx

```typescript
// web/src/components/ImageLabelsPanel.tsx

interface ImageLabelsPanelProps {
  image: Image;
  editable: boolean;
}

export function ImageLabelsPanel({ image, editable }: ImageLabelsPanelProps) {
  // Display existing labels grouped by type
  // - Caption (editable textarea)
  // - NSFW flag (toggle)
  // - Tags (chips, add/remove)

  // "Relabel" button (calls Claude)
  // "Add Manual Label" form
  // Label confidence scores
}
```

#### Component: AlbumLabelingPanel.tsx

```typescript
// web/src/components/AlbumLabelingPanel.tsx

export function AlbumLabelingPanel({ album }: { album: Album }) {
  // Show labeling statistics
  // - Total images
  // - Labeled images
  // - Unlabeled images
  // - NSFW flagged

  // "Label All Unlabeled" button
  // "Re-label All" button (with confirmation)
  // Progress indicator
  // Custom prompt context input
}
```

#### Integration

- Add labels panel to ImageDetailPage
- Add labeling panel to AlbumDetailPage
- Show NSFW indicator on ImageCard thumbnails
- Add label search/filter to gallery views

**Total Effort:** 8-10 days

---

## Phase 4: Training Pipeline (Priority 4)

**Goal:** Fix training implementation and build UI.

### 4.1 Fix Training Dataset Preparation (1 day)

**Current Issue:** Creates `images/` and `captions/` subdirectories, but SD 1.5 expects flat structure.

```python
# server/tasks/training.py (FIX)

def prepare_training_data(training_run):
    """
    Prepare training data in SD 1.5 format.

    Format:
        training_dir/
        ├── image_0001.jpg
        ├── image_0001.txt
        ├── image_0002.png
        ├── image_0002.txt
        └── ...
    """
    config = json.loads(training_run.training_config) if training_run.training_config else {}
    album_ids = config.get('album_ids', [])

    if not album_ids:
        raise ValueError("No albums specified for training")

    training_dir = get_training_dataset_root() / f"training_run_{training_run.id}"
    training_dir.mkdir(parents=True, exist_ok=True)

    total_images = 0

    for album_id in album_ids:
        album = db.session.get(Album, album_id)
        if not album:
            logger.warning(f"Album {album_id} not found, skipping")
            continue

        album_images = (
            db.session.query(Image)
            .join(AlbumImage)
            .filter(AlbumImage.album_id == album_id)
            .all()
        )

        for image in album_images:
            # Validate image has caption
            caption_labels = [
                label for label in image.labels
                if label.label_type in ('caption', 'scrape_caption')
            ]

            if not caption_labels:
                logger.warning(f"Image {image.id} has no caption, skipping")
                continue

            src_path = Path(image.file_path)
            if not src_path.exists():
                logger.warning(f"Image file not found: {src_path}")
                continue

            # SD 1.5 format: sequential naming
            image_filename = f"image_{total_images:04d}{src_path.suffix}"
            caption_filename = f"image_{total_images:04d}.txt"

            dst_image_path = training_dir / image_filename
            dst_caption_path = training_dir / caption_filename

            try:
                # Copy image
                shutil.copy2(src_path, dst_image_path)

                # Write caption
                caption_text = caption_labels[0].label_text
                dst_caption_path.write_text(caption_text, encoding='utf-8')

                total_images += 1

            except Exception as e:
                logger.error(f"Error processing image {image.id}: {e}")
                continue

    if total_images == 0:
        raise ValueError("No valid captioned images found in specified albums")

    if total_images < 20:
        logger.warning(f"Only {total_images} images for training - may not be enough")

    logger.info(f"Prepared {total_images} images for training in {training_dir}")
    return training_dir
```

### 4.2 Remove is_training_source Flag (1 day)

**Change:** Training run selects albums directly, no pre-flagging needed.

```python
# server/database.py (REMOVE)
# Line 282: is_training_source = db.Column(db.Boolean, default=False)

# server/routes/training.py (UPDATE)
@training_bp.route('/albums', methods=['GET'])
def list_available_albums():
    """List ALL albums available for training."""
    # Remove filter on is_training_source
    albums = Album.query.filter(
        Album.source_type.in_(['batch_generation', 'scrape', 'manual'])
    ).all()

    # Add metadata about labeling status
    album_data = []
    for album in albums:
        labeled_count = sum(
            1 for img in album.images
            if any(label.label_type == 'caption' for label in img.labels)
        )

        album_data.append({
            **album.to_dict(),
            'total_images': len(album.images),
            'labeled_images': labeled_count,
            'ready_for_training': labeled_count == len(album.images) and len(album.images) >= 20
        })

    return jsonify({'albums': album_data})
```

### 4.3 Enhanced Training Configuration (1 day)

Add more training parameters:

```python
# server/routes/training.py (ENHANCE)

@training_bp.route('', methods=['POST'])
@require_admin
def create_training_run():
    """Create new training run with enhanced config."""
    data = request.json or {}

    # Validate album selection
    album_ids = data.get('album_ids', [])
    if not album_ids:
        return jsonify({'error': 'At least one album required'}), 400

    # Validate albums are properly labeled
    validation_errors = []
    total_images = 0

    for album_id in album_ids:
        album = Album.query.get(album_id)
        if not album:
            validation_errors.append(f"Album {album_id} not found")
            continue

        labeled_count = sum(
            1 for img in album.images
            if any(label.label_type == 'caption' for label in img.labels)
        )

        if labeled_count < len(album.images):
            validation_errors.append(
                f"Album '{album.name}' has unlabeled images ({labeled_count}/{len(album.images)})"
            )

        total_images += labeled_count

    if validation_errors:
        return jsonify({'errors': validation_errors}), 400

    if total_images < 20:
        return jsonify({
            'error': f'Not enough training images ({total_images}). Minimum 20 recommended.'
        }), 400

    # Enhanced training config
    training_config = {
        'album_ids': album_ids,
        'steps': data.get('steps', 1500),  # Increased default
        'rank': data.get('rank', 8),  # Increased for complex styles
        'alpha': data.get('alpha', 32),
        'learning_rate': data.get('learning_rate', 1e-4),
        'batch_size': data.get('batch_size', 1),
        'gradient_accumulation_steps': data.get('gradient_accumulation_steps', 4),
        'warmup_steps': data.get('warmup_steps', 100),
        'save_steps': data.get('save_steps', 500),
        # Data augmentation
        'random_flip': data.get('random_flip', True),
        'center_crop': data.get('center_crop', True),
        # Model
        'base_model': data.get('base_model', 'runwayml/stable-diffusion-v1-5'),
    }

    # Create training run
    run = TrainingRun(
        name=data['name'],
        description=data.get('description', ''),
        training_config=json.dumps(training_config),
        status='pending',
        progress=0
    )

    db.session.add(run)
    db.session.commit()

    # Set paths
    dataset_path = get_training_dataset_root() / f"training_run_{run.id}"
    output_path = get_model_cache_dir() / "lora" / f"trained_{run.id}"

    run.dataset_path = str(dataset_path)
    run.output_path = str(output_path)
    db.session.commit()

    return jsonify(run.to_dict(include_sensitive=True)), 201
```

### 4.4 Frontend Implementation (4-5 days)

#### Page: TrainingRunsPage.tsx

```typescript
// web/src/pages/TrainingRunsPage.tsx

export function TrainingRunsPage() {
  // Tabs:
  // - All Runs (list with filters)
  // - Create New Run
  // - Trained LoRAs (browse/download)

  return (
    <div>
      <Tabs defaultValue="runs">
        <TabsList>
          <TabsTrigger value="runs">Training Runs</TabsTrigger>
          <TabsTrigger value="create">Create New</TabsTrigger>
          <TabsTrigger value="loras">Trained LoRAs</TabsTrigger>
        </TabsList>

        <TabsContent value="runs">
          <TrainingRunsList />
        </TabsContent>

        <TabsContent value="create">
          <CreateTrainingRunForm />
        </TabsContent>

        <TabsContent value="loras">
          <TrainedLoRAsGallery />
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

#### Component: CreateTrainingRunForm.tsx

```typescript
// web/src/components/CreateTrainingRunForm.tsx

export function CreateTrainingRunForm() {
  // Form fields:
  // - Run name (required)
  // - Description
  // - Album multi-select with labeling status indicators
  // - Advanced settings (collapsible):
  //   - Steps (slider: 500-5000, default 1500)
  //   - Rank (slider: 4-32, default 8)
  //   - Learning rate (input: 1e-5 to 5e-4)
  //   - Batch size
  //   - Data augmentation toggles

  // Validation:
  // - Show total images count
  // - Warn if < 50 images
  // - Error if any albums have unlabeled images
  // - Estimated training time

  // Submit → Create run → Redirect to progress viewer
}
```

#### Component: TrainingProgressViewer.tsx

```typescript
// web/src/components/TrainingProgressViewer.tsx

export function TrainingProgressViewer({ runId }: { runId: number }) {
  // Real-time updates via polling
  // - Progress bar (0-100%)
  // - Current step / total steps
  // - Live log streaming (tail -f style)
  // - Training loss graph (if available)
  // - ETA

  // Actions:
  // - Cancel (if running)
  // - Download LoRA (if completed)
  // - Integrate LoRA (copy to main LoRA dir)
  // - Retry (if failed)
  // - View full logs
}
```

**Total Effort:** 7-9 days

---

## Implementation Timeline

### Sprint 1: Core Scraping (Week 1-2)
- **Days 1-3:** Copy scraping dependencies and core classes
- **Days 4-5:** Validation, deduplication, captioning
- **Days 6-8:** Refactor `server/tasks/scraping.py`
- **Days 9-10:** Testing with real sites

**Deliverable:** Functional web scraping creating albums

### Sprint 2: Upload & Labeling (Week 3-4)
- **Days 1-2:** Image upload backend
- **Days 3-5:** Image upload frontend
- **Days 6-8:** Enhanced labeling backend
- **Days 9-11:** Labeling UI components
- **Days 12-14:** Testing and polish

**Deliverable:** Image upload and labeling working end-to-end

### Sprint 3: Training (Week 5-6)
- **Days 1-2:** Fix training dataset preparation
- **Days 3-4:** Enhanced training configuration
- **Days 5-9:** Training UI (form, progress, LoRA management)
- **Days 10-12:** End-to-end training tests
- **Days 13-14:** Documentation and polish

**Deliverable:** Complete LoRA training pipeline

---

## Configuration Changes

### config.yaml Updates

```yaml
scraping:
  # Crawler settings
  max_depth: 3
  max_images: 1000
  timeout: 30
  concurrent_downloads: 20
  user_agent: "Imagineer Bot 1.0 (+https://imagineer.example.com)"

  # Validation
  min_width: 100
  min_height: 100
  min_megapixels: 0.01
  max_aspect_ratio: 10.0
  allowed_formats: [jpg, jpeg, png, webp, gif, bmp]

  # Deduplication
  duplicate_threshold: 10  # Perceptual hash distance

  # Captioning
  caption_on_scrape: false  # If false, caption later via labeling
  captioning_model: "claude-sonnet-4-5-20250929"
  captioning_batch_size: 5

labeling:
  model: "claude-sonnet-4-5-20250929"
  max_tokens: 500
  temperature: 0.3
  detect_nsfw: true
  extract_tags: true
  batch_size: 10

training:
  # Defaults for new training runs
  default_steps: 1500
  default_rank: 8
  default_alpha: 32
  default_learning_rate: 1e-4
  default_batch_size: 1

  # Validation
  min_images: 20
  warn_images: 50

  # Paths (existing)
  checkpoint_dir: /mnt/speedy/imagineer/checkpoints
  dataset_dir: /mnt/speedy/imagineer/data/training
```

### Remove from config.yaml

```yaml
# DELETE THIS ENTIRE SECTION
scraping:
  training_data_repo: /mnt/storage/imagineer/training-data
```

---

## Database Migrations

### Migration 1: Remove is_training_source

```python
# migrations/remove_is_training_source.py

def upgrade():
    op.drop_column('albums', 'is_training_source')

def downgrade():
    op.add_column('albums', sa.Column('is_training_source', sa.Boolean(), default=False))
```

---

## Testing Strategy

### Unit Tests
- Scraping components (crawler, downloader, validator, deduplicator)
- Labeling logic
- Training dataset preparation
- API endpoints

### Integration Tests
- Full scraping pipeline → album creation
- Upload → labeling → training pipeline
- Error handling and retries

### Manual Testing
- Test with sites from `docs/card_sites.json`
- Verify JS-rendered sites work (Playwright)
- Test duplicate detection
- Verify caption quality
- End-to-end training run

---

## Success Criteria

### Phase 1 Complete When:
- ✅ Scraping works without training-data dependency
- ✅ Albums created with images and captions
- ✅ JavaScript-rendered sites supported
- ✅ Duplicate detection working
- ✅ Tests passing

### Phase 2 Complete When:
- ✅ Single and bulk image upload working
- ✅ Images added to new or existing albums
- ✅ Upload progress tracking
- ✅ Thumbnails generated

### Phase 3 Complete When:
- ✅ Images can be labeled individually or in batches
- ✅ NSFW detection working
- ✅ Manual label editing
- ✅ Caption quality acceptable for training
- ✅ UI shows labeling status

### Phase 4 Complete When:
- ✅ Training runs create valid LoRAs
- ✅ UI for creating and monitoring training
- ✅ LoRAs can be downloaded and integrated
- ✅ Trained LoRAs work in generation

---

## Risk Mitigation

### Risk: Scraping Code Incompatibility
**Mitigation:** Copy code early, test incrementally, maintain training-data as reference

### Risk: Training Quality Issues
**Mitigation:** Start with known-good datasets, validate caption quality, tune hyperparameters

### Risk: API Costs (Claude)
**Mitigation:** Make captioning optional, add cost estimation, implement caching

### Risk: Training Duration
**Mitigation:** Optimize dataset size, use gradient accumulation, provide accurate ETAs

---

## Documentation Updates Needed

1. **CLAUDE.md** - Remove training-data references, document scraping architecture
2. **ARCHITECTURE.md** - Update with new scraping package structure
3. **docs/plans/BACKEND_TASKS_CONSOLIDATED.md** - Update priorities
4. **docs/plans/FRONTEND_TASKS_CONSOLIDATED.md** - Update priorities
5. **Create docs/SCRAPING.md** - Document scraping configuration and usage
6. **Create docs/LABELING.md** - Document labeling workflow
7. **Create docs/TRAINING.md** - Document LoRA training workflow

---

**Next Steps:**
1. Review and approve this plan
2. Begin Sprint 1: Copy scraping code
3. Remove training-data dependency
4. Update all documentation

