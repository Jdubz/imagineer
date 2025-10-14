# ✨ Imagineer

**AI Image Generation Toolkit** with Web Interface

Imagineer is a complete AI image generation system built on Stable Diffusion and Hugging Face Diffusers. It features a modern web UI, REST API, and command-line tools for generating high-quality images from text prompts.

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![PyTorch](https://img.shields.io/badge/pytorch-2.0%2B-orange)
![React](https://img.shields.io/badge/react-18.3-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## ✨ Features

### Core Functionality
- 🎨 **Text-to-Image Generation** - Create images from descriptive text prompts
- 🖼️ **Web Interface** - Modern React-based UI with real-time generation
- 🔧 **REST API** - Flask-based API for programmatic access
- 📊 **Job Queue System** - Background processing with status tracking
- 💾 **Metadata Preservation** - Save generation parameters with each image

### Advanced Features
- 🎛️ **Interactive Controls** - Adjust steps, guidance scale, and seed values
- 🔄 **LoRA Fine-Tuning** - Train custom models on your datasets
- ⚡ **Memory Optimizations** - Efficient inference for consumer GPUs
- 📁 **Batch Generation** - Process multiple prompts automatically
- 🌐 **Network Access** - Optional SMB shares for remote access

### Supported Models
- Stable Diffusion 1.5 (default)
- Stable Diffusion 2.1
- Stable Diffusion XL
- Custom fine-tuned models

## 🚀 Quick Start

### Prerequisites
- Python 3.8+ (3.12+ recommended)
- NVIDIA GPU with 6GB+ VRAM (8GB+ recommended)
- CUDA 11.8+ and NVIDIA drivers
- Node.js 18+ (for web interface)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/imagineer.git
cd imagineer
```

2. **Install Python dependencies**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

3. **Install frontend dependencies**
```bash
cd web
npm install
cd ..
```

4. **Build the frontend**
```bash
make build
```

### Usage

**Start the full application (API + Web UI):**
```bash
make dev
```

Then open your browser to: `http://localhost:10051`

**Or use individual commands:**
```bash
make api      # Start API server only (port 10050)
make web-dev  # Start frontend dev server only (port 10051)
```

**Command-line generation:**
```bash
source venv/bin/activate
python examples/generate.py --prompt "a beautiful sunset over mountains"
```

## 📖 Documentation

- **[Setup Guide](docs/SETUP.md)** - Detailed installation and configuration
- **[API Reference](docs/API.md)** - REST API endpoints and usage
- **[Makefile Commands](docs/MAKEFILE_REFERENCE.md)** - All available make commands
- **[Contributing](docs/CONTRIBUTING.md)** - Development guidelines

## 🎨 Web Interface Features

- **Prompt Input** - Enter descriptive text for image generation
- **Advanced Controls**:
  - **Steps** (10-75): Number of denoising iterations
  - **Guidance Scale** (1-20): How closely to follow the prompt
  - **Seed**: Reproducible results with fixed seeds
- **Image Gallery** - View all generated images with metadata
- **Real-time Status** - Live updates during generation
- **Image Details** - Click any image to view full resolution and parameters

## 🛠️ Configuration

Edit `config.yaml` to customize:

```yaml
generation:
  width: 512
  height: 512
  steps: 30
  guidance_scale: 7.5
  negative_prompt: "blurry, low quality..."  # Exhaustive quality filters

model:
  default: "runwayml/stable-diffusion-v1-5"
  cache_dir: "models/"

output:
  directory: "outputs/"
  format: "png"
  save_metadata: true
```

## 📁 Project Structure

```
imagineer/
├── server/              # Flask REST API
│   └── api.py          # Main API server with job queue
├── web/                # React frontend (source)
│   ├── src/
│   │   ├── components/ # React components
│   │   └── styles/     # CSS styling
│   └── package.json
├── public/             # Built frontend (generated)
├── src/imagineer/      # Core Python library
│   ├── __init__.py
│   └── utils.py        # Image processing utilities
├── examples/           # Example scripts
│   ├── generate.py     # Config-based generation
│   ├── basic_inference.py
│   └── train_lora.py   # LoRA fine-tuning
├── scripts/            # Utility scripts
│   ├── setup/          # System setup scripts
│   └── start_*.sh      # Service launchers
├── docs/               # Documentation
├── data/               # Training data
├── models/             # Model cache (~5GB on first run)
├── outputs/            # Generated images
├── checkpoints/        # Training checkpoints
├── config.yaml         # Main configuration
├── Makefile           # Task automation
└── requirements.txt   # Python dependencies
```

## 🔧 API Endpoints

```bash
GET  /api/config              # Get current configuration
PUT  /api/config              # Update configuration
POST /api/generate            # Submit generation job
GET  /api/jobs                # List all jobs
GET  /api/jobs/{id}           # Get job status
GET  /api/outputs             # List generated images
GET  /api/outputs/{filename}  # Serve image file
GET  /api/health              # Health check
```

## 💻 Hardware Requirements

### Minimum
- **RAM:** 8GB system memory
- **GPU:** 4GB VRAM (GTX 1650+)
- **Storage:** 20GB free space
- **OS:** Linux, Windows, or macOS

### Recommended
- **RAM:** 16GB+ system memory
- **GPU:** 8GB+ VRAM (RTX 3060, RTX 3080, RTX 4060+)
- **Storage:** 50GB+ for models and outputs
- **OS:** Linux with NVIDIA drivers

### Tested Configuration
- **GPU:** NVIDIA GeForce RTX 3080 (10GB VRAM)
- **Driver:** NVIDIA 580.65.06 (open-source)
- **CUDA:** 12.1+
- **OS:** Ubuntu 24.04 LTS

## 🎓 Advanced Usage

### LoRA Fine-Tuning

1. Prepare training data in `data/training/`:
   - Add images (.jpg, .png)
   - Create matching `.txt` files with captions

2. Train the model:
```bash
source venv/bin/activate
python examples/train_lora.py \
  --data-dir data/training \
  --output-dir checkpoints/my_lora \
  --steps 1000 \
  --rank 4
```

### Batch Generation

Create a text file with prompts (one per line) and use:
```bash
python scripts/batch_generate.py --prompts prompts.txt
```

### Network Access

The web UI is accessible across your network at `http://YOUR_IP:10051` where YOUR_IP is your machine's local network IP address.

## 🐛 Troubleshooting

**CUDA Out of Memory:**
- Reduce image dimensions in `config.yaml`
- Lower batch size
- Enable more memory optimizations

**Model Download Fails:**
- Check internet connection
- Verify Hugging Face access
- Manually download models to `models/` directory

**Web UI Won't Start:**
- Verify ports 10050/10051 are available
- Check Node.js is installed
- Run `make kill` to stop conflicting processes
- Try `make clean && make build`

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Hugging Face Diffusers](https://github.com/huggingface/diffusers) - Core diffusion library
- [Stable Diffusion](https://stability.ai/) - Base model
- [PyTorch](https://pytorch.org/) - Deep learning framework
- [React](https://react.dev/) - Frontend framework
- [Flask](https://flask.palletsprojects.com/) - API framework

## 📞 Support

- 📖 [Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/yourusername/imagineer/issues)
- 💬 [Discussions](https://github.com/yourusername/imagineer/discussions)

---

Made with ❤️ by the Imagineer community
