# Development Environment Setup

## Current System Architecture

### Hardware
- **GPU:** NVIDIA GeForce RTX 3080 (10GB VRAM)
- **CPU:** AMD Ryzen (PCI bus 0000:17:00.0)
- **Memory:** 16GB+ RAM
- **Display Configuration:**
  - Primary: 3440x1440@60Hz ultrawide (DP-4)
  - Secondary: 1920x1080@60Hz vertical (DP-3, left)
  - Tertiary: 1920x1080@60Hz vertical (DP-1, right)

### Software Stack
- **OS:** Ubuntu 24.04 LTS (or current)
- **Kernel:** Linux 6.14.0-33-generic
- **Driver:** NVIDIA 580.65.06 (open-source)
- **CUDA:** Version 13.0
- **Python:** 3.12+ (3.8+ supported)

## Installation & Configuration

### 1. System Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python venv and build tools
sudo apt install python3.12-venv build-essential
```

### 2. NVIDIA Driver (Already Configured)
The system is running the open-source NVIDIA 580 driver with CUDA 13.0 support. All displays are connected via DisplayPort and functioning correctly.

To verify driver status:
```bash
nvidia-smi
xrandr | grep connected
```

### 3. Python Environment Setup
```bash
# Navigate to project directory
cd imagineer

# Create virtual environment
python3 -m venv venv

# Activate environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install PyTorch with CUDA support
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Install project dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -e ".[dev]"
```

### 4. Project Structure
```
imagineer/
├── src/imagineer/          # Core library
│   ├── __init__.py
│   └── utils.py            # Image processing, device detection, VRAM monitoring
├── examples/               # Example scripts
│   ├── basic_inference.py  # Text-to-image generation
│   └── train_lora.py       # LoRA fine-tuning
├── data/                   # Training datasets
│   └── training/           # Image-caption pairs for LoRA
├── models/                 # Hugging Face model cache (~5GB per model)
├── outputs/                # Generated images
├── checkpoints/            # LoRA training checkpoints
├── config.yaml             # Central configuration
└── requirements.txt        # Python dependencies
```

## Next Steps

### For Image Generation
1. Ensure virtual environment is activated: `source venv/bin/activate`
2. Test basic generation:
   ```bash
   python examples/basic_inference.py \
     --prompt "a serene mountain landscape at sunset" \
     --output outputs/test.png \
     --steps 25
   ```
3. First run will download ~5GB Stable Diffusion model from Hugging Face
4. Generated images saved to `outputs/` with optional JSON metadata

### For Model Fine-Tuning
1. Prepare training data in `data/training/`:
   - Add images (.jpg, .png)
   - Create matching `.txt` caption files (same filename)
2. Start LoRA training:
   ```bash
   python examples/train_lora.py \
     --data-dir data/training \
     --output-dir checkpoints/my_lora \
     --steps 1000 \
     --rank 4
   ```
3. Checkpoints saved every N steps to `checkpoints/`

### Configuration
Edit `config.yaml` to customize:
- Model selection (SD 1.5, SD 2.1, SDXL)
- Default generation parameters (steps, guidance scale, size)
- Training hyperparameters (learning rate, LoRA rank/alpha)
- Hardware settings (device, mixed precision, memory optimizations)

## Development Workflow

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

### Git Workflow
```bash
# Current branch
git status

# Create feature branch
git checkout -b feature/your-feature

# Commit changes
git add .
git commit -m "Description of changes"

# Push to remote
git push origin feature/your-feature
```

## Performance Optimization

### Memory Management
- **Attention slicing:** Enabled by default on CUDA (reduces VRAM usage)
- **VAE slicing:** Optional, enable in config for lower VRAM
- **xformers:** Install for faster attention computation
- **Mixed precision:** Uses fp16 on CUDA, fp32 on CPU

### VRAM Monitoring
```python
from imagineer.utils import calculate_vram_usage

# Check GPU memory usage
vram_used, vram_total = calculate_vram_usage()
print(f"VRAM: {vram_used:.2f} GB / {vram_total:.2f} GB")
```

### Batch Generation
Use `load_prompt_list()` utility to process multiple prompts:
```python
from imagineer.utils import load_prompt_list

prompts = load_prompt_list("prompts.txt")
for prompt in prompts:
    # Generate images...
```

## Troubleshooting

### CUDA Out of Memory
- Reduce image dimensions (use 512x512 instead of 1024x1024)
- Lower batch size to 1
- Enable attention slicing and VAE slicing
- Reduce number of inference steps

### Model Download Issues
- Models cached in `models/` directory
- First run requires internet connection
- Use Hugging Face CLI for manual downloads:
  ```bash
  huggingface-cli login
  huggingface-cli download runwayml/stable-diffusion-v1-5
  ```

### Display Issues (Resolved)
System is currently stable with open-source NVIDIA 580 driver. All displays connected via DisplayPort are functioning correctly.

## Additional Resources

- **Stable Diffusion:** https://github.com/Stability-AI/stablediffusion
- **Diffusers Library:** https://huggingface.co/docs/diffusers
- **LoRA Training:** https://huggingface.co/docs/diffusers/training/lora
- **CUDA Toolkit:** https://developer.nvidia.com/cuda-downloads
