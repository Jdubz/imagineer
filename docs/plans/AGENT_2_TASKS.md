# Agent 2 Task List - Image Management & Labeling Systems

**Agent:** Secondary (working in separate worktree)
**Focus Area:** Image endpoint consolidation, labeling infrastructure, and frontend UI
**Estimated Time:** 7-9 hours
**Files to Modify:** `server/api.py`, `server/routes/images.py`, `server/celery_app.py`, `server/tasks/labeling.py`, `web/src/components/`, `tests/backend/`

---

## Task 1: Consolidate Duplicate Image Endpoints 🔴 CRITICAL

**Priority:** P0 (Blocking)
**Estimated Time:** 2 hours
**Files:** `server/api.py`, `server/routes/images.py`

### Problem
Image and thumbnail endpoints exist in both `server/api.py` and `server/routes/images.py`. The blueprint version (routes/images.py) has the latest safety checks, but the api.py version may still be in use. This causes:
- Code drift between implementations
- Maintenance burden
- Potential bugs from using older version

### Investigation Steps

1. **Identify all image-related endpoints in api.py:**
```bash
grep -n "@app.route.*image\|@app.route.*thumbnail\|@app.route.*outputs" server/api.py | head -20
```

2. **Compare with blueprint:**
```bash
grep -n "@images_bp.route" server/routes/images.py
```

3. **Check which is being used:**
```bash
# Check if blueprint is registered
grep -n "register_blueprint.*images" server/api.py
```

### Solution Steps

1. **Verify blueprint is registered in api.py:**
```python
# In server/api.py, should have:
from server.routes.images import images_bp

app.register_blueprint(images_bp)
```

2. **Remove duplicate endpoints from api.py:**

Find and DELETE these sections from `server/api.py`:
- `/api/images` GET (if exists)
- `/api/images/<id>` GET
- `/api/images/upload` POST (if exists)
- `/api/images/<id>/thumbnail` GET
- `/api/thumbnails/<id>` GET (if exists)
- `/api/outputs/<path>` GET (check if overlaps with blueprint)

**Before deleting, document which endpoints exist:**
```bash
# Create a backup
cp server/api.py server/api.py.backup

# List all endpoints that will be removed
grep -B 2 -A 10 "@app.route.*\(/api/images\|/api/thumbnails\|/api/outputs\)" server/api.py > /tmp/endpoints_to_remove.txt
```

3. **Ensure blueprint has all functionality:**

**Required endpoints in routes/images.py:**
- `GET /api/images` - List with pagination, NSFW filter ✅
- `GET /api/images/<id>` - Get specific image ✅
- `POST /api/images/upload` - Upload with admin auth ✅
- `GET /api/images/<id>/thumbnail` - Generate/serve thumbnail ✅
- `DELETE /api/images/<id>` - Delete image (admin) ✅

If any are missing from blueprint, add them:
```python
# In server/routes/images.py

@images_bp.route("/<int:image_id>/thumbnail", methods=["GET"])
def get_thumbnail(image_id: int):
    """Generate and serve thumbnail for image."""
    image = Image.query.get_or_404(image_id)

    # Check public visibility
    if not image.is_public:
        return jsonify({"error": "Image not found"}), 404

    # Generate thumbnail if missing
    from server.services.thumbnails import generate_thumbnail
    thumbnail_path = generate_thumbnail(image)

    # Serve thumbnail
    return send_file(thumbnail_path, mimetype='image/webp')

@images_bp.route("/<int:image_id>", methods=["DELETE"])
@require_admin
def delete_image(image_id: int):
    """Delete an image (admin only)."""
    image = Image.query.get_or_404(image_id)

    # Delete file
    try:
        Path(image.file_path).unlink(missing_ok=True)
        # Delete thumbnail
        thumbnail_path = Path(f"/mnt/speedy/imagineer/outputs/thumbnails/{image.id}.webp")
        thumbnail_path.unlink(missing_ok=True)
    except Exception as e:
        logger.warning(f"Failed to delete files: {e}")

    # Delete from database
    db.session.delete(image)
    db.session.commit()

    return jsonify({"message": "Image deleted"}), 200
```

4. **Update tests to use blueprint endpoints:**
```bash
# Check tests that use image endpoints
grep -r "/api/images\|/api/thumbnails" tests/
```

