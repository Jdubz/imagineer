# Imagineer Architecture

**Last Updated:** 2025-11-04

## Overview

Imagineer is an AI Image Generation Toolkit built on Stable Diffusion 1.5 with a focus on batch generation of themed card collections (playing cards, tarot, zodiac). The system supports multi-LoRA loading, template-based batch generation, AI-powered image labeling, and provides both REST API and web UI interfaces.

## Terminology

**CRITICAL DISTINCTION:**

- **Batch Template** (`BatchTemplate` model): A reusable recipe/blueprint that defines HOW to generate a collection of images. Stored in the `batch_templates` database table. Contains:
  - CSV data defining items to generate (e.g., 54 playing cards)
  - Prompt templates with placeholders
  - LoRA configurations
  - Generation settings (dimensions, negative prompts)
  - Example themes for user guidance

- **Album** (`Album` model): An output collection of generated images. Stored in the `albums` database table. Created when:
  - A batch template is executed with a user's custom theme (`source_type='batch_generation'`)
  - Images are manually scraped from the web (`source_type='scrape'`)
  - Images are manually curated (`source_type='manual'`)

- **Batch Generation Run** (`BatchGenerationRun` model): Execution tracking for a specific batch generation. Links a template to the resulting album, tracks progress (completed/failed items), and stores the user's theme and parameters.

**Key Difference:** Templates are *instructions* (reusable), Albums are *outputs* (one-time results). Think of templates as recipes and albums as the meals cooked from those recipes.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interfaces                          │
├─────────────────────────────────────────────────────────────────┤
│  Web UI (React)          CLI Scripts         REST API Clients   │
│  http://localhost:3000   examples/*.py       curl/Postman       │
└────────────────┬────────────────────────────────┬───────────────┘
                 │                                │
                 v                                v
         ┌───────────────────────────────────────────────────┐
         │         Flask REST API (server/api.py)            │
         │         Port: 10050 (configurable)                │
         ├───────────────────────────────────────────────────┤
         │  - Job Queue Management                           │
         │  - Batch Template Configuration Loading           │
         │  - Batch Generation Orchestration                 │
         │  - LoRA Configuration (Single/Multi)              │
         └─────────────────────┬─────────────────────────────┘
                               │
                               v
         ┌─────────────────────────────────────────────────┐
         │    Generation Worker (Background Thread)        │
         │    subprocess: examples/generate.py             │
         ├─────────────────────────────────────────────────┤
         │  - Loads Stable Diffusion Pipeline              │
         │  - Applies LoRA(s) at runtime                   │
         │  - Executes generation jobs sequentially        │
         └─────────────────────┬───────────────────────────┘
                               │
                               v
         ┌─────────────────────────────────────────────────┐
         │     Stable Diffusion 1.5 Pipeline               │
         │     (Hugging Face Diffusers)                    │
         ├─────────────────────────────────────────────────┤
         │  UNet + CLIP Text Encoder + VAE                 │
         │  + LoRA Adapters (PEFT)                         │
         │  DPMSolverMultistepScheduler                    │
         └─────────────────────────────────────────────────┘

         ┌─────────────────────────────────────────────────┐
         │     AI Labeling System (Celery Tasks)           │
         │     server/tasks/labeling.py                    │
         ├─────────────────────────────────────────────────┤
         │  - Image captioning                             │
         │  - NSFW classification                          │
         │  - Tag generation                               │
         │  - Album batch labeling                         │
         └─────────────────────┬───────────────────────────┘
                               │
                               v
         ┌─────────────────────────────────────────────────┐
         │   Claude CLI in Docker (Ephemeral Containers)   │
         │   server/services/labeling_cli.py               │
         ├─────────────────────────────────────────────────┤
         │  docker run --rm imagineer-claude-cli           │
         │  - Mounts: ~/.claude/.credentials.json          │
         │  - Mounts: image directory (read-only)          │
         │  - tmpfs: /home/node/.claude (writable)         │
         │  - Automatic cleanup after each job             │
         └─────────────────────────────────────────────────┘
