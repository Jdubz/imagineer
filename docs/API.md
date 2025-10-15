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

**Request:**
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

**Response: 201 Created**
```json
{
  "id": 1,
  "status": "queued",
  "submitted_at": "2025-10-13T14:32:15.123456",
  "queue_position": 1,
  "prompt": "a beautiful landscape"
}
```

**Headers:**
- `Location: /api/jobs/1` - URL to poll job status

**Required:**
- `prompt` - Text prompt (1-2000 chars, non-empty)

**Optional:**
- `negative_prompt`, `seed`, `steps`, `width`, `height`, `guidance_scale`

**Validation:**
- Prompt: 1-2000 characters (trimmed)
- Seed: 0-2147483647
- Steps: 1-150
- Width/Height: 64-2048, divisible by 8
- Guidance scale: 0-30

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
Get specific job details including queue position

**Response for Queued Job:**
```json
{
  "id": 1,
  "status": "queued",
  "prompt": "a beautiful landscape",
  "seed": 42,
  "steps": 30,
  "width": 512,
  "height": 512,
  "guidance_scale": 7.5,
  "negative_prompt": "low quality",
  "submitted_at": "2025-10-13T14:32:15.123456",
  "queue_position": 2,
  "estimated_time_remaining": null
}
```

**Response for Running Job:**
```json
{
  "id": 1,
  "status": "running",
  "queue_position": 0,
  "started_at": "2025-10-13T14:35:00.000000",
  ...
}
```

**Response for Completed Job:**
```json
{
  "id": 1,
  "status": "completed",
  "completed_at": "2025-10-13T14:39:30.000000",
  "duration_seconds": 270.5,
  "output_path": "outputs/20251013_143930_a_beautiful_landscape.png",
  ...
}
```

### DELETE `/api/jobs/<id>`
Cancel a queued job

**Response: 200 OK**
```json
{
  "message": "Job cancelled successfully"
}
```

**Errors:**
- `404` - Job not found
- `409` - Cannot cancel currently running job
- `410` - Cannot cancel completed job

**Note:** Only jobs with status `queued` can be cancelled

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
import time

# Submit generation job
response = requests.post('http://localhost:5000/api/generate', json={
    'prompt': 'a dog jumping over a candle',
    'seed': 42,
    'steps': 30
})

job = response.json()
print(f"Job {job['id']} submitted, position: {job['queue_position']}")

# Poll for completion
job_id = job['id']
while True:
    status_response = requests.get(f'http://localhost:5000/api/jobs/{job_id}')
    job_status = status_response.json()

    if job_status['status'] == 'completed':
        print(f"Job completed! Output: {job_status['output_path']}")
        break
    elif job_status['status'] == 'failed':
        print(f"Job failed: {job_status['error']}")
        break
    elif job_status['status'] == 'cancelled':
        print("Job was cancelled")
        break
    else:
        print(f"Status: {job_status['status']}, position: {job_status.get('queue_position', 'N/A')}")
        time.sleep(2)
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
console.log(`Job ${job.id} submitted, position: ${job.queue_position}`);

// Poll for completion
const pollJob = async (jobId) => {
  const statusResponse = await fetch(`http://localhost:5000/api/jobs/${jobId}`);
  const jobStatus = await statusResponse.json();

  if (jobStatus.status === 'completed') {
    console.log(`Image ready: ${jobStatus.output_path}`);
  } else if (jobStatus.status === 'failed') {
    console.error(`Job failed: ${jobStatus.error}`);
  } else if (jobStatus.status === 'cancelled') {
    console.log('Job was cancelled');
  } else {
    console.log(`Status: ${jobStatus.status}, position: ${jobStatus.queue_position || 'N/A'}`);
    setTimeout(() => pollJob(jobId), 2000);
  }
};

pollJob(job.id);
```

## Job Statuses

- `queued` - Job is waiting in queue
- `running` - Job is currently being processed
- `completed` - Job finished successfully
- `failed` - Job encountered an error
- `cancelled` - Job was cancelled by user

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