5. **Test consolidation:**
```bash
# Start server
python server/api.py

# Test each endpoint
curl http://localhost:10050/api/images
curl http://localhost:10050/api/images/1
curl http://localhost:10050/api/images/1/thumbnail
```

### Acceptance Criteria
- ✅ Only one implementation of each image endpoint exists
- ✅ Blueprint is registered and handling all requests
- ✅ All tests pass with blueprint endpoints
- ✅ No duplicate code in api.py
- ✅ Image upload, listing, thumbnail generation all work

---

## Task 2: Fix Celery Task Naming 🟡 HIGH

**Priority:** P1 (Important)
**Estimated Time:** 1.5 hours
**Files:** `server/celery_app.py`, `server/tasks/labeling.py`, potentially `server/tasks/training.py` and `server/tasks/scraping.py`

### Problem
Celery routing configuration expects task names like `server.tasks.labeling.label_image`, but tasks may be registered with simplified names like `tasks.label_image`. This causes routing issues.

### Investigation Steps

1. **Check current task names:**
```bash
# See how tasks are decorated
grep -n "@celery.*task\|@celery_app.task" server/tasks/*.py
```

2. **Check Celery routing config:**
```bash
grep -A 20 "task_routes\|CELERY_ROUTES" server/celery_app.py
```

3. **Test current task names:**
```bash
# Start Python and check registered tasks
python3 -c "from server.celery_app import celery; print(celery.tasks.keys())"
```

### Solution Steps

1. **Standardize task naming in decorators:**

**Option A - Use explicit names (RECOMMENDED):**
```python
# In server/tasks/labeling.py:

@celery.task(bind=True, name="server.tasks.labeling.label_image")
def label_image_task(self, image_id: int, prompt_type: str = "default"):
    """Label a single image asynchronously."""
    # ... implementation ...

@celery.task(bind=True, name="server.tasks.labeling.label_album")
def label_album_task(self, album_id: int, prompt_type: str = "sd_training", force: bool = False):
    """Label every image in an album."""
    # ... implementation ...
```

**Option B - Import from celery_app consistently:**
```python
# In server/tasks/labeling.py:
from server.celery_app import celery as celery_app

@celery_app.task(bind=True)  # Will auto-generate name as server.tasks.labeling.label_image_task
def label_image_task(self, image_id: int, prompt_type: str = "default"):
    # ... implementation ...
```

2. **Update Celery routing config to match:**
```python
# In server/celery_app.py:

celery.conf.update(
    task_routes={
        # Labeling tasks
        'server.tasks.labeling.label_image': {'queue': 'labeling'},
        'server.tasks.labeling.label_album': {'queue': 'labeling'},

        # Training tasks
        'server.tasks.training.train_lora': {'queue': 'training'},

        # Scraping tasks
        'server.tasks.scraping.scrape_site': {'queue': 'scraping'},

        # Default queue for everything else
        '*': {'queue': 'default'}
    },
    task_default_queue='default',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)
```

3. **Update API calls to use correct task names:**
```bash
# Find all .delay() or .apply_async() calls
grep -n "\.delay\|\.apply_async" server/api.py server/routes/*.py
```

Ensure they match the task names:
```python
# In server/api.py or routes:
from server.tasks.labeling import label_image_task, label_album_task

# Call with correct name
result = label_image_task.delay(image_id, prompt_type)
# or
result = label_album_task.apply_async(args=[album_id, prompt_type], kwargs={'force': force})
```

4. **Verify task registration:**
```bash
# After changes, check registered tasks
python3 -c "
from server.celery_app import celery
import server.tasks.labeling
import server.tasks.training
import server.tasks.scraping
print('Registered tasks:')
for task in sorted(celery.tasks.keys()):
    if not task.startswith('celery.'):
        print(f'  {task}')
"
```

### Testing Steps

1. **Start Celery worker:**
```bash
celery -A server.celery_app worker --loglevel=info
```

2. **Trigger a labeling task:**
```bash
curl -X POST http://localhost:10050/api/labeling/image/1 \
  -H "Content-Type: application/json"
```

3. **Check Celery logs:**
```bash
# Should see task received and executed
# Look for: "Task server.tasks.labeling.label_image[task-id] received"
```

