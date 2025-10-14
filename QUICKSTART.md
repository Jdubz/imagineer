# Imagineer Quick Start Guide

Complete setup for AI image generation with web interface and SMB sharing.

## ✅ What's Been Set Up

1. **✅ Project Structure** - Complete Imagineer toolkit
2. **✅ Virtual Environment** - Python dependencies installed
3. **✅ Config System** - YAML-based configuration
4. **✅ Command-Line Tool** - Simple `generate.py` script
5. **✅ Drive Setup Scripts** - Ready to format and mount drives
6. **✅ SMB Sharing Scripts** - Ready to configure network shares
7. **✅ Web Server** - Flask API with web UI

## 🚀 Quick Start

### Option 1: Command Line (Simplest)

```bash
# Activate environment
source venv/bin/activate

# Generate an image
python examples/generate.py --prompt "a beautiful sunset over mountains"

# Images saved to outputs/ (or /mnt/speedy/imagineer/outputs if configured)
```

### Option 2: Web Interface (Recommended)

```bash
# Start the web server
bash start_server.sh

# Open browser to:
# http://localhost:5000
```

The web interface lets you:
- Submit prompts from any device on your network
- Queue multiple generation jobs
- Update default settings
- Browse generated images
- View job history

## 📁 Current Setup

Your config is already updated to use the Speedy drive paths:
- **Outputs**: `/mnt/speedy/imagineer/outputs`
- **Models**: `/mnt/speedy/imagineer/models`
- **Checkpoints**: `/mnt/speedy/imagineer/checkpoints`
- **Training Data**: `/mnt/speedy/imagineer/data/training`

## 🌐 Network Access

Once the server is running, access it from:
- **Local**: http://localhost:5000
- **Network**: http://YOUR_IP:5000 (find IP with `hostname -I`)
- **SMB Share**: `\\YOUR_IP\Imagineer\outputs`

## 🎨 Generate Your First Image

### Via Command Line

```bash
source venv/bin/activate
python examples/generate.py --prompt "a dog jumping over a candle" --seed 42
```

### Via Web UI

1. Start server: `bash start_server.sh`
2. Open http://localhost:5000 in browser
3. Enter prompt in the form
4. Click "Generate Image"
5. Watch the queue and wait for completion
6. View in gallery when done

### Via API

```python
import requests

response = requests.post('http://localhost:5000/api/generate', json={
    'prompt': 'a cute cat wearing sunglasses',
    'seed': 42,
    'steps': 30
})

print(response.json())
```

## 📝 Default Settings

Current defaults from `config.yaml`:
- **Model**: Stable Diffusion v1.5
- **Steps**: 30
- **Size**: 512x512
- **Guidance**: 7.5
- **Negative Prompt**: Comprehensive quality filters

You can override any setting per-generation or update defaults via web UI.

## 🔧 Common Commands

```bash
# Generate with specific settings
python examples/generate.py \
  --prompt "your prompt" \
  --steps 50 \
  --width 768 \
  --height 768 \
  --seed 42

# Start web server
bash start_server.sh

# Check GPU status
nvidia-smi

# View outputs
ls -lh /mnt/speedy/imagineer/outputs/

# Access via SMB (from Windows/Mac)
\\YOUR_IP\Imagineer\outputs
```

## 📚 Documentation

- **SERVER_README.md** - Complete API documentation
- **SETUP.md** - Detailed environment setup
- **README.md** - Project overview
- **CLAUDE.md** - AI assistant instructions

## 🛠️ Troubleshooting

### Server won't start
```bash
# Check if port 5000 is in use
sudo lsof -i :5000

# Try a different port
python server/api.py --port 5001
```

### Generation fails
```bash
# Check GPU
nvidia-smi

# Test manually
source venv/bin/activate
python examples/generate.py --prompt "test"
```

### Can't access from network
```bash
# Allow port through firewall
sudo ufw allow 5000

# Find your IP
hostname -I
```

### SMB share not accessible
```bash
# Restart Samba
sudo systemctl restart smbd

# Check status
sudo systemctl status smbd
```

## 🎯 Next Steps

1. **Generate some test images** to verify everything works
2. **Access from phone/tablet** to test network access
3. **Explore different prompts** and settings
4. **Set up auto-start** (see SERVER_README.md for systemd service)
5. **Train a LoRA** on custom dataset (see `examples/train_lora.py`)

## 💡 Tips

- **Use seeds** for reproducible results
- **Start with 25-30 steps** for speed, increase for quality
- **512x512 is fastest**, larger sizes need more VRAM
- **Queue multiple prompts** in web UI for batch generation
- **Access SMB share** to view images from any device
- **Check metadata JSON** files for generation parameters

## 🔐 Security Note

The server currently has no authentication. For production use:
- Add authentication to the API
- Use HTTPS with SSL certificates
- Restrict firewall to specific IPs
- Use a reverse proxy (Nginx)

See SERVER_README.md for production deployment options.

---

**Need help?** Check the documentation files or test commands above.

**Ready to generate!** 🎨✨
