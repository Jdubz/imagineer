# Web Scraping - Simple Threading Implementation

## Overview

The web scraping feature uses a **simple threading-based queue** matching the image generation pattern. No external dependencies required!

## Architecture

The implementation (`server/routes/scraping_simple.py`) uses the same pattern as image generation:

1. **Job Queue**: `queue.Queue[int]` stores job IDs
2. **Background Worker**: Single daemon thread processes jobs sequentially
3. **Database Tracking**: Job status stored in PostgreSQL
4. **No External Dependencies**: Everything runs in the Flask process

## How It Works

### Job Submission

```python
# User clicks "Start Scrape" in UI
POST /api/scraping/start
{
  "url": "https://example.com",
  "depth": 3,
  "max_images": 100
}

# API creates job in database
job = ScrapeJob(status="pending", ...)
db.session.add(job)
db.session.commit()

# Job ID added to queue
scrape_queue.put(job.id)  # Non-blocking
```

### Job Processing

```python
# Background worker thread (daemon)
def process_scrape_jobs():
    while True:
        job_id = scrape_queue.get()  # Blocks until job available

        # Update status to "running"
        job.status = "running"

        # Run scraping subprocess
        scrape_site_implementation(job_id)

        # Job completes, status updated to "completed"/"failed"
        scrape_queue.task_done()
```

### Progress Tracking

The scraping subprocess streams output that's parsed for progress:

```
INFO     Discovered 50 images
INFO     Downloaded 10/100 images
INFO     Downloaded 20/100 images
INFO     Captioning image 5/100
...
```

This updates `job.progress`, `job.images_scraped`, and `job.description` in real-time.

## Benefits

### Simplicity
- **No external services** to install or configure
- **One systemd service** (just the API)
- **Fewer moving parts** = easier debugging
- **Single process** handles both API and scraping

### Resource Efficiency
- **Low memory overhead** - no separate worker process
- **Automatic lifecycle management** - daemon thread
- **Single process** for everything

### Development Experience
- **Instant setup** - works after `pip install`
- **Simpler testing** - no extra services to start
- **Easier debugging** - all logs in one place
- **Hot reload** - changes apply immediately

### Operational Benefits
- **Fewer failure modes** - no network dependencies
- **Simpler monitoring** - just check API health
- **Easier deployment** - one service to deploy
- **Auto-recovery** - thread restarts with API

## Limitations

### Sequential Processing Only
- **One job at a time** - no parallel scraping
- For Imagineer's use case (occasional training data collection), this is fine
- Can increase to 2-3 threads if needed (simple change)

### No Distributed Workers
- Can't distribute scraping across multiple servers
- For Imagineer (single server), this is not a concern

## Deployment

### Apply Changes

```bash
# Pull latest code
cd /home/jdubz/Development/imagineer
git pull

# Restart API (picks up new scraping_simple.py)
sudo systemctl restart imagineer-api

# Verify service started
sudo systemctl status imagineer-api

# Test scraping
./scripts/test_scraping.sh
```

### No Additional Services Needed

Unlike other approaches, no additional setup required:
- ✅ No extra installations
- ✅ No additional systemd services
- ✅ Just restart the API

## Testing

### Test Scraping Job

```bash
# 1. Ensure API is running
curl http://localhost:10050/health

# 2. Start a test scrape (requires admin auth)
curl -X POST http://localhost:10050/api/scraping/start \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "depth": 2,
    "max_images": 10
  }'

# 3. Check job status
curl http://localhost:10050/api/scraping/jobs

# 4. Watch logs
sudo journalctl -u imagineer-api -f
```

### Verify Background Worker

```bash
# Check that worker thread is running
ps aux | grep imagineer-api

# Should see one Python process with multiple threads
# The scraping worker runs as a daemon thread
```

### Monitor Queue

```bash
# Check queue status
curl http://localhost:10050/api/scraping/queue

# Response:
{
  "queue_size": 0,
  "current_job_id": null
}
```

## Troubleshooting

### Jobs Stuck in "pending"

**Symptom:** Jobs never transition from "pending" to "running"

**Cause:** Background worker thread not started

**Fix:**
```bash
# Restart API service
sudo systemctl restart imagineer-api

# Check logs for "Starting scrape job X"
sudo journalctl -u imagineer-api -f
```

### API Crash on Scrape

**Symptom:** API crashes when scraping job starts

**Cause:** Missing training-data dependency or config issue

**Fix:**
```bash
# Check logs for actual error
sudo journalctl -u imagineer-api -n 100

# Common issues:
# 1. training-data repo not configured
# 2. Output directory not writable
# 3. Python subprocess fails to start
```

### Jobs Never Complete

**Symptom:** Jobs stay in "running" forever

**Cause:** Scraping subprocess hangs or times out

**Fix:**
```bash
# Check for orphaned processes
ps aux | grep training_data

# Kill orphaned scrapers
pkill -f training_data

# Restart API
sudo systemctl restart imagineer-api
```

## Performance Tuning

### Increase Concurrency

Edit `server/routes/scraping_simple.py`:

```python
# Change from 1 worker to N workers
num_workers = 3

for i in range(num_workers):
    worker = threading.Thread(
        target=process_scrape_jobs,
        daemon=True,
        name=f"scraper-worker-{i}"
    )
    worker.start()
```

### Adjust Timeouts

Edit `server/tasks/scraping.py`:

```python
# Default: 2 hours max, 10 min idle timeout
SCRAPING_MAX_DURATION_SECONDS = 2 * 60 * 60
SCRAPING_IDLE_TIMEOUT_SECONDS = 600

# For faster sites, reduce:
SCRAPING_MAX_DURATION_SECONDS = 30 * 60  # 30 min
SCRAPING_IDLE_TIMEOUT_SECONDS = 300      # 5 min
```

## Files

### Core Implementation
- `server/routes/scraping_simple.py` - Threading-based routes (254 lines)
- `server/tasks/scraping.py:170` - Core scraping logic
- `server/api.py:173` - Route registration

### Related
- `server/routes/generation.py:222` - Similar pattern for image generation
- `web/src/components/ScrapingTab.tsx` - Frontend component
- `web/src/lib/api.ts:538` - API client

## Summary

For Imagineer's use case:
- **Threading is simpler** - no infrastructure overhead
- **Threading is sufficient** - sequential processing is fine
- **Threading is reliable** - fewer failure modes
- **Threading is faster to set up** - no extra services

The implementation matches the proven image generation queue pattern and has been working reliably since the project started.