4. **Verify task routing:**
```bash
# Check which queue tasks go to
celery -A server.celery_app inspect active
```

### Acceptance Criteria
- ✅ All tasks have consistent naming convention
- ✅ Task names match routing configuration
- ✅ Tasks route to correct queues
- ✅ API calls use correct task names
- ✅ Celery worker receives and executes tasks

---

## Task 3: Implement Frontend Labeling UI 🟡 HIGH

**Priority:** P1 (Important)
**Estimated Time:** 3 hours
**Files:** `web/src/components/LabelingPanel.tsx` (new), `web/src/components/AlbumsTab.tsx`, `web/src/App.tsx`

### Problem
No frontend UI to trigger image labeling. Users cannot label images without direct API calls.

### Solution Steps

1. **Create LabelingPanel component:**

```typescript
// web/src/components/LabelingPanel.tsx
import React, { useState } from 'react';
import '../styles/LabelingPanel.css';

interface LabelingPanelProps {
  imageId?: number;
  albumId?: number;
  onComplete?: () => void;
}

export const LabelingPanel: React.FC<LabelingPanelProps> = ({
  imageId,
  albumId,
  onComplete
}) => {
  const [isLabeling, setIsLabeling] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('');
  const [progress, setProgress] = useState(0);

  const startLabeling = async () => {
    setIsLabeling(true);
    setStatus('Starting labeling...');

    try {
      const endpoint = imageId
        ? `/api/labeling/image/${imageId}`
        : `/api/labeling/album/${albumId}`;

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt_type: 'sd_training',
          force: false
        })
      });

      const data = await response.json();

      if (response.status === 202) {
        // Async task started
        setTaskId(data.task_id);
        setStatus('Labeling in progress...');
        pollTaskStatus(data.task_id);
      } else if (response.ok) {
        // Immediate success
        setStatus('Labeling complete!');
        setProgress(100);
        setTimeout(() => {
          onComplete?.();
          resetState();
        }, 2000);
      } else {
        throw new Error(data.error || 'Labeling failed');
      }
    } catch (error) {
      console.error('Labeling error:', error);
      setStatus(`Error: ${error.message}`);
      setIsLabeling(false);
    }
  };

  const pollTaskStatus = async (taskId: string) => {
    const poll = setInterval(async () => {
      try {
        const response = await fetch(`/api/labeling/tasks/${taskId}`);
        const data = await response.json();

        if (data.state === 'SUCCESS') {
          setStatus('Labeling complete!');
          setProgress(100);
          clearInterval(poll);
          setTimeout(() => {
            onComplete?.();
            resetState();
          }, 2000);
        } else if (data.state === 'FAILURE') {
          setStatus(`Failed: ${data.result?.message || 'Unknown error'}`);
          setIsLabeling(false);
          clearInterval(poll);
        } else if (data.state === 'PROGRESS') {
          const current = data.result?.current || 0;
          const total = data.result?.total || 1;
          setProgress((current / total) * 100);
          setStatus(`Labeled ${current} of ${total} images...`);
        } else {
          setStatus(`Status: ${data.state}`);
        }
      } catch (error) {
        console.error('Poll error:', error);
        clearInterval(poll);
        setIsLabeling(false);
      }
    }, 2000); // Poll every 2 seconds

    // Cleanup
    return () => clearInterval(poll);
  };

  const resetState = () => {
    setIsLabeling(false);
    setTaskId(null);
    setStatus('');
    setProgress(0);
  };

  return (
    <div className="labeling-panel">
      <h3>🏷️ AI Labeling</h3>

      <div className="labeling-info">
        {imageId && <p>Labeling image #{imageId}</p>}
        {albumId && <p>Labeling entire album</p>}
        <p className="help-text">
          Claude will analyze {imageId ? 'this image' : 'all images in this album'}
          and generate captions, tags, and NSFW ratings.
        </p>
      </div>

      {isLabeling ? (
        <div className="labeling-progress">
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="status-text">{status}</p>
          {taskId && <p className="task-id">Task: {taskId}</p>}
        </div>
      ) : (
        <button
          className="label-button"
          onClick={startLabeling}
        >
          🚀 Start Labeling
        </button>
      )}
    </div>
  );
};
```

2. **Add styling:**