```

## Directory Structure

```
imagineer/
├── server/
│   ├── api.py                    # Flask REST API server
│   ├── auth.py                   # OAuth authentication
│   ├── celery_app.py             # Celery task queue
│   ├── database.py               # SQLAlchemy models
│   ├── routes/                   # API route blueprints
│   │   ├── images.py             # Image management endpoints
│   │   ├── scraping.py           # Web scraping endpoints
│   │   └── training.py           # LoRA training endpoints
│   ├── services/
│   │   └── labeling_cli.py       # Claude CLI Docker wrapper
│   └── tasks/
│       ├── labeling.py           # AI labeling Celery tasks
│       ├── scraping.py           # Web scraping tasks
│       └── training.py           # LoRA training tasks
├── docker/
│   └── claude-cli/
│       └── Dockerfile            # Claude CLI container image
├── examples/
│   ├── generate.py               # Core generation script (supports multi-LoRA)
│   ├── basic_inference.py        # Simple inference example
│   └── train_lora.py             # LoRA training script
├── data/
│   └── sets/                     # CSV data files for batch templates (not in repo)
│       ├── card_deck.csv         # 54 playing card prompts with visual layouts
│       ├── tarot_deck.csv        # 22 Major Arcana prompts
│       └── zodiac.csv            # 12 zodiac sign prompts
├── web/                          # React frontend
│   ├── src/
│   │   ├── App.jsx              # Main app with routing
│   │   ├── Gallery.jsx          # Batch gallery viewer
│   │   └── ...
│   └── package.json
├── public/                       # Compiled frontend
├── docs/                         # Documentation
├── config.yaml                   # Main app configuration
└── requirements.txt              # Python dependencies

External Directories (configured in config.yaml):
/mnt/speedy/imagineer/
├── models/
│   └── lora/                     # LoRA weight files (.safetensors)
├── sets/
│   └── config.yaml               # Batch template configurations
├── checkpoints/                  # LoRA training outputs
└── outputs/                      # Generated images
    └── [album_name]/             # Album subdirectories (batch outputs)
        ├── *.png                 # Generated images
        └── *.json                # Metadata sidecars
```

## Core Components

### 1. REST API Server (`server/api.py`)

**Port:** 10050 (configurable via `FLASK_RUN_PORT`)

**Key Features:**
- Job queue with background worker thread
- Batch template configuration loading and validation
- Batch generation orchestration
- Dynamic template discovery from CSV files
- Multi-LoRA configuration support

**Key Endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/config` | GET/PUT | Manage global configuration |
| `/api/generate` | POST | Submit single generation job |
| `/api/batch-templates` | GET | List all batch templates |
| `/api/batch-templates/<id>` | GET | Get template details with CSV data |
| `/api/batch-templates/<id>/generate` | POST | Generate batch from template with user theme |
| `/api/batch-templates/<id>/runs` | GET | List generation runs for template |
| `/api/batch-templates/<id>/runs/<run_id>` | GET | Get run status for progress polling |
| `/api/albums` | GET | List albums (supports ?source_type filter) |
| `/api/albums/<id>` | GET | Get album details with images |
| `/api/jobs` | GET | View job queue and history |
| `/api/jobs/<id>` | GET/DELETE | Manage specific job |
| `/api/batches` | GET | List batch outputs (legacy) |
| `/api/batches/<id>` | GET | View batch images (legacy) |
| `/api/images` | GET | List generated images |
| `/api/images/<id>/file` | GET | Serve generated image |
| `/api/themes/random` | GET | Generate random theme |
| `/api/health` | GET | Health check |

**Job Queue Architecture:**
```python
job_queue = queue.Queue()      # FIFO queue for pending jobs
current_job = None              # Currently executing job
job_history = []                # Completed jobs (last 50)

# Background worker thread
process_jobs() -> subprocess.run(examples/generate.py)
```

