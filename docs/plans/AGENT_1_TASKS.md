# Agent 1 Task List - Training & Scraping Systems

**Agent:** Primary (working in main worktree)
**Focus Area:** Training pipeline and web scraping backend
**Estimated Time:** 6-8 hours
**Files to Modify:** `server/routes/training.py`, `server/tasks/training.py`, `server/tasks/scraping.py`, `config.yaml`

---

## Task 1: Fix Training Album Persistence 🔴 CRITICAL

**Priority:** P0 (Blocking)
**Estimated Time:** 1.5 hours
**Files:** `server/routes/training.py` (or `server/api.py` training creation endpoint)

### Problem
Training jobs fail with "No albums specified" because album_ids are not being persisted to the TrainingRun database record.

### Investigation Steps

1. **Find the training run creation endpoint:**
```bash
grep -n "POST.*training" server/api.py server/routes/training.py
```

2. **Check how TrainingRun is created:**
```bash
grep -A 20 "TrainingRun(" server/routes/training.py server/api.py
```

3. **Verify album_ids field in database model:**
```bash
grep -A 5 "class TrainingRun" server/database.py
```

### Expected Root Cause
The endpoint likely creates TrainingRun without setting the `album_ids` field, or it's being set but not committed to the database.

### Solution Steps

1. **Locate the POST endpoint for training creation** (likely in `server/routes/training.py` or `server/api.py`)

2. **Ensure album_ids are extracted from request and stored:**
```python
# In the POST /api/training/runs endpoint
data = request.json
album_ids = data.get('album_ids', [])  # Should be a list of ints

# Create training run with album_ids
training_run = TrainingRun(
    name=data['name'],
    album_ids=album_ids,  # ← Ensure this is set
    config=data.get('config', {}),
    status='pending',
    created_by=current_user.email if current_user else None
)

db.session.add(training_run)
db.session.commit()
```

3. **Verify the task reads album_ids correctly:**
```python
# In server/tasks/training.py - train_lora_task function
training_run = db.session.get(TrainingRun, training_run_id)
album_ids = training_run.album_ids  # Should be a list

if not album_ids:
    raise ValueError("No albums specified for training")
```

### Testing Steps

1. **Create a test training run via API:**
```bash
curl -X POST http://localhost:10050/api/training/runs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test_run",
    "album_ids": [1, 2],
    "config": {
      "steps": 100,
      "learning_rate": 0.0001
    }
  }'
```

2. **Verify database record:**
```bash
sqlite3 instance/imagineer.db "SELECT id, name, album_ids FROM training_runs ORDER BY id DESC LIMIT 1;"
```

3. **Check task execution:**
```bash
# Monitor Celery logs for task start
tail -f logs/imagineer.log | grep "train_lora_task"
```

### Acceptance Criteria
- ✅ Training runs created via API have album_ids persisted
- ✅ train_lora_task can read album_ids from TrainingRun
- ✅ Task does not fail with "No albums specified"
- ✅ Training job progresses to image collection phase

---

## Task 2: Initialize SCRAPED_OUTPUT_PATH 🔴 CRITICAL

**Priority:** P0 (Blocking)
**Estimated Time:** 1 hour
**Files:** `server/tasks/scraping.py`, `config.yaml`, possibly `server/api.py`

### Problem
`SCRAPED_OUTPUT_PATH` is `None` at runtime (line 22 of `server/tasks/scraping.py`), causing scraping jobs to fail.

### Investigation Steps

1. **Check current implementation:**
```bash
grep -n "SCRAPED_OUTPUT_PATH" server/tasks/scraping.py
```

2. **Check if config.yaml has the path:**
```bash
grep -A 5 "scraped\|scraping" config.yaml
```

### Solution Steps

1. **Add scraped output path to config.yaml:**
```yaml
# In config.yaml, add under outputs section:
outputs:
  base_dir: /mnt/speedy/imagineer/outputs
  scraped_dir: /mnt/speedy/imagineer/outputs/scraped  # ← Add this
```

2. **Load configuration in scraping task module:**
```python
# At top of server/tasks/scraping.py, after imports:
import yaml
from pathlib import Path

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

SCRAPED_OUTPUT_PATH = Path(config['outputs'].get('scraped_dir', '/mnt/speedy/imagineer/outputs/scraped'))

# Ensure directory exists
SCRAPED_OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
```