```css
/* web/src/styles/LabelingPanel.css */
.labeling-panel {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 20px;
  margin: 20px 0;
}

.labeling-panel h3 {
  margin-top: 0;
  color: #343a40;
}

.labeling-info {
  margin: 15px 0;
}

.labeling-info .help-text {
  color: #6c757d;
  font-size: 0.9em;
  margin-top: 10px;
}

.label-button {
  background: #007bff;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  font-size: 1em;
  cursor: pointer;
  transition: background 0.2s;
}

.label-button:hover {
  background: #0056b3;
}

.labeling-progress {
  margin-top: 20px;
}

.progress-bar {
  background: #e9ecef;
  border-radius: 10px;
  height: 24px;
  overflow: hidden;
  margin: 10px 0;
}

.progress-fill {
  background: linear-gradient(90deg, #007bff, #0056b3);
  height: 100%;
  transition: width 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
}

.status-text {
  color: #495057;
  margin: 10px 0;
}

.task-id {
  color: #6c757d;
  font-size: 0.85em;
  font-family: monospace;
}
```

3. **Integrate into AlbumsTab:**

```typescript
// web/src/components/AlbumsTab.tsx
import { LabelingPanel } from './LabelingPanel';

// Inside AlbumsTab component, add a section:

{selectedAlbum && (
  <div className="album-details">
    <h2>{selectedAlbum.name}</h2>
    <p>{selectedAlbum.description}</p>

    {/* Add labeling section */}
    {isAdmin && (
      <LabelingPanel
        albumId={selectedAlbum.id}
        onComplete={() => {
          // Refresh album data
          fetchAlbumDetails(selectedAlbum.id);
        }}
      />
    )}

    {/* Rest of album content */}
  </div>
)}
```

4. **Add to individual image view (optional):**

```typescript
// In ImageModal or ImageDetails component:
{isAdmin && (
  <LabelingPanel
    imageId={image.id}
    onComplete={() => fetchImageDetails(image.id)}
  />
)}
```

### Testing Steps

1. **Build frontend:**
```bash
cd web && npm run build
```

2. **Test single image labeling:**
- Click on an image
- Should see labeling panel
- Click "Start Labeling"
- Should see progress

3. **Test album batch labeling:**
- Navigate to AlbumsTab
- Select an album
- Click "Start Labeling"
- Should see progress for multiple images

4. **Test error handling:**
- Try labeling without auth (should fail)
- Try labeling non-existent image (should handle gracefully)

### Acceptance Criteria
- ✅ LabelingPanel component renders
- ✅ Can trigger single image labeling
- ✅ Can trigger album batch labeling
- ✅ Progress updates in real-time
- ✅ Shows completion/error states
- ✅ Refreshes data after completion
- ✅ Only visible to admin users

---

## Task 4: Update Async Labeling Tests 🟢 MEDIUM

**Priority:** P2 (Important)
**Estimated Time:** 1.5 hours
**Files:** `tests/backend/test_phase3_labeling.py`

### Problem
Tests assume synchronous execution but API now returns 202 + task_id for async processing.

### Solution Steps

1. **Update test fixtures:**

```python
# tests/backend/test_phase3_labeling.py

import pytest
from unittest.mock import Mock, patch
from server.tasks.labeling import label_image_task

@pytest.fixture
def mock_celery_task():
    """Mock Celery task execution."""
    with patch('server.tasks.labeling.label_image_task.delay') as mock_delay:
        mock_result = Mock()
        mock_result.id = 'test-task-id-123'
        mock_delay.return_value = mock_result
        yield mock_delay

@pytest.fixture
def mock_celery_result():
    """Mock Celery AsyncResult."""
    with patch('server.api.AsyncResult') as mock_result:
        result_obj = Mock()
        result_obj.state = 'SUCCESS'
        result_obj.result = {
            'status': 'success',
            'image_id': 1,
            'nsfw_rating': 'SAFE',
            'tags': ['test', 'image']
        }
        mock_result.return_value = result_obj
        yield mock_result
```

2. **Update API tests:**