### 2. Generation Script (`examples/generate.py`)

**Purpose:** Core image generation with LoRA support

**Key Features:**
- Multi-LoRA loading via PEFT adapters
- Backward compatible with single LoRA
- Automatic device detection (CUDA/MPS/CPU)
- DPMSolverMultistepScheduler for fast inference
- Metadata sidecar JSON files
- Seed control for reproducibility

**LoRA Loading Flow:**
```python
# Single LoRA (backward compatible)
--lora-path <path> --lora-weight <weight>
→ pipe.load_lora_weights() → pipe.fuse_lora()

# Multiple LoRAs (new)
--lora-paths <path1> <path2> --lora-weights <w1> <w2>
→ pipe.load_lora_weights(adapter_name=stem) for each
→ pipe.set_adapters([names], adapter_weights=[weights])
```

**Command-Line Interface:**
```bash
python examples/generate.py \
  --prompt "Your prompt" \
  --lora-paths /path/to/lora1.safetensors /path/to/lora2.safetensors \
  --lora-weights 0.6 0.3 \
  --width 512 --height 720 \
  --steps 25 --seed 42 \
  --output outputs/image.png
```

### 3. Batch Template System

**Database Table:** `batch_templates`

**Purpose:** Store reusable batch generation recipes in the database

**Structure (BatchTemplate model):**
```python
class BatchTemplate(db.Model):
    id: int                      # Primary key
    name: str                    # Display name (e.g., "Playing Card Deck")
    description: str             # Description of template
    csv_data: str                # JSON array of CSV rows
    base_prompt: str             # Base prompt for all items
    prompt_template: str         # Template with placeholders like "{value} of {suit}"
    style_suffix: str            # Technical style terms appended to prompts
    example_theme: str           # Example theme to inspire users
    width: int                   # Image width (default 512)
    height: int                  # Image height (default 720)
    negative_prompt: str         # Things to avoid in generation
    lora_config: str             # JSON array of LoRA configurations
    created_by: str              # User email who created template
    created_at: datetime         # Creation timestamp
```

**LoRA Configuration Format (JSON):**
```json
[
  {"path": "/path/to/lora1.safetensors", "weight": 0.6},
  {"path": "/path/to/lora2.safetensors", "weight": 0.3}
]
```

**Prompt Construction Order:**
```
[Base Prompt] [User Theme] [CSV Data via Template] [Style Suffix]
```

This order follows SD best practices where front words have strongest influence.

**CSV Template Format:**

CSV files define the prompts for batch generation. Each row becomes one image generation job.

`card_deck.csv`:
```csv
value,suit,personality,visual_layout
Ace,Spades,The Seeker - represents new...,"Large single black spade..."
Two,Hearts,The Pair - symbolizes union...,"Two red heart symbols..."
...
```

Each row's columns are available as `{column}` in the prompt_template, allowing dynamic prompt generation for each item.

### 4. LoRA System

**Storage:** `/mnt/speedy/imagineer/models/lora/`

**Supported Format:** `.safetensors` (Stable Diffusion 1.5 compatible)

**Working LoRAs (Tested 2025-10-13):**
- `Card_Fronts-000008.safetensors` (24MB) - Playing cards, clean layout
- `Devil Carnival-000001.safetensors` (36MB) - Artistic tarot style
- `Tarot.safetensors` (144MB) - Mystical card aesthetic

**SDXL LoRAs (Incompatible with SD 1.5):**
- Files >150MB are typically SDXL
- Will fail to load with dimension mismatch errors

**Multi-LoRA Stacking:**

LoRAs are combined additively with weighted influence:
```python
# Example: Playing card structure + mystical aesthetic
loras:
  - path: "Card_Fronts-000008.safetensors"
    weight: 0.6  # Strong influence on card structure
  - path: "Tarot.safetensors"
    weight: 0.2  # Subtle mystical styling
```