3. **Alternative: Read from environment variable:**
```python
# If you prefer environment-based config
SCRAPED_OUTPUT_PATH = Path(os.environ.get(
    'SCRAPED_OUTPUT_PATH',
    '/mnt/speedy/imagineer/outputs/scraped'
))
SCRAPED_OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
```

### Testing Steps

1. **Verify path is initialized:**
```bash
# Start Python REPL and import
python3 -c "from server.tasks.scraping import SCRAPED_OUTPUT_PATH; print(SCRAPED_OUTPUT_PATH)"
```

2. **Check directory creation:**
```bash
ls -la /mnt/speedy/imagineer/outputs/ | grep scraped
```

3. **Create test scrape job:**
```bash
curl -X POST http://localhost:10050/api/scraping/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "album_name": "test_scrape",
    "depth": 1
  }'
```

4. **Monitor job execution:**
```bash
tail -f logs/imagineer.log | grep "scrape_site_task"
```

### Acceptance Criteria
- ✅ SCRAPED_OUTPUT_PATH is not None
- ✅ Directory exists and is writable
- ✅ Scrape jobs can create subdirectories
- ✅ Images are downloaded to correct location

---

## Task 3: Implement Training Logs Streaming 🟡 HIGH

**Priority:** P1 (Important)
**Estimated Time:** 2.5 hours
**Files:** `server/routes/training.py`, `server/tasks/training.py`

### Problem
Training logs endpoint returns placeholder text. Need to capture subprocess output and serve it via API.

### Solution Steps

1. **Modify train_lora_task to capture logs:**
```python
# In server/tasks/training.py, in train_lora_task function:

import subprocess
from pathlib import Path

def train_lora_task(self, training_run_id):
    # ... existing setup code ...

    # Create log file
    log_dir = Path('logs/training')
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f'training_run_{training_run_id}.log'

    # Build training command
    cmd = [
        'python', 'examples/train_lora.py',
        '--data-dir', str(data_dir),
        '--output-dir', str(output_dir),
        '--steps', str(config.get('steps', 1000)),
        '--rank', str(config.get('rank', 4)),
        '--learning-rate', str(config.get('learning_rate', 1e-4))
    ]

    # Run with output capture
    with open(log_file, 'w') as log_f:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1  # Line buffered
        )

        # Stream output to both log file and logger
        for line in process.stdout:
            log_f.write(line)
            log_f.flush()
            logger.info(f"Training output: {line.rstrip()}")

            # Parse progress from output if available
            # Example: "Epoch 1/5, Step 100/500"
            if 'Step' in line:
                # Extract progress and update database
                # training_run.current_step = parsed_step
                # db.session.commit()
                pass

        process.wait()

    # Store log file path in database
    training_run.training_logs = str(log_file)

    if process.returncode != 0:
        training_run.status = 'failed'
        training_run.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        raise RuntimeError(f"Training failed with exit code {process.returncode}")

    # ... rest of success handling ...
```

2. **Update logs endpoint to serve file:**
```python
# In server/routes/training.py, find GET /api/training/runs/<id>/logs

@training_bp.route("/runs/<int:run_id>/logs", methods=["GET"])
def get_training_logs(run_id: int):
    """Get training logs for a specific run."""
    training_run = db.session.get(TrainingRun, run_id)
    if not training_run:
        return jsonify({"error": "Training run not found"}), 404

    # Check if log file exists
    if not training_run.training_logs:
        return jsonify({"logs": "No logs available yet"}), 200

    log_path = Path(training_run.training_logs)
    if not log_path.exists():
        return jsonify({"logs": "Log file not found"}), 404

    # Read and return logs
    try:
        with open(log_path, 'r') as f:
            logs = f.read()

        return jsonify({
            "logs": logs,
            "log_file": str(log_path),
            "status": training_run.status
        })
    except Exception as e:
        logger.error(f"Failed to read log file: {e}")
        return jsonify({"error": "Failed to read logs"}), 500
```