```python
def test_label_image_endpoint_async(client, mock_celery_task):
    """Test async image labeling via API."""
    response = client.post('/api/labeling/image/1')

    assert response.status_code == 202
    data = response.json
    assert 'task_id' in data
    assert data['task_id'] == 'test-task-id-123'
    assert 'status' in data

    # Verify task was called
    mock_celery_task.assert_called_once_with(1, 'default')

def test_label_album_endpoint_async(client, mock_celery_task):
    """Test async album labeling via API."""
    response = client.post(
        '/api/labeling/album/1',
        json={'prompt_type': 'sd_training', 'force': False}
    )

    assert response.status_code == 202
    data = response.json
    assert 'task_id' in data
    assert 'message' in data

    mock_celery_task.assert_called_once()

def test_task_status_endpoint(client, mock_celery_result):
    """Test task status polling endpoint."""
    response = client.get('/api/labeling/tasks/test-task-id-123')

    assert response.status_code == 200
    data = response.json
    assert data['state'] == 'SUCCESS'
    assert data['result']['status'] == 'success'
```

3. **Add integration test with actual Celery:**

```python
@pytest.mark.integration
def test_label_image_full_workflow(client, test_db, test_image):
    """Full integration test with real Celery task."""
    # Start labeling
    response = client.post(f'/api/labeling/image/{test_image.id}')
    assert response.status_code == 202
    task_id = response.json['task_id']

    # Poll for completion (with timeout)
    import time
    max_wait = 30  # 30 seconds
    start = time.time()

    while time.time() - start < max_wait:
        response = client.get(f'/api/labeling/tasks/{task_id}')
        data = response.json

        if data['state'] in ['SUCCESS', 'FAILURE']:
            break

        time.sleep(1)

    assert data['state'] == 'SUCCESS'
    assert 'result' in data

    # Verify database updated
    from server.database import Image, Label
    image = test_db.session.get(Image, test_image.id)
    assert len(image.labels) > 0
```

4. **Test error handling:**

```python
def test_label_nonexistent_image(client):
    """Test labeling non-existent image."""
    response = client.post('/api/labeling/image/99999')
    assert response.status_code == 404

def test_label_without_auth(client):
    """Test labeling without authentication (if required)."""
    # If labeling requires admin auth
    response = client.post('/api/labeling/image/1')
    # Should return 401 or 403
    assert response.status_code in [401, 403]
```

### Testing Steps

1. **Run unit tests:**
```bash
pytest tests/backend/test_phase3_labeling.py -v
```

2. **Run integration tests:**
```bash
pytest tests/backend/test_phase3_labeling.py -v -m integration
```

3. **Check coverage:**
```bash
pytest tests/backend/test_phase3_labeling.py --cov=server.tasks.labeling --cov-report=term
```

### Acceptance Criteria
- ✅ Tests expect 202 status for async tasks
- ✅ Tests mock Celery task execution
- ✅ Tests cover task status polling
- ✅ Integration tests work with real Celery
- ✅ All tests pass
- ✅ Coverage remains >80%

---

## Task 5: Add Frontend Tests for Admin UIs 🟢 MEDIUM

**Priority:** P2 (Nice to have)
**Estimated Time:** 1.5 hours
**Files:** `web/src/components/*.test.tsx` (new test files)

### Problem
Admin UI components (LabelingPanel, AlbumsTab features) lack test coverage.

### Solution Steps

1. **Create LabelingPanel tests:**

```typescript
// web/src/components/LabelingPanel.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { LabelingPanel } from './LabelingPanel';

describe('LabelingPanel', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  test('renders labeling panel with image ID', () => {
    render(<LabelingPanel imageId={123} />);
    expect(screen.getByText(/Labeling image #123/i)).toBeInTheDocument();
  });

  test('renders labeling panel with album ID', () => {
    render(<LabelingPanel albumId={456} />);
    expect(screen.getByText(/Labeling entire album/i)).toBeInTheDocument();
  });

  test('starts labeling when button clicked', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      status: 202,
      json: async () => ({ task_id: 'test-task-123' })
    });

    render(<LabelingPanel imageId={1} />);

    const button = screen.getByText(/Start Labeling/i);
    fireEvent.click(button);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/labeling/image/1',
        expect.objectContaining({ method: 'POST' })
      );
    });

    expect(screen.getByText(/Labeling in progress/i)).toBeInTheDocument();
  });

  test('polls task status and shows progress', async () => {
    // Mock initial labeling request
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        status: 202,
        json: async () => ({ task_id: 'test-task-123' })
      })
      // Mock status polling responses
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          state: 'PROGRESS',
          result: { current: 5, total: 10 }
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          state: 'SUCCESS',
          result: { status: 'success' }
        })
      });

    jest.useFakeTimers();
    render(<LabelingPanel albumId={1} />);

    fireEvent.click(screen.getByText(/Start Labeling/i));

    // Fast-forward through polling
    await waitFor(() => {
      expect(screen.getByText(/Labeled 5 of 10/i)).toBeInTheDocument();
    });

    jest.advanceTimersByTime(2000);

    await waitFor(() => {
      expect(screen.getByText(/complete/i)).toBeInTheDocument();
    });

    jest.useRealTimers();
  });

  test('shows error on failure', async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(
      new Error('Network error')
    );

    render(<LabelingPanel imageId={1} />);
    fireEvent.click(screen.getByText(/Start Labeling/i));

    await waitFor(() => {
      expect(screen.getByText(/Error: Network error/i)).toBeInTheDocument();
    });
  });

  test('calls onComplete callback when finished', async () => {
    const onComplete = jest.fn();

    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        status: 202,
        json: async () => ({ task_id: 'test-task-123' })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ state: 'SUCCESS' })
      });

    jest.useFakeTimers();
    render(<LabelingPanel imageId={1} onComplete={onComplete} />);

    fireEvent.click(screen.getByText(/Start Labeling/i));
    jest.advanceTimersByTime(5000);

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalled();
    });

    jest.useRealTimers();
  });
});
```

2. **Run tests:**
```bash
cd web && npm test -- LabelingPanel.test.tsx
```

### Acceptance Criteria
- ✅ LabelingPanel has test coverage
- ✅ Tests cover happy path and errors
- ✅ Tests verify polling behavior
- ✅ All tests pass

---

## Summary Checklist

Use this to track your progress:

- [ ] Task 1: Consolidate Duplicate Endpoints (2h) 🔴
  - [ ] Identify duplicate endpoints in api.py
  - [ ] Verify blueprint is registered
  - [ ] Remove duplicates from api.py
  - [ ] Test all image endpoints work
  - [ ] Update tests

- [ ] Task 2: Fix Celery Task Naming (1.5h) 🟡
  - [ ] Check current task registration
  - [ ] Standardize task names
  - [ ] Update routing config
  - [ ] Verify task discovery
  - [ ] Test task execution

- [ ] Task 3: Frontend Labeling UI (3h) 🟡
  - [ ] Create LabelingPanel component
  - [ ] Add styling
  - [ ] Integrate into AlbumsTab
  - [ ] Test single image labeling
  - [ ] Test album batch labeling

- [ ] Task 4: Update Async Tests (1.5h) 🟢
  - [ ] Create Celery mocks
  - [ ] Update API tests
  - [ ] Add integration tests
  - [ ] Test error cases
  - [ ] Verify coverage

- [ ] Task 5: Frontend Tests (1.5h) 🟢
  - [ ] Write LabelingPanel tests
  - [ ] Test user interactions
  - [ ] Test polling logic
  - [ ] Verify all pass

**Total Estimated Time:** 9-10 hours
**Critical Path:** Task 1 should complete first to unblock other work

---

## Notes

- **Separate Worktree Setup:**
```bash
# Create a new worktree
git worktree add ../imagineer-agent2 develop

# Work in that directory
cd ../imagineer-agent2
```

- **Test as you go** - Don't wait until the end
- **Commit frequently** - After each task
- **Use TypeScript** - Frontend components should be .tsx
- **Mock API calls** - Use jest.mock() for fetch

## Coordination with Agent 1

- **File Conflicts:**
  - You work on: api.py, routes/images.py, routes/albums.py, tasks/labeling.py, celery_app.py
  - Agent 1 works on: routes/training.py, tasks/training.py, tasks/scraping.py
  - **Potential conflict:** api.py (but minimal, different sections)

- **Merge Strategy:**
  - Agent 1 should merge first (training/scraping fixes)
  - Then you merge (image consolidation + labeling UI)
  - Conflicts should be minimal and easy to resolve

- **Communication:**
  - Both update CONSOLIDATED_STATUS.md when complete
  - Mark tasks as ✅ in the document

Good luck! 🎨