**Weight Ranges:**
- 0.0 = No effect
- 0.3-1.0 = Typical range
- >1.0 = Over-emphasized (can cause artifacts)

### 5. Web Frontend (`web/`)

**Framework:** React 18 + Vite

**Key Components:**

- `App.jsx` - Main app with React Router
- `Gallery.jsx` - Batch gallery with navigation (Next/Previous)
- `AlbumsTab.jsx` - Template selection and batch generation
- `ConfigPanel.jsx` - Configuration management
- `JobsPanel.jsx` - Job queue monitoring

**Gallery Features:**
- Navigate between batch outputs
- Grid view of all cards in batch
- Metadata display (prompt, settings, LoRAs)
- Direct API integration (no state management library)

**Build & Deploy:**
```bash
cd web
npm install
npm run build  # Outputs to ../public/
```

**Dev Server:** `npm run dev` (port 3000)

### 6. AI Labeling System

**Purpose:** Automated image captioning, NSFW classification, and tag generation using Claude vision AI.

**Architecture:** Claude CLI running in ephemeral Docker containers (no direct API integration).

**Key Components:**

#### Docker Container (`docker/claude-cli/Dockerfile`)
```dockerfile
FROM node:20-slim
RUN npm install -g @anthropic-ai/claude-code
USER node  # Non-root for --dangerously-skip-permissions flag
HEALTHCHECK CMD claude --version || exit 1
```

**Build:**
```bash
docker build -t imagineer-claude-cli:latest docker/claude-cli/
```

#### Labeling Service (`server/services/labeling_cli.py`)

**Class:** `ClaudeCliLabeler`

**Key Method:**
```python
def label_image(self, image_path: str, prompt_type: str = "default", timeout: int = 120):
    """Label image using Claude CLI in ephemeral Docker container"""
    docker_cmd = [
        "docker", "run", "--rm",  # Ephemeral container
        "-v", f"{image_path.parent}:/images:ro",  # Mount image dir read-only
        "--tmpfs", "/home/node/.claude:uid=1000,gid=1000",  # Writable CLI dir
        "-v", f"{self.credentials_path}:/tmp/host-creds.json:ro",  # Mount credentials
        self.DOCKER_IMAGE,
        "sh", "-c",
        f"cp /tmp/host-creds.json /home/node/.claude/.credentials.json && "
        f"claude --print --dangerously-skip-permissions --output-format json '{prompt}'"
    ]
    result = subprocess.run(docker_cmd, capture_output=True, timeout=timeout)
    return self._parse_response(result.stdout, result.stderr)
```

**Credentials:** Mounted from `~/.claude/.credentials.json` (no API keys in environment).

**Prompt Types:**
- `default` - General description, NSFW rating, 5-10 tags
- `sd_training` - Detailed caption for Stable Diffusion training

**Output Format:**
```python
{
    "status": "success",
    "description": "Detailed image caption",
    "nsfw_rating": "SAFE",  # SAFE, SUGGESTIVE, ADULT, EXPLICIT
    "tags": ["tag1", "tag2", "tag3"],
    "raw_response": "..."
}
```

#### Celery Tasks (`server/tasks/labeling.py`)

**Task:** `label_image_task(image_id, prompt_type)`
- Labels single image asynchronously
- Updates database: `image.is_nsfw`, creates `Label` records
- Called via API: `POST /api/labeling/image/<id>`

**Task:** `label_album_task(album_id, prompt_type, force)`
- Labels all images in an album
- Skips already-labeled images unless `force=True`
- Progress tracking via Celery state updates
- Called via API: `POST /api/labeling/album/<id>`

**Label Storage:**
```python
# Caption stored as Label with type="caption"
Label(image_id=image.id, label_text=description, label_type="caption",
      source_model="claude-3-5-sonnet")

# Tags stored as separate Label records with type="tag"
for tag in tags:
    Label(image_id=image.id, label_text=tag, label_type="tag",
          source_model="claude-3-5-sonnet")
```

