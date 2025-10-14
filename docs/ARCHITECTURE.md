# Imagineer Architecture

**Last Updated:** 2025-10-13

## Overview

Imagineer is an AI Image Generation Toolkit built on Stable Diffusion 1.5 with a focus on batch generation of themed card sets (playing cards, tarot, zodiac). The system supports multi-LoRA loading, set-based batch generation, and provides both REST API and web UI interfaces.

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
         │  - Set Configuration Loading                      │
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
```

## Directory Structure

```
imagineer/
├── server/
│   └── api.py                    # Flask REST API server
├── examples/
│   ├── generate.py               # Core generation script (supports multi-LoRA)
│   ├── basic_inference.py        # Simple inference example
│   └── train_lora.py             # LoRA training script
├── data/
│   └── sets/                     # Set definitions (not in repo)
│       ├── card_deck.csv         # 54 playing cards with visual layouts
│       ├── tarot_deck.csv        # 22 Major Arcana
│       └── zodiac.csv            # 12 zodiac signs
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
│   └── config.yaml               # Set-specific configurations
├── checkpoints/                  # LoRA training outputs
└── outputs/                      # Generated images
    └── [batch_id]/               # Batch subdirectories
        ├── *.png                 # Generated images
        └── *.json                # Metadata sidecars
```

## Core Components

### 1. REST API Server (`server/api.py`)

**Port:** 10050 (configurable via `FLASK_RUN_PORT`)

**Key Features:**
- Job queue with background worker thread
- Set configuration loading and validation
- Batch generation orchestration
- Dynamic set discovery from CSV files
- Multi-LoRA configuration support

**Key Endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/config` | GET/PUT | Manage global configuration |
| `/api/generate` | POST | Submit single generation job |
| `/api/generate/batch` | POST | Submit batch generation from set |
| `/api/sets` | GET | List available sets |
| `/api/sets/<name>/info` | GET | Get set details |
| `/api/jobs` | GET | View job queue and history |
| `/api/jobs/<id>` | GET/DELETE | Manage specific job |
| `/api/batches` | GET | List batch outputs |
| `/api/batches/<id>` | GET | View batch images |
| `/api/outputs/<path>` | GET | Serve generated images |
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

### 3. Set Configuration System

**Location:** `/mnt/speedy/imagineer/sets/config.yaml`

**Purpose:** Define batch generation templates for card sets

**Structure:**
```yaml
<set_id>:
  name: "Display Name"
  description: "Set description"
  csv_path: "data/sets/<set_id>.csv"
  base_prompt: "Base description that applies to all items"
  prompt_template: "{column1} of {column2}. {column3}"
  style_suffix: "Technical style terms"
  example_theme: "Example for user inspiration"
  width: 512
  height: 720
  negative_prompt: "Things to avoid"
  loras:  # Multi-LoRA support
    - path: "/path/to/lora1.safetensors"
      weight: 0.6
    - path: "/path/to/lora2.safetensors"
      weight: 0.3
```

**Prompt Construction Order:**
```
[Base Prompt] [User Theme] [CSV Data via Template] [Style Suffix]
```

This order follows SD best practices where front words have strongest influence.

**CSV Set Format:**

`card_deck.csv`:
```csv
value,suit,personality,visual_layout
Ace,Spades,The Seeker - represents new...,"Large single black spade..."
Two,Hearts,The Pair - symbolizes union...,"Two red heart symbols..."
...
```

Each row becomes one generation job with columns available as `{column}` in prompt_template.

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
- `SetSelector.jsx` - Set selection and batch generation
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

### 6. Configuration (`config.yaml`)

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
User → API: GET /api/outputs/<filename>
```

### Batch Generation

```
User → API: POST /api/generate/batch
  {set_name: "card_deck", user_theme: "gothic style"}
  ↓
API: Load set config & CSV
  ↓
API: For each CSV row:
  - Construct prompt from template
  - Create job with set dimensions, LoRAs, negative_prompt
  - Add to queue
  ↓
API: Create batch directory: outputs/{set_name}_{timestamp}/
  ↓
Worker: Process jobs sequentially
  - Each job outputs to batch directory
  - Filename: {timestamp}_{item_name}.png
  ↓
User → API: GET /api/batches/<batch_id>
  ↓
Gallery: Display all images in batch
```

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
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd web && npm install
```

**Start Development:**
```bash
# Terminal 1: API server
source venv/bin/activate
python server/api.py

# Terminal 2: Frontend dev server
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

**v1.0.0 (2025-10-13):**
- ✅ Multi-LoRA support via PEFT
- ✅ Set-based batch generation
- ✅ React gallery with batch navigation
- ✅ REST API with job queue
- ✅ Explicit visual layouts for card_deck
- ✅ Compatible version locking (diffusers 0.31.0, transformers 4.47.0)

**Initial (2025-10-11):**
- Basic SD 1.5 inference
- CSV set definitions
- Flask API
- Web UI

---

**For questions or contributions, see:**
- `docs/API.md` - Complete API documentation
- `docs/CONTRIBUTING.md` - Contribution guidelines
- `CLAUDE.md` - Claude Code guidance (project instructions)
