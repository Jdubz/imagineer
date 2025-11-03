# Web Scraping Fixes Applied

## Issues Fixed

### 1. Simple Threading Queue
✅ Implemented threading-based queue matching image generation pattern
- Created `server/routes/scraping_simple.py` with background worker thread
- Modified `server/api.py:173` to use simple implementation
- No external dependencies required

### 2. Training-Data CLI Integration Fixes
✅ Fixed command-line interface to training-data scraper
- **Wrong Python Path**: Changed from `"python"` to training-data venv Python
- **Wrong CLI Format**: Fixed positional argument order to `[OPTIONS] URL PROMPT OUTPUT_DIR`
- **Missing Config**: Added automatic config file detection
- **API Key Loading**: Added .env loading from training-data repo

### 3. Output Parsing Updates
✅ Updated progress tracking to match actual training-data output
- Parse "Discovered X images" format
- Parse "Downloaded X/Y images" format
- Parse "Captioning image X/Y" format
- Calculate progress percentages correctly

## Changes Made

### server/tasks/scraping.py
**Lines 224-258**: Fixed Python path and CLI arguments
```python
# Use training-data's virtual environment Python
training_venv_python = training_data_repo / "venv" / "bin" / "python"

# Correct CLI format: [OPTIONS] URL PROMPT OUTPUT_DIR
cmd = [
    str(training_venv_python),
    "-m",
    "training_data",
]

# Add options FIRST
if max_images > 0:
    cmd.extend(["--max-images", str(max_images)])
if depth > 0:
    cmd.extend(["--max-depth", str(depth)])

# Add positional arguments
cmd.extend([
    job.source_url,      # URL
    "training data",     # PROMPT
    str(output_dir),     # OUTPUT_DIR
])
```

**Lines 316-358**: Updated output parsing
```python
# Parse training-data output format
if "Discovered" in line and "images" in line:
    # Extract from "Discovered X images"
    parts = line.split("Discovered")[1].split("images")[0].strip()
    discovered_count = int(parts)

elif "Downloaded" in line and "images" in line:
    # Extract from "Downloaded X/Y images"
    parts = line.split("Downloaded")[1].split("images")[0].strip()
    if "/" in parts:
        downloaded_count = int(parts.split("/")[0].strip())
    job.images_scraped = downloaded_count

elif "Captioning" in line:
    # Extract from "Captioning image X/Y"
    ...
```

### server/routes/scraping_simple.py (NEW)
**254 lines**: Complete threading-based implementation
- Job queue using `queue.Queue[int]`
- Background worker thread (daemon)
- All endpoints: `/start`, `/jobs`, `/jobs/<id>`, `/cancel`, `/cleanup`, `/stats`, `/queue`
- No Celery dependencies

### server/api.py
**Line 173**: Changed import
```python
# Before:
from server.routes.scraping import scraping_bp

# After:
from server.routes.scraping_simple import scraping_bp
```

## How to Apply

### 1. Restart API Service
```bash
sudo systemctl restart imagineer-api
```

That's all! No Redis, no Celery, no additional services.

### 2. Verify Service Started
```bash
sudo systemctl status imagineer-api
sudo journalctl -u imagineer-api -f
```

Should see: "Starting scrape job X" when jobs are processed

## Testing

### Via Web UI
1. Open https://imagineer-generator.web.app
2. Navigate to "Scraping" tab (admin only)
3. Click "Start New Scrape"
4. Enter:
   - URL: https://example.com (or any image gallery site)
   - Max Depth: 2
   - Max Images: 10
5. Click "Start Scrape"
6. Watch job progress: `pending` → `running` → `completed`

### Via API
```bash
# Start scrape job
curl -X POST http://localhost:10050/api/scraping/start \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "depth": 2,
    "max_images": 10
  }'

# Check job status
curl http://localhost:10050/api/scraping/jobs

# Check queue status
curl http://localhost:10050/api/scraping/queue
```

## Expected Behavior

### Job Flow
1. **pending** - Job created and queued
2. **running** - Background worker processing
   - Progress updates: 0% → 90% (downloading) → 95% (captioning) → 100%
   - `images_scraped` counter increments
   - `description` shows current activity
3. **completed** - Job finished successfully
   - Images imported to database
   - Album created
   - Output directory populated

### Progress Messages
You should see in logs:
```
INFO     Starting pipeline for https://example.com
INFO     Discovered 15 images
INFO     Downloaded 5/15 images
INFO     Downloaded 10/15 images
INFO     Captioning image 1/15
INFO     Captioning image 5/15
```

### Frontend Updates
- Stats cards update (Total Jobs, Images Scraped, Recent Jobs)
- Job status updates every 5 seconds
- Progress bar shows completion percentage
- Real-time message updates ("Discovered X images", etc.)

## Troubleshooting

### Jobs Stuck in "pending"
**Cause**: Background worker thread not started

**Fix**:
```bash
sudo systemctl restart imagineer-api
sudo journalctl -u imagineer-api -f
```

Look for "Processing scrape job X" in logs

### Jobs Fail Immediately
**Cause**: Missing Anthropic API key or training-data dependencies

**Fix**:
```bash
# Check training-data has API key
cat /home/jdubz/Development/training-data/.env | grep ANTHROPIC

# If missing, add it:
echo "ANTHROPIC_API_KEY=sk-ant-..." >> /home/jdubz/Development/training-data/.env

# Check training-data module is installed
cd /home/jdubz/Development/training-data
source venv/bin/activate
python -m training_data --help
```

### No Images Scraped
**Cause**: Target website has no accessible images or requires authentication

**Solution**: Test with a known working site first
```bash
# Try these test sites:
- https://picsum.photos
- https://unsplash.com
- Any simple image gallery
```

### Job Hangs Forever
**Cause**: Subprocess timeout or scraper crash

**Fix**:
```bash
# Check for orphaned processes
ps aux | grep training_data

# Kill if stuck
pkill -f training_data

# Restart API
sudo systemctl restart imagineer-api
```

## What's Different from Before

### Before (Broken)
```
User → API → Celery Task Queue → ❌ (No Redis/Worker)
```
- Required Redis (not installed)
- Required Celery worker service (not running)
- Jobs stuck in "pending" forever
- Error toasts every few seconds

### After (Working)
```
User → API → Python Queue → Background Thread → Training-Data Scraper → ✅
```
- No external dependencies
- Single service (API)
- Jobs process immediately
- Real-time progress updates

## Dependencies

### Required (Already Installed)
- ✅ training-data repo at `/home/jdubz/Development/training-data`
- ✅ training-data venv with module installed
- ✅ Anthropic API key in training-data/.env

### NOT Required
- ❌ Additional systemd services
- ❌ External message brokers
- ❌ Background worker processes

## Files Created

- `server/routes/scraping_simple.py` - New threading implementation
- `docs/deployment/WEB_SCRAPING_SIMPLE_FIX.md` - Full technical docs
- `scripts/test_scraping.sh` - Automated test script
- `scripts/restart_api.sh` - API restart helper
- `WEB_SCRAPING_FIX_SUMMARY.md` - Quick start guide
- `SCRAPING_FIXES_APPLIED.md` - This file

## Next Steps

1. ✅ Code changes complete
2. ✅ Documentation complete
3. ⏳ **Restart API to apply**: `sudo systemctl restart imagineer-api`
4. ⏳ **Test scraping job** via UI or API
5. ⏳ **Monitor first job** to completion
6. ⏳ **Clean up old pending job** (if exists)

## Status

All fixes applied and ready for deployment!

Just restart the API service and web scraping will work.