**NSFW Classification:**
```python
# Boolean flag: blur or not blur
image.is_nsfw = nsfw_rating in {"ADULT", "EXPLICIT"}
```

#### Key Benefits of Docker/CLI Approach

1. **Context Isolation** - Fresh container per labeling job prevents context pollution
2. **Ephemeral** - `--rm` flag ensures automatic cleanup after each job
3. **Security** - Credentials mounted read-only, no API keys in environment
4. **Sandboxing** - Container isolation prevents interference between jobs
5. **No Rate Limits** - Uses Claude Code account (not API account)

#### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/labeling/image/<id>` | POST | Queue single image labeling task |
| `/api/labeling/album/<id>` | POST | Queue album batch labeling task |

**Request:**
```json
{
  "prompt_type": "sd_training",  // "default" or "sd_training"
  "force": false  // For albums: relabel already-labeled images
}
```

**Response:**
```json
{
  "status": "queued",
  "task_id": "celery-task-id"
}
```

### 7. Configuration (`config.yaml`)

**Location:** `/home/jdubz/Development/imagineer/config.yaml`

**Structure:**
```yaml
model:
  default: "runwayml/stable-diffusion-v1-5"
  cache_dir: "/mnt/speedy/imagineer/models"

generation:
  width: 512
  height: 512
  steps: 25
  guidance_scale: 8.0
  negative_prompt: "blurry, low quality, ..."
  batch_size: 1
  num_images: 1

output:
  directory: "/mnt/speedy/imagineer/outputs"
  save_metadata: true

sets:
  directory: "/mnt/speedy/imagineer/sets"

training:
  learning_rate: 1e-4
  rank: 4
  alpha: 8
  dropout: 0.1
  max_steps: 1000
  save_every: 100
  output_dir: "/mnt/speedy/imagineer/checkpoints"

hardware:
  device: "cuda"  # auto, cuda, mps, cpu
  mixed_precision: true
  enable_attention_slicing: true
  enable_vae_slicing: false
  enable_xformers: false
```

## Data Flow

### Single Image Generation

```
User → API: POST /api/generate
  ↓
API: Create job → Add to queue
  ↓
Worker: Dequeue job
  ↓
Worker: subprocess.run(generate.py)
  ↓
generate.py: Load SD pipeline → Load LoRA(s) → Generate → Save
  ↓
Worker: Update job status → Add to history
  ↓
User → API: GET /api/jobs/<id> (poll for completion)
  ↓
User → API: GET /api/images/<id>/file
```

### Batch Generation

```
User → API: POST /api/batch-templates/<template_id>/generate
  {album_name: "My Steampunk Cards", user_theme: "gothic steampunk aesthetic"}
  ↓
API: Load BatchTemplate from database
  - Parse CSV data (JSON array of item rows)
  - Load LoRA config, dimensions, prompts
  ↓
API: Create BatchGenerationRun record
  - Links to template_id
  - Stores user_theme and album_name
  - Status: "queued" → "processing"
  ↓
API: For each CSV row:
  - Construct prompt: [base_prompt] [user_theme] [csv_row via template] [style_suffix]
  - Create generation job with:
    - Prompt, LoRAs, dimensions, negative_prompt
    - batch_generation_run_id for tracking
  - Add to job queue
  ↓
Worker: Process jobs sequentially
  - Each job runs examples/generate.py
  - Outputs to batch output directory
  - Updates BatchGenerationRun progress (completed_items/failed_items)
  ↓
Worker: When all jobs complete
  - Create new Album record
    - source_type='batch_generation'
    - source_id=run.id
  - Link all generated images to album
  - Update run.status='completed', run.album_id=album.id
  ↓
Frontend: Poll GET /api/batch-templates/<id>/runs/<run_id>
  - Shows progress toast (X/Y complete)
  - On completion, redirects to album
  ↓
User → API: GET /api/albums/<album_id>
  ↓
Frontend: Display album with all generated images
```

