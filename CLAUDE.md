# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Imagineer is an AI Image Generation Toolkit built on Stable Diffusion and Hugging Face Diffusers. It provides tools for generating images from text prompts and fine-tuning models using LoRA (Low-Rank Adaptation).

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

## Common Commands

### Image Generation
```bash
# Basic image generation
python examples/basic_inference.py \
  --prompt "your prompt here" \
  --output outputs/image.png \
  --steps 25

# With specific parameters
python examples/basic_inference.py \
  --prompt "your prompt" \
  --negative-prompt "blurry, low quality" \
  --width 512 \
  --height 512 \
  --guidance-scale 7.5 \
  --seed 42
```

### LoRA Training
```bash
# Fine-tune model with custom dataset
python examples/train_lora.py \
  --data-dir data/training \
  --output-dir checkpoints/my_lora \
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

### Core Components

**src/imagineer/utils.py**
Central utility module providing:
- `save_image_with_metadata()`: Saves images with JSON metadata sidecars
- `create_image_grid()`: Creates grid layouts from multiple images
- `get_device()`: Auto-detects optimal device (cuda/mps/cpu)
- `get_optimal_dtype()`: Returns appropriate dtype for device (fp16 on cuda, fp32 elsewhere)
- `preprocess_image()`: Handles image resizing and center cropping
- `calculate_vram_usage()`: Monitors GPU memory on CUDA devices
- `generate_filename()`: Creates timestamped filenames from prompts
- `load_prompt_list()`: Loads batch prompts from text files

**examples/basic_inference.py**
Inference pipeline using StableDiffusionPipeline with:
- DPMSolverMultistepScheduler for faster generation
- Automatic device detection and dtype selection
- Memory optimizations (attention slicing)
- Seed control for reproducibility

**examples/train_lora.py**
LoRA fine-tuning implementation featuring:
- `ImageCaptionDataset`: Loads image-caption pairs (looks for .txt files matching image names)
- Custom LoRA layers via LoRAAttnProcessor applied to UNet attention processors
- Training loop with noise prediction and MSE loss
- Checkpoint saving at regular intervals

### Configuration

**config.yaml**
Central configuration for:
- Model selection (default: runwayml/stable-diffusion-v1-5)
- Generation parameters (size, steps, guidance_scale, negative_prompt)
- Training hyperparameters (learning_rate, LoRA rank/alpha/dropout)
- Hardware settings (device auto-detection, mixed precision, memory optimizations)

### Data Organization

```
data/training/           # Training images with .txt caption files
models/                  # Hugging Face model cache
outputs/                 # Generated images
checkpoints/             # LoRA training checkpoints
```

## Key Design Patterns

**Model Loading:**
All scripts load models via `StableDiffusionPipeline.from_pretrained()` with conditional dtype based on device (fp16 for CUDA, fp32 otherwise). Safety checker is disabled for faster inference.

**Memory Management:**
- Attention slicing enabled by default on CUDA
- VAE slicing and xformers available but opt-in
- LoRA training uses memory-efficient parameter updates

**Dataset Format:**
Training expects image files (.jpg/.png) with matching .txt caption files in same directory. Falls back to filename as caption if .txt missing.

## Important Notes

- First run will download ~5GB models from Hugging Face Hub to `models/` cache
- LoRA training modifies only attention processor parameters, keeping base model frozen
- Generated images are saved with optional JSON metadata sidecars containing generation parameters
- All scripts accept command-line arguments; check `--help` for full options
