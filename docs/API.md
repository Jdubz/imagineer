# Imagineer Web Server

A Flask-based REST API server with web UI for managing AI image generation.

## Features

- **Web UI** - Submit prompts and manage settings from any browser
- **REST API** - Programmatic access to generation
- **Job Queue** - Queue multiple prompts for batch generation
- **Config Management** - Update default settings via web interface
- **Gallery** - Browse generated images with metadata
- **SMB Integration** - Generated images accessible via network share

## Quick Start

### 1. Start the Server

```bash
bash start_server.sh
```

The server will start on port 5000 and be accessible from:
- **Local**: http://localhost:5000
- **Network**: http://YOUR_IP:5000

### 2. Access from Other Devices

The server is accessible from any device on your network:
- **Desktop/Laptop**: Open browser to `http://YOUR_IP:5000`
- **Phone/Tablet**: Open browser to `http://YOUR_IP:5000`
- **SMB Share**: `\\YOUR_IP\Imagineer\outputs`

## API Endpoints

### GET `/api/config`
Get current configuration

### PUT `/api/config`
Update full configuration

### PUT `/api/config/generation`
Update just generation settings

```json
{
  "steps": 30,
  "guidance_scale": 7.5,
  "negative_prompt": "blurry, low quality..."
}
```

### POST `/api/generate`
Submit image generation job

```json
{
  "prompt": "a beautiful landscape",
  "seed": 42,
  "steps": 30,
  "width": 512,
  "height": 512,
  "guidance_scale": 7.5,
  "negative_prompt": "low quality"
}
```

Response:
```json
{
  "success": true,
  "job": {
    "id": 1,
    "prompt": "a beautiful landscape",
    "status": "queued",
    "submitted_at": "2025-10-13T..."
  },
  "queue_position": 1
}
```

### GET `/api/jobs`
Get current queue and job history

Response:
```json
{
  "current": {...},
  "queued": [...],
  "history": [...]
}
```

### GET `/api/jobs/<id>`
Get specific job details

### GET `/api/outputs`
List all generated images with metadata

### GET `/api/outputs/<filename>`
Serve a generated image file

### GET `/api/health`
Health check

Response:
```json
{
  "status": "ok",
  "queue_size": 0,
  "current_job": false,
  "total_completed": 5
}
```

## Using the API

### Python Example

```python
import requests

# Submit generation job
response = requests.post('http://localhost:5000/api/generate', json={
    'prompt': 'a dog jumping over a candle',
    'seed': 42,
    'steps': 30
})

job = response.json()
print(f"Job {job['job']['id']} submitted!")

# Check job status
job_id = job['job']['id']
status = requests.get(f'http://localhost:5000/api/jobs/{job_id}').json()
print(f"Status: {status['status']}")
```

### cURL Example

```bash
# Submit job
curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"a beautiful sunset","steps":30}'

# Check queue
curl http://localhost:5000/api/jobs

# Get config
curl http://localhost:5000/api/config
```

### JavaScript/Node.js Example

```javascript
// Submit generation job
const response = await fetch('http://localhost:5000/api/generate', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    prompt: 'a cute cat',
    seed: 42,
    steps: 30
  })
});

const job = await response.json();
console.log(`Job ${job.job.id} submitted!`);
```

## Job Statuses

- `queued` - Job is waiting in queue
- `running` - Job is currently being processed
- `completed` - Job finished successfully
- `failed` - Job encountered an error

## Configuration

Server reads from `config.yaml` for:
- Default generation parameters
- Output directory paths
- Model cache location

Update via web UI or directly edit `config.yaml` (requires server restart).

## Network Access

To access from other devices on your network:

1. **Find your IP**: `hostname -I`
2. **Check firewall**: Allow port 5000
   ```bash
   sudo ufw allow 5000
   ```
3. **Access**: `http://YOUR_IP:5000`

## Troubleshooting

**Server won't start:**
```bash
# Check if port 5000 is in use
sudo lsof -i :5000

# Kill process using port 5000
sudo kill -9 <PID>
```

**Can't access from network:**
```bash
# Allow port through firewall
sudo ufw allow 5000

# Check server is listening on 0.0.0.0
netstat -tuln | grep 5000
```

**Jobs failing:**
```bash
# Check server logs
# Look for Python errors in terminal

# Test generation manually
source venv/bin/activate
python examples/generate.py --prompt "test"
```

## Development

The server uses:
- **Flask** - Web framework
- **Flask-CORS** - Cross-origin resource sharing
- **Threading** - Background job processing
- **Queue** - Job queue management

To modify:
- **API**: Edit `server/api.py`
- **Web UI**: Edit `server/static/index.html`
- **Config**: Edit `config.yaml`

## Production Deployment

For production use, consider:

1. **Use a production WSGI server** (Gunicorn, uWSGI)
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 server.api:app
   ```

2. **Set up reverse proxy** (Nginx, Apache)
3. **Use HTTPS** for secure access
4. **Set up authentication** for API access
5. **Use systemd** for auto-start on boot

## systemd Service (Auto-start)

Create `/etc/systemd/system/imagineer.service`:

```ini
[Unit]
Description=Imagineer API Server
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/path/to/imagineer
ExecStart=/path/to/imagineer/venv/bin/python server/api.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable imagineer
sudo systemctl start imagineer
sudo systemctl status imagineer
```