### Image Labeling (AI-Powered)

```
User → API: POST /api/labeling/image/<id>
  {prompt_type: "sd_training"}
  ↓
API: Queue Celery task → label_image_task.delay(image_id, prompt_type)
  ↓
Celery Worker: Execute label_image_task
  ↓
labeling_cli.py: Build Docker command
  ↓
Docker: Spawn ephemeral container
  - Mount ~/.claude/.credentials.json (read-only)
  - Mount image directory (read-only)
  - Create tmpfs for CLI working directory
  ↓
Container: Copy credentials → Run claude CLI → Parse JSON output
  ↓
Container: Exit (automatic cleanup via --rm)
  ↓
Celery Task: Parse response
  - Update image.is_nsfw (boolean)
  - Create Label records (caption + tags)
  - Commit to database
  ↓
User → API: Poll task status or wait for completion
  ↓
User → API: GET /api/images/<id>?include=labels
```

**Album Batch Labeling:**
Same flow as single image, but `label_album_task` iterates through all unlabeled images in an album, calling `label_image_with_claude()` for each.

## Key Technical Details

### Stable Diffusion Pipeline

**Model:** `runwayml/stable-diffusion-v1-5`

**Components:**
- UNet: Diffusion denoiser
- CLIP Text Encoder: Converts prompts to embeddings
- VAE: Encodes/decodes between latent and pixel space

**Scheduler:** DPMSolverMultistepScheduler (fast, 20-25 steps typical)

**Precision:**
- CUDA: float16 (faster, less VRAM)
- CPU/MPS: float32 (more stable)

**Memory Optimizations:**
- Attention slicing: Enabled by default (reduces VRAM)
- VAE slicing: Optional (further VRAM reduction)
- xformers: Optional (fastest, requires separate install)

### LoRA (Low-Rank Adaptation)

**Library:** PEFT (Parameter-Efficient Fine-Tuning)

**How it works:**
- Injects small trainable adapters into UNet attention layers
- Base model weights remain frozen
- Adapter weights ~10-200MB vs ~4GB base model
- Multiple adapters can be loaded simultaneously

**Loading Process:**
```python
# Single LoRA
pipe.load_lora_weights(folder, weight_name=file)
pipe.fuse_lora(lora_scale=weight)

# Multiple LoRAs
for lora in loras:
    pipe.load_lora_weights(folder, weight_name=file, adapter_name=name)
pipe.set_adapters([name1, name2], adapter_weights=[w1, w2])
```

**Adapter Stacking:**
LoRAs combine additively in the model's attention layers:
```
Output = Base + (Adapter1 * weight1) + (Adapter2 * weight2)
```

### Image Dimensions

**Requirements:**
- Width and height must be divisible by 8 (VAE constraint)
- Typical: 512x512 (square), 512x720 (portrait), 720x512 (landscape)
- Max recommended: 768x768 (higher needs more VRAM)

**Aspect Ratios:**
- Playing Cards: 512x720 (5:7 ratio)
- Tarot Cards: 512x896 (11:19 ratio)
- Square: 512x512

## Dependencies

### Python (requirements.txt)

**Core:**
- `torch>=2.0.0` - PyTorch for model execution
- `diffusers==0.31.0` - Hugging Face Diffusers library
- `transformers==4.47.0` - CLIP text encoder
- `accelerate>=0.25.0` - Training acceleration
- `peft>=0.17.0` - LoRA adapter support (REQUIRED for multi-LoRA)

**Version Constraints:**
- `diffusers==0.31.0` and `transformers==4.47.0` are tested together
- Newer versions may have compatibility issues
- `peft>=0.17.0` required for LoRA loading

