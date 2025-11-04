# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Imagineer is an AI Image Generation Toolkit built on Stable Diffusion 1.5 with a focus on batch generation of themed card collections (playing cards, tarot, zodiac). The system supports multi-LoRA loading, template-based batch generation, and provides both REST API and web UI interfaces.

## Terminology

- **Batch Generation Template**: A CSV file + configuration (prompts, LoRAs, dimensions) that defines HOW to generate a collection of images. Stored as Albums with `is_set_template=True`.
- **Album**: An output collection of generated images. Created when a batch template is executed with a user's custom theme.
- **Batch**: A single execution of a template that creates an album.

**For detailed architecture documentation, see:** `docs/ARCHITECTURE.md`

## Environment Setup

**Prerequisites:**
- Python 3.12+ (3.8+ supported but 3.12 recommended)
- NVIDIA GPU with 8GB+ VRAM recommended
- CUDA 12.1+ and NVIDIA drivers

**Initial Setup:**
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

**Development Dependencies:**
```bash
pip install -e ".[dev]"  # Installs pytest, black, flake8, isort
```

## Deployment Architecture

**Production Setup:**
- **Frontend:** Firebase Hosting (https://imagineer-generator.web.app)
- **Backend API:** Gunicorn on localhost:10050
- **Tunnel:** Cloudflare Tunnel (imagineer-api.joshwentworth.com)
- **Public Directory:** NO LONGER SERVED by Flask/nginx - Use Firebase only

**Admin Authentication:**
- Admin roles are configured in `server/users.json` (not in git)
- Copy `server/users.json.example` to `server/users.json` and add your email
- Format: `{"your-email@example.com": {"role": "admin"}}`
- Restart API after changes: `sudo systemctl restart imagineer-api`

**Architecture Diagram:**
```
Internet
   │
   ├─> Firebase Hosting ──────> React SPA (static files)
   │   (imagineer-generator.web.app)
   │
   └─> Cloudflare Tunnel ─────> Flask API (localhost:10050)
       (imagineer-api.joshwentworth.com)
```

**See:** `docs/deployment/FIREBASE_CLOUDFLARE_DEPLOYMENT.md` for full deployment guide

## Common Commands

### Development Mode

```bash
# Terminal 1: API Server (Port 10050)
source venv/bin/activate
python server/api.py

# Terminal 2: Web UI Dev Server (Port 3000)
cd web && npm run dev
```

### Production Services

```bash
# Backend API (Gunicorn)
sudo systemctl status imagineer-api
sudo systemctl restart imagineer-api
sudo journalctl -u imagineer-api -f

# Cloudflare Tunnel
sudo systemctl status cloudflared-imagineer-api
sudo journalctl -u cloudflared-imagineer-api -f

# Frontend Deployment
cd web && npm run build
firebase deploy --only hosting
```

### Image Generation

**Single LoRA:**
```bash
python examples/generate.py \
  --prompt "your prompt here" \
  --lora-path /mnt/speedy/imagineer/models/lora/Card_Fronts-000008.safetensors \
  --lora-weight 0.6 \
  --width 512 --height 720 --steps 25
```

**Multiple LoRAs (Stacking):**
```bash
python examples/generate.py \
  --prompt "PlayingCards. Ace of Spades..." \
  --lora-paths /path/to/lora1.safetensors /path/to/lora2.safetensors \
  --lora-weights 0.6 0.3 \
  --width 512 --height 720 --steps 25
```

**Via API:**
```bash
# Single generation
curl -X POST http://localhost:10050/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "your prompt", "steps": 25}'

# Batch generation from template
curl -X POST http://localhost:10050/api/albums/<template_id>/generate \
  -H "Content-Type: application/json" \
  -d '{"user_theme": "gothic style"}'
```

### Testing LoRAs
```bash
# Test all LoRAs in lora directory
./test_all_loras.sh

# Results in: /mnt/speedy/imagineer/outputs/lora_tests/
```

### LoRA Training
```bash
# Fine-tune model with custom dataset
python examples/train_lora.py \
  --data-dir data/training \
  --output-dir /mnt/speedy/imagineer/checkpoints/my_lora \
  --steps 1000 \
  --rank 4 \
  --learning-rate 1e-4
```

### Code Quality
```bash
# Format code
black src/ examples/

# Sort imports
isort src/ examples/

# Lint
flake8 src/ examples/

# Run tests (when available)
pytest
```

## Architecture

**See `docs/ARCHITECTURE.md` for complete system architecture documentation.**

### Core Components

**server/api.py** - Flask REST API (Port 10050)
- Job queue with background worker
- Template-based batch generation
- Multi-LoRA configuration support
- Dynamic batch template discovery

**examples/generate.py** - Core generation script
- Multi-LoRA loading via PEFT adapters
- Backward compatible with single LoRA
- DPMSolverMultistepScheduler for fast inference
- Metadata JSON sidecars

**web/** - React Frontend (Port 3000)
- Album gallery with navigation
- Batch template selection and generation UI
- Real-time job queue monitoring

**examples/train_lora.py** - LoRA training
- Custom LoRA fine-tuning on datasets
- ImageCaptionDataset with .txt caption files

### Configuration Files

**config.yaml** - Main application config
- Model, generation, training, hardware settings
- Paths to external directories

**/mnt/speedy/imagineer/sets/config.yaml** - Batch template definitions
- Per-template prompts, dimensions, LoRAs, negative prompts
- Multi-LoRA stacking configuration
- CSV data defining items to generate

**firebase.json** - Firebase Hosting configuration
- SPA routing rules
- Cache headers for static assets
- Security headers

**/etc/cloudflared/config.yml** - Cloudflare Tunnel configuration
- Routes imagineer-api.joshwentworth.com → localhost:10050
- Tunnel credentials and ingress rules

**Nginx (DEPRECATED):**
- `/etc/nginx/sites-available/imagineer` exists but is NOT used in production
- Port 8080 config for local testing only
- Production uses Cloudflare Tunnel + Firebase Hosting instead

### Data Organization

```
/home/jdubz/Development/imagineer/  # Repository
├── server/api.py                    # Flask API
├── examples/generate.py             # Generation script
├── web/                             # React UI
└── config.yaml                      # Main config

/mnt/speedy/imagineer/              # External storage
├── models/lora/*.safetensors        # LoRA weights
├── sets/
│   ├── config.yaml                  # Batch template configurations
│   ├── card_deck.csv                # 54 playing card prompts
│   ├── tarot_deck.csv               # 22 Major Arcana prompts
│   └── zodiac.csv                   # 12 zodiac sign prompts
├── checkpoints/                     # Training outputs
└── outputs/
    └── [album_name]/                # Album subdirectories (batch outputs)
        ├── *.png                    # Generated images
        └── *.json                   # Metadata sidecars
```

## Key Design Patterns

**Template-Based Batch Generation:**

Batch templates are stored as Albums with `is_set_template=True` and contain:
- CSV data with rows defining items to generate
- Base prompt, prompt template, style suffix
- LoRA configurations
- Generation settings (dimensions, negative prompt)

```yaml
# /mnt/speedy/imagineer/sets/config.yaml
card_deck:
  prompt_template: "{value} of {suit}. CARD LAYOUT: {visual_layout}"
  loras:
    - path: "/path/to/lora1.safetensors"
      weight: 0.6
    - path: "/path/to/lora2.safetensors"
      weight: 0.3
```

Prompt construction order: `[Base Prompt] [User Theme] [CSV Data] [Style Suffix]`

When executed, creates a new Album (output) with generated images.

**Multi-LoRA Loading:**
```python
# Single LoRA (backward compatible)
--lora-path <path> --lora-weight <weight>

# Multiple LoRAs (stacking)
--lora-paths <path1> <path2> --lora-weights <w1> <w2>
```

LoRAs combine additively: `Output = Base + (LoRA1 * w1) + (LoRA2 * w2)`

**Job Queue Architecture:**
- API enqueues jobs → Background worker processes sequentially
- Each job spawns `subprocess.run(examples/generate.py)`
- Job history kept for last 50 completions

**Memory Management:**
- Attention slicing enabled by default on CUDA (saves ~1-2GB VRAM)
- fp16 on CUDA, fp32 on CPU/MPS
- Safety checker disabled for performance

## Important Notes

**Dependencies:**
- **CRITICAL:** `peft>=0.17.0` required for LoRA loading
- **Version Lock:** `diffusers==0.31.0` and `transformers==4.47.0` are tested together
- Newer versions may have compatibility issues

**LoRA Compatibility:**
- Only SD 1.5 LoRAs work (typically <150MB)
- SDXL LoRAs (>150MB) will fail with dimension errors
- 3 working LoRAs tested: Card_Fronts-000008, Devil Carnival, Tarot

**First Run:**
- Downloads ~5GB SD 1.5 model from Hugging Face to model cache
- LoRAs must be manually downloaded to `/mnt/speedy/imagineer/models/lora/`

**File References:**
- Use `file_path:line_number` format when referencing code
- Example: "LoRA loading happens in examples/generate.py:137"

**Generated Images:**
- Saved with JSON metadata sidecars (prompt, settings, LoRAs, seed)
- Batch images organized in album subdirectories: `outputs/{album_name}/`
- Linked to Album records in the database for gallery viewing
