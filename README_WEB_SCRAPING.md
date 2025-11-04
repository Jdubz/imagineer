# Web Scraping - Quick Reference

## Status: ✅ Working (Threading-Based)

The web scraping feature is now fully functional using a simple threading queue.

## How to Use

### Via Web UI
1. Go to https://imagineer-generator.web.app
2. Click "Scraping" tab (admin only)
3. Click "Start New Scrape"
4. Enter URL and settings
5. Click "Start Scrape"

### Via API
```bash
curl -X POST http://localhost:10050/api/scraping/start \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "depth": 2,
    "max_images": 10
  }'
```

## Architecture

```
Web UI → Flask API → Python Queue → Background Thread → Training-Data Scraper
```

**One service. No external dependencies.**

## Deployment

```bash
# Apply changes
sudo systemctl restart imagineer-api

# Verify
sudo systemctl status imagineer-api
```

## Testing

```bash
# Run automated tests
./scripts/test_scraping.sh

# Check queue status
curl http://localhost:10050/api/scraping/queue

# View logs
sudo journalctl -u imagineer-api -f
```

## Troubleshooting

**Jobs stuck in "pending":**
```bash
sudo systemctl restart imagineer-api
```

**Jobs fail immediately:**
```bash
# Check Anthropic API key
cat /home/jdubz/Development/training-data/.env | grep ANTHROPIC
```

## Documentation

- **Technical Details**: `docs/deployment/WEB_SCRAPING_SIMPLE_FIX.md`
- **Implementation**: `server/routes/scraping_simple.py`
- **Changes Log**: `SCRAPING_FIXES_APPLIED.md`
- **Summary**: `WEB_SCRAPING_FIX_SUMMARY.md`

## Implementation Details

- **Pattern**: Same as image generation (`server/routes/generation.py`)
- **Queue**: `queue.Queue[int]` (Python standard library)
- **Worker**: Single daemon thread
- **Processing**: Sequential (one job at a time)
- **Progress**: Real-time updates via database

## Files

```
server/
  routes/
    scraping_simple.py    # Threading-based routes (active)
    scraping.py           # Old implementation (not loaded)
  tasks/
    scraping.py           # Core scraping logic (shared)
  api.py                  # Imports scraping_simple
```

## Requirements

- ✅ Flask API (already running)
- ✅ training-data repo (`/home/jdubz/Development/training-data`)
- ✅ Anthropic API key (in training-data/.env)

**No additional services required!**