**API:**
- `flask>=3.0.0` - REST API server
- `flask-cors>=4.0.0` - CORS support
- `celery>=5.3.0` - Distributed task queue
- `redis>=5.0.0` - Celery message broker

**AI Labeling:**
- **Docker** - Required for Claude CLI containers
- **Claude CLI** - Installed in Docker image via `npm install -g @anthropic-ai/claude-code`
- ~~`anthropic>=0.25.0`~~ - Removed in favor of CLI approach

**Utilities:**
- `Pillow>=10.0.0` - Image processing
- `pyyaml>=6.0.0` - Configuration files
- `safetensors>=0.4.0` - Safe model loading

### JavaScript (web/package.json)

**Framework:**
- `react@^18.2.0` - UI library
- `react-dom@^18.2.0` - DOM rendering
- `react-router-dom@^6.27.0` - Routing

**Build:**
- `vite@^5.1.0` - Fast build tool
- `@vitejs/plugin-react@^4.2.1` - React plugin

## Performance Characteristics

**Generation Times (NVIDIA GPU, 25 steps):**
- Single 512x512 image: ~5-7 seconds
- Single 512x720 image: ~6-8 seconds
- With 1 LoRA: +0-1 second overhead
- With 2 LoRAs: +0-2 seconds overhead

**Batch Generation:**
- 54-card deck: ~6-8 minutes total
- Sequential processing (one at a time)
- Can be parallelized in future with multiple GPUs

**VRAM Usage:**
- Base SD 1.5: ~4GB
- With LoRA: ~4.5GB
- With 2 LoRAs: ~5GB
- Attention slicing reduces by ~1-2GB

**AI Labeling Times:**
- Single image labeling: ~10-20 seconds (includes Docker startup)
- Album batch labeling (10 images): ~2-4 minutes
- Docker container overhead: ~2-3 seconds per image
- Claude API latency: ~8-15 seconds per image

**Labeling Throughput:**
- Sequential processing (one at a time)
- Limited by Anthropic rate limits (not API rate limits)
- Fresh Docker container per image prevents context pollution

## Security Considerations

**API (server/api.py):**
- ✅ Path traversal validation on set names and filenames
- ✅ Output directory sandboxing
- ✅ Parameter validation (ranges, types)
- ✅ Prompt length limits (2000 chars)
- ⚠️ No authentication (local network use only)
- ⚠️ Config update endpoint allows full config replacement (dangerous)

**Recommended:**
- Run on trusted local network only
- Use firewall rules to restrict port 10050 access
- Consider adding API key authentication for production

## Troubleshooting

### Common Issues

**1. LoRA fails to load: "PEFT backend is required"**
- Solution: `pip install peft>=0.17.0`

**2. LoRA fails with dimension mismatch**
- Cause: SDXL LoRA used with SD 1.5 model
- Solution: Only use LoRAs <150MB designed for SD 1.5

**3. Import error: "cannot import name 'EncoderDecoderCache'"**
- Cause: Version incompatibility between transformers and diffusers
- Solution: `pip install diffusers==0.31.0 transformers==4.47.0`

**4. CUDA out of memory**
- Solution: Enable attention slicing in config.yaml
- Solution: Reduce image dimensions (768→512)
- Solution: Close other GPU applications

**5. Batch images wrong: "Ace shows as Five"**
- Cause: Base SD 1.5 doesn't understand card structure
- Solution: Use LoRAs (Card_Fronts-000008.safetensors recommended)

**6. Claude CLI labeling fails: "credentials not found"**
- Cause: Missing `~/.claude/.credentials.json` file
- Solution: Run `claude setup-token` to authenticate

**7. Docker labeling timeout**
- Cause: Claude API rate limits or slow response
- Solution: Increase timeout in `labeling_cli.py` (default 120s)

**8. Docker image not found**
- Cause: Claude CLI Docker image not built
- Solution: `docker build -t imagineer-claude-cli:latest docker/claude-cli/`