3. **Add log streaming endpoint (optional, for real-time updates):**
```python
@training_bp.route("/runs/<int:run_id>/logs/stream", methods=["GET"])
def stream_training_logs(run_id: int):
    """Stream training logs in real-time (Server-Sent Events)."""
    training_run = db.session.get(TrainingRun, run_id)
    if not training_run or not training_run.training_logs:
        return jsonify({"error": "No logs available"}), 404

    log_path = Path(training_run.training_logs)

    def generate():
        with open(log_path, 'r') as f:
            # Send existing logs
            for line in f:
                yield f"data: {line}\n\n"

            # Tail new logs (if training is still running)
            if training_run.status == 'running':
                while True:
                    line = f.readline()
                    if line:
                        yield f"data: {line}\n\n"
                    else:
                        # Check if training completed
                        db.session.refresh(training_run)
                        if training_run.status != 'running':
                            break
                        time.sleep(0.5)

    return Response(generate(), mimetype='text/event-stream')
```

### Testing Steps

1. **Start a training job:**
```bash
curl -X POST http://localhost:10050/api/training/runs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test_logging",
    "album_ids": [1],
    "config": {"steps": 10}
  }'
```

2. **Check log file creation:**
```bash
ls -la logs/training/
```

3. **Fetch logs via API:**
```bash
curl http://localhost:10050/api/training/runs/1/logs
```

4. **Verify log content:**
```bash
cat logs/training/training_run_1.log
```

### Acceptance Criteria
- ✅ Training output is captured to log file
- ✅ Log file path is stored in TrainingRun.training_logs
- ✅ GET /api/training/runs/<id>/logs returns actual logs
- ✅ Logs update in real-time during training
- ✅ Log files persist after training completion

---

## Task 4: Auto-Register Trained LoRAs 🟢 MEDIUM

**Priority:** P2 (Enhancement)
**Estimated Time:** 1.5 hours
**Files:** `server/tasks/training.py`, `server/api.py` (LoRA listing endpoint)

### Problem
Trained LoRAs are not automatically added to the `/api/loras` list. Users must manually discover and register them.

### Solution Steps

1. **After successful training, register LoRA:**
```python
# In server/tasks/training.py, at end of train_lora_task after training succeeds:

def _register_lora(lora_path: Path, training_run: TrainingRun):
    """Register newly trained LoRA with metadata."""
    from PIL import Image as PILImage
    import json

    # Create metadata file
    metadata = {
        "name": training_run.name,
        "description": f"Trained on {len(training_run.album_ids)} albums",
        "training_run_id": training_run.id,
        "created_at": training_run.created_at.isoformat(),
        "training_config": training_run.config,
        "default_weight": 0.8,
        "tags": ["custom", "trained"]
    }

    metadata_path = lora_path.parent / f"{lora_path.stem}_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Registered LoRA: {lora_path.name}")

# At end of train_lora_task, after training succeeds:
if output_lora_path and Path(output_lora_path).exists():
    _register_lora(Path(output_lora_path), training_run)
```

2. **Update LoRA listing to include custom-trained LoRAs:**
```python
# In server/api.py or wherever /api/loras is defined:

@app.route("/api/loras", methods=["GET"])
def list_loras():
    """List all available LoRA models including custom-trained ones."""
    config = load_config()
    lora_dir = Path(config['paths']['lora_dir'])

    loras = []

    for lora_file in lora_dir.glob("*.safetensors"):
        metadata_file = lora_file.parent / f"{lora_file.stem}_metadata.json"
        preview_file = lora_file.parent / f"{lora_file.stem}_preview.png"

        # Load metadata if exists
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

        lora_info = {
            "folder": lora_file.stem,
            "name": metadata.get("name", lora_file.stem),
            "path": str(lora_file),
            "size": lora_file.stat().st_size,
            "has_preview": preview_file.exists(),
            "preview_url": f"/api/loras/{lora_file.stem}/preview" if preview_file.exists() else None,
            "metadata": metadata,
            "is_custom": "training_run_id" in metadata  # Flag custom-trained LoRAs
        }

        loras.append(lora_info)

    # Sort: custom LoRAs first, then by name
    loras.sort(key=lambda x: (not x["is_custom"], x["name"]))

    return jsonify({"loras": loras, "total": len(loras)})
```

3. **Optionally generate a preview image:**
```python
# After training, generate a quick preview
def _generate_preview(lora_path: Path):
    """Generate preview image using the trained LoRA."""
    preview_path = lora_path.parent / f"{lora_path.stem}_preview.png"

    cmd = [
        'python', 'examples/generate.py',
        '--prompt', 'high quality, detailed, masterpiece',
        '--lora-path', str(lora_path),
        '--lora-weight', '0.8',
        '--output', str(preview_path),
        '--steps', '20',
        '--seed', '42'
    ]

    try:
        subprocess.run(cmd, check=True, timeout=60, capture_output=True)
        logger.info(f"Generated preview for {lora_path.name}")
    except Exception as e:
        logger.warning(f"Failed to generate preview: {e}")
```

