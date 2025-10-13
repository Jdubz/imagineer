# Imagineer

AI Image Generation Toolkit built on Stable Diffusion and Hugging Face Diffusers.

## Features

- Generate images from text prompts using Stable Diffusion
- Fine-tune models on custom datasets using LoRA
- Memory-efficient inference optimizations
- Utility functions for image processing and batch generation
- Support for multiple Stable Diffusion versions (SD 1.5, SD 2.1, SDXL)

## Prerequisites

- Python 3.12+
- NVIDIA GPU with 8GB+ VRAM (recommended)
- CUDA 12.1+ and NVIDIA drivers installed

## Setup

1. **Clone the repository**
```bash
git clone https://github.com/Jdubz/imagineer.git
cd imagineer
```

2. **Install Python virtual environment package**
```bash
sudo apt install python3.12-venv
```

3. **Create and activate virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate
```

4. **Install dependencies**
```bash
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

## Quick Start

### Generate an Image

```bash
python examples/basic_inference.py \
  --prompt "a beautiful landscape with mountains and lake, sunset" \
  --output outputs/landscape.png \
  --steps 25
```

### Fine-tune with LoRA

Prepare your training data:
- Place images in `data/training/`
- Create matching `.txt` files with captions for each image

Train the model:
```bash
python examples/train_lora.py \
  --data-dir data/training \
  --output-dir checkpoints/my_lora \
  --steps 1000
```

## Project Structure

```
imagineer/
├── src/imagineer/        # Core library code
│   ├── __init__.py
│   └── utils.py          # Utility functions
├── examples/             # Example scripts
│   ├── basic_inference.py
│   └── train_lora.py
├── data/                 # Training data
├── models/               # Downloaded model cache
├── outputs/              # Generated images
├── checkpoints/          # Training checkpoints
├── config.yaml           # Configuration file
└── requirements.txt      # Python dependencies
```

## Configuration

Edit `config.yaml` to customize default settings for model paths, generation parameters, and training options.

## Hardware Requirements

**Minimum:**
- 8GB RAM
- GPU with 4GB VRAM
- 20GB disk space

**Recommended:**
- 16GB+ RAM
- GPU with 8GB+ VRAM (RTX 3060, RTX 3080, etc.)
- 50GB+ disk space for models

## Available Models

The toolkit supports all Stable Diffusion models from Hugging Face:
- `runwayml/stable-diffusion-v1-5` (default, best compatibility)
- `stabilityai/stable-diffusion-2-1` (improved quality)
- `stabilityai/stable-diffusion-xl-base-1.0` (highest quality, requires more VRAM)

## License

See LICENSE file for details.