**9. Labeling fails with permission error**
- Cause: Docker can't read credentials file
- Solution: Check `~/.claude/.credentials.json` has read permissions

### Debug Commands

```bash
# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available())"

# Check VRAM usage
nvidia-smi

# Test single generation
python examples/generate.py --prompt "test" --steps 5 --output test.png

# Check API health
curl http://localhost:10050/api/health

# View job queue
curl http://localhost:10050/api/jobs

# List available LoRAs
ls -lh /mnt/speedy/imagineer/models/lora/*.safetensors

# Test Claude CLI Docker image
docker run --rm imagineer-claude-cli:latest claude --version

# Test labeling with real image
docker run --rm \
  -v /path/to/image.png:/images/test.png:ro \
  -v ~/.claude/.credentials.json:/tmp/creds.json:ro \
  --tmpfs /home/node/.claude:uid=1000,gid=1000 \
  imagineer-claude-cli:latest \
  sh -c 'cp /tmp/creds.json /home/node/.claude/.credentials.json && \
         claude --print --dangerously-skip-permissions --output-format json \
         "Analyze /images/test.png"'

# Check Celery worker status
celery -A server.celery_app inspect active

# Check Redis connection
redis-cli ping
```

## Future Enhancements

**Planned:**
- [ ] Parallel batch generation (multi-GPU)
- [ ] Real-time generation progress via WebSocket
- [ ] LoRA training UI
- [ ] Custom negative prompts per set item
- [ ] Img2img support for refinement
- [ ] ControlNet integration
- [ ] SDXL support (separate pipeline)

**Under Consideration:**
- [ ] User authentication
- [ ] Job priority queue
- [ ] Result caching
- [ ] Automatic upscaling
- [ ] Video generation

## Development Workflow

**Setup:**
```bash
# Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd web && npm install

# Claude CLI credentials (for AI labeling)
claude setup-token  # Follow prompts to authenticate

# Docker image for labeling
docker build -t imagineer-claude-cli:latest docker/claude-cli/

# Redis (for Celery)
# Install via package manager or Docker
redis-server  # Start Redis server
```

**Start Development:**
```bash
# Terminal 1: API server
source venv/bin/activate
python server/api.py

# Terminal 2: Celery worker (for AI labeling tasks)
source venv/bin/activate
celery -A server.celery_app worker --loglevel=info

# Terminal 3: Frontend dev server
cd web
npm run dev
```

**Testing:**
```bash
# Run test script for all LoRAs
./test_all_loras.sh

# Single card test
python examples/generate.py --prompt "test" --steps 5
```

**Pre-commit Checks:**
```bash
black src/ examples/
isort src/ examples/
flake8 src/ examples/
```

## Version History

**v1.1.0 (2025-10-27):**
- ✅ AI-powered image labeling via Claude CLI in Docker
- ✅ NSFW classification and content filtering
- ✅ Automated caption generation for training datasets
- ✅ Album batch labeling with Celery tasks
- ✅ Context isolation via ephemeral Docker containers
- ✅ Removed direct Anthropic API dependency
- ✅ OAuth authentication with Google
- ✅ Web scraping capabilities
- ✅ LoRA training workflows

**v1.0.0 (2025-10-13):**
- ✅ Multi-LoRA support via PEFT
- ✅ Template-based batch generation
- ✅ React album gallery with navigation
- ✅ REST API with job queue
- ✅ Explicit visual layouts for card_deck
- ✅ Compatible version locking (diffusers 0.31.0, transformers 4.47.0)

**Initial (2025-10-11):**
- Basic SD 1.5 inference
- CSV batch templates
- Flask API
- Web UI

---

**For questions or contributions, see:**
- `docs/API.md` - Complete API documentation
- `docs/CONTRIBUTING.md` - Contribution guidelines
- `CLAUDE.md` - Claude Code guidance (project instructions)