### Testing Steps

1. **Complete a training run**
2. **Check metadata file created:**
```bash
ls -la /mnt/speedy/imagineer/models/lora/*_metadata.json
```

3. **Verify LoRA appears in listing:**
```bash
curl http://localhost:10050/api/loras | jq '.loras[] | select(.is_custom)'
```

4. **Check preview generation:**
```bash
ls -la /mnt/speedy/imagineer/models/lora/*_preview.png
```

### Acceptance Criteria
- ✅ Trained LoRAs automatically get metadata files
- ✅ Custom LoRAs appear in /api/loras list
- ✅ Custom LoRAs are flagged with is_custom: true
- ✅ Preview images are generated (optional)
- ✅ LoRAs can be immediately used in generation

---

## Task 5: Training Directory Cleanup 🟢 LOW

**Priority:** P3 (Nice to have)
**Estimated Time:** 30 minutes
**Files:** `server/tasks/training.py`

### Problem
Temporary training directories in `/tmp/training_*` are not cleaned up after training completes.

### Solution Steps

1. **Add cleanup in finally block:**
```python
# In server/tasks/training.py, train_lora_task function:

def train_lora_task(self, training_run_id):
    # ... existing code ...

    temp_dir = None  # Track temp directory

    try:
        # Create temporary directory for training data
        temp_dir = Path(tempfile.mkdtemp(prefix='training_'))
        data_dir = temp_dir / 'data'
        data_dir.mkdir()

        # ... rest of training code ...

    except Exception as e:
        # ... error handling ...
        raise

    finally:
        # Cleanup temporary directory
        if temp_dir and temp_dir.exists():
            try:
                import shutil
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory: {e}")
```

### Testing Steps

1. **Start training**
2. **Monitor /tmp during training:**
```bash
watch -n 1 'ls -la /tmp/training_*'
```

3. **Verify cleanup after completion:**
```bash
ls -la /tmp/training_* 2>&1 | grep "No such file"
```

### Acceptance Criteria
- ✅ Temp directories cleaned up on success
- ✅ Temp directories cleaned up on failure
- ✅ No orphaned directories in /tmp

---

## Summary Checklist

Use this to track your progress:

- [ ] Task 1: Training Album Persistence (1.5h) 🔴
  - [ ] Find training creation endpoint
  - [ ] Add album_ids to TrainingRun creation
  - [ ] Test via API
  - [ ] Verify database record
  - [ ] Confirm task doesn't fail

- [ ] Task 2: SCRAPED_OUTPUT_PATH Init (1h) 🔴
  - [ ] Add scraped_dir to config.yaml
  - [ ] Load config in scraping.py
  - [ ] Create directory if missing
  - [ ] Test path initialization
  - [ ] Run test scrape job

- [ ] Task 3: Training Logs Streaming (2.5h) 🟡
  - [ ] Capture subprocess output to file
  - [ ] Store log path in database
  - [ ] Update logs endpoint
  - [ ] Test log retrieval
  - [ ] Verify real-time updates

- [ ] Task 4: Auto-Register LoRAs (1.5h) 🟢
  - [ ] Create metadata on training completion
  - [ ] Update LoRA listing endpoint
  - [ ] Add is_custom flag
  - [ ] Test registration
  - [ ] Generate preview (optional)

- [ ] Task 5: Training Cleanup (0.5h) 🟢
  - [ ] Add finally block
  - [ ] Test cleanup on success
  - [ ] Test cleanup on failure

**Total Estimated Time:** 7-8 hours
**Critical Path:** Tasks 1 & 2 must complete first

---

## Notes

- **Test as you go** - Don't wait until the end to test
- **Commit frequently** - After each task completion
- **Log everything** - Use logger.info() liberally
- **Check database** - Use sqlite3 CLI to verify data
- **Monitor Celery** - Keep an eye on task execution

## Coordination with Agent 2

- **No file conflicts expected** - You're working on training.py, scraping.py
- **Agent 2 works on** - images.py, labeling.py, frontend
- **Merge order** - Either order is fine, minimal conflicts
- **Communication** - Update CONSOLIDATED_STATUS.md when tasks complete

Good luck! 🚀
