# Imagineer - Comprehensive Improvement Plan

**Project:** Imagineer AI Image Generation Platform
**Audit Date:** 2025-10-26
**Project Phase:** Development (Solo project, no production users)
**Infrastructure Approach:** Pragmatic (Redis/PostgreSQL acceptable, Docker Compose)

---

## 🔄 UPDATED: See REVISED_IMPROVEMENT_PLAN.md

**This original plan was based on initial assumptions about the project scope. After analyzing the actual codebase and understanding your real goals, a completely revised plan has been created that focuses on building the album system, AI labeling, web scraping integration, and training pipeline.**

**👉 For the actual implementation roadmap, see: [`REVISED_IMPROVEMENT_PLAN.md`](./REVISED_IMPROVEMENT_PLAN.md)**

This document remains useful for:
- Security audit findings (28 vulnerabilities identified)
- Code quality review (34 issues found)
- General architectural best practices
- Reference for specific technical implementations

---

## Executive Summary

This comprehensive improvement plan synthesizes findings from security, code quality, and architectural audits of the Imagineer codebase. Based on your priorities (job queue reliability, generation speed/throughput, testing and code quality) and ML roadmap (training, fine-tuning, edge deployment), this plan provides a phased approach to transform Imagineer from a development project into a production-ready ML platform.

### Critical Findings

**Security:** 28 vulnerabilities identified (5 critical, 8 high, 10 medium, 5 low)
**Code Quality:** 34 issues found, test coverage at ~25% backend, 0% frontend
**Architecture:** Monolithic design with in-memory queue, blocking job processing, no persistence

### Overall Assessment

- **Security Posture:** HIGH RISK - Critical issues must be fixed before any production deployment
- **Code Quality Score:** 68/100 - Good foundation but needs systematic improvements
- **Architecture Maturity:** Early stage - Works for development but needs infrastructure upgrades

---

## Your Priorities

Based on your responses, this plan focuses on:

1. ✅ **Job Queue Reliability** - Move from in-memory to persistent Redis-backed queue
2. ✅ **Generation Speed/Throughput** - Implement async processing, optimize GPU usage
3. ✅ **Testing and Code Quality** - Achieve 80%+ test coverage, refactor monolithic code
4. ✅ **ML Pipeline Foundation** - Architecture to support training, fine-tuning, model versioning

---

## Phased Implementation Roadmap

### Phase 1: Critical Security & Foundation (Week 1-2, ~40 hours)

**Goal:** Fix critical security vulnerabilities and establish testing infrastructure

#### 1.1 Security Fixes (Priority: CRITICAL)

**Estimated Time:** 12 hours

```bash
# Issues to fix:
✓ CRITICAL-1: Hardcoded secret keys
✓ CRITICAL-2: Client-side password authentication
✓ CRITICAL-4: Missing API authentication
✓ CRITICAL-5: CORS misconfiguration
✓ HIGH-2: Plaintext user storage
```

**Action Items:**

1. **Remove hardcoded secrets** (2 hours)
```python
# server/auth.py:74
def get_secret_key() -> str:
    """Get Flask secret key - MUST be set in production"""
    secret = os.environ.get("FLASK_SECRET_KEY")

    if not secret:
        if os.environ.get("FLASK_ENV") == "production":
            raise RuntimeError(
                "FLASK_SECRET_KEY must be set. Generate with:\n"
                "  python -c 'import secrets; print(secrets.token_hex(32))'"
            )
        # Development only - generate and warn
        import secrets
        secret = secrets.token_hex(32)
        logger.warning(f"Generated dev secret key: {secret}")

    return secret

app.config["SECRET_KEY"] = get_secret_key()
```

2. **Remove PasswordGate component** (1 hour)
```bash
# Delete client-side password authentication
rm web/src/components/PasswordGate.jsx
rm web/src/styles/PasswordGate.css

# Update App.jsx to remove PasswordGate wrapper
# Update .env.example to remove VITE_APP_PASSWORD
```

3. **Add API authentication decorators** (4 hours)
```python
# server/api.py - Apply to ALL sensitive endpoints

# Admin only
@app.route("/api/config", methods=["PUT"])
@require_role(ROLE_ADMIN)
def update_config():
    ...

# Editor and above
@app.route("/api/sets/<set_name>/loras", methods=["PUT"])
@require_role(ROLE_EDITOR)
def update_set_loras(set_name):
    ...

# Authenticated users
@app.route("/api/generate", methods=["POST"])
@require_auth
def generate():
    ...

@app.route("/api/outputs/<path:filename>")
@require_auth
def serve_output(filename):
    ...
```

4. **Fix CORS configuration** (1 hour)
```python
# server/api.py:28
ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '').split(',')
if not ALLOWED_ORIGINS or ALLOWED_ORIGINS == ['']:
    ALLOWED_ORIGINS = [
        'http://localhost:3000',
        'http://localhost:5173',
        'http://127.0.0.1:3000',
        'http://127.0.0.1:5173'
    ]

CORS(app,
     resources={r"/api/*": {"origins": ALLOWED_ORIGINS}},
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE"])
```

5. **Migrate users.json to SQLite** (4 hours)
```python
# server/auth.py - Replace file-based with database

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "users.db"

def init_user_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            name TEXT,
            role TEXT NOT NULL DEFAULT 'viewer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            action TEXT NOT NULL,
            old_role TEXT,
            new_role TEXT,
            changed_by TEXT,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

# Update .gitignore to exclude users.db
```

**Testing:**
- Test all endpoints with/without authentication
- Verify CORS with different origins
- Test user role permissions (viewer/editor/admin)

#### 1.2 Testing Infrastructure (Priority: HIGH)

**Estimated Time:** 16 hours

**Current State:** Backend ~25% coverage, Frontend ~0%
**Target:** Backend 80%+, Frontend 70%+

**Action Items:**

1. **Backend test suite** (10 hours)

```python
# tests/backend/test_generate.py (NEW FILE)
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_lora_loading_single():
    """Test single LoRA loading works correctly"""
    with patch('examples.generate.StableDiffusionPipeline') as mock_pipe:
        # Test implementation
        pass

def test_lora_loading_multiple():
    """Test multi-LoRA stacking"""
    with patch('examples.generate.load_lora_weights') as mock_load:
        # Test multiple LoRAs are loaded with correct weights
        pass

def test_generation_with_fixed_seed():
    """Test reproducible generation with same seed"""
    pass

def test_memory_cleanup():
    """Test CUDA memory is properly released"""
    pass

# tests/backend/test_auth.py (NEW FILE)
def test_require_auth_decorator_blocks_unauthenticated():
    """Test @require_auth blocks requests without session"""
    pass

def test_require_role_admin():
    """Test @require_role(ROLE_ADMIN) blocks non-admin users"""
    pass

def test_user_database_operations():
    """Test user CRUD operations"""
    pass

def test_oauth_callback_success():
    """Test successful OAuth callback flow"""
    pass

# tests/backend/test_security.py (NEW FILE)
def test_path_traversal_set_loading():
    """Verify set loading blocks path traversal"""
    with pytest.raises(ValueError):
        load_set_data("../../etc/passwd")

def test_path_traversal_output_serving(client):
    """Verify output serving blocks path traversal"""
    response = client.get('/api/outputs/../../../etc/passwd')
    assert response.status_code in [403, 404]

def test_command_injection_prevention():
    """Test subprocess calls sanitize inputs"""
    pass

# tests/backend/test_api_validation.py (NEW FILE)
def test_seed_validation():
    """Test seed parameter validation"""
    pass

def test_steps_validation():
    """Test steps parameter validation"""
    pass

def test_dimension_validation():
    """Test width/height validation"""
    pass
```

2. **Frontend test suite** (6 hours)

```javascript
// tests/components/GenerateForm.test.jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import GenerateForm from '../../src/components/GenerateForm'

describe('GenerateForm', () => {
  test('validates prompt input', () => {
    render(<GenerateForm />)
    const submitButton = screen.getByText('Generate')

    // Empty prompt should be rejected
    fireEvent.click(submitButton)
    expect(screen.getByText(/prompt is required/i)).toBeInTheDocument()
  })

  test('submits single generation with valid parameters', async () => {
    const mockOnGenerate = jest.fn()
    render(<GenerateForm onGenerate={mockOnGenerate} />)

    fireEvent.change(screen.getByLabelText('Prompt'), {
      target: { value: 'A beautiful sunset' }
    })
    fireEvent.click(screen.getByText('Generate'))

    await waitFor(() => {
      expect(mockOnGenerate).toHaveBeenCalledWith(
        expect.objectContaining({
          prompt: 'A beautiful sunset'
        })
      )
    })
  })

  test('loads and displays set options', async () => {
    // Test batch generation set selection
  })
})

// tests/components/App.test.jsx
describe('App', () => {
  test('loads initial data on mount', async () => {
    // Mock API calls
    global.fetch = jest.fn()
      .mockResolvedValueOnce({ json: () => Promise.resolve({ config: {} }) })
      .mockResolvedValueOnce({ json: () => Promise.resolve({ images: [] }) })
      .mockResolvedValueOnce({ json: () => Promise.resolve({ batches: [] }) })

    render(<App />)

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(3)
    })
  })

  test('handles API failures gracefully', async () => {
    // Test error states
  })
})
```

3. **CI/CD integration** (Already exists, enhance)

```yaml
# .github/workflows/test-backend.yml - ADD coverage reporting
- name: Run tests with coverage
  run: |
    pytest tests/backend/ --cov=server --cov=examples --cov-report=xml --cov-report=term

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml

- name: Enforce minimum coverage
  run: |
    coverage report --fail-under=80
```

#### 1.3 Structured Logging (Priority: HIGH)

**Estimated Time:** 6 hours

```python
# server/logging_config.py (NEW FILE)
import logging
import json
from logging.handlers import RotatingFileHandler
from datetime import datetime
from flask import request, has_request_context

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging"""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add request context if available
        if has_request_context():
            log_data["request"] = {
                "method": request.method,
                "path": request.path,
                "ip": request.remote_addr,
                "user_agent": request.headers.get('User-Agent', '')
            }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)

def configure_logging(app):
    """Configure structured logging for the application"""

    # Create logs directory
    import os
    os.makedirs('logs', exist_ok=True)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Console handler - human readable for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)

    # File handler - JSON for production parsing
    file_handler = RotatingFileHandler(
        'logs/imagineer.log',
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(JSONFormatter())

    # Security audit log - separate file
    security_handler = RotatingFileHandler(
        'logs/security_audit.log',
        maxBytes=10485760,
        backupCount=10
    )
    security_handler.setLevel(logging.WARNING)
    security_handler.setFormatter(JSONFormatter())

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Security logger
    security_logger = logging.getLogger('security')
    security_logger.addHandler(security_handler)

    return root_logger

# server/api.py - ADD at top
from server.logging_config import configure_logging

logger = configure_logging(app)

# ADD centralized error handling
@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {e}", exc_info=True)

    if app.debug:
        return jsonify({
            "error": "Internal server error",
            "detail": str(e),
            "type": type(e).__name__
        }), 500
    else:
        return jsonify({"error": "Internal server error"}), 500

# ADD security event logging
security_logger = logging.getLogger('security')

# In routes - add logging
@app.route("/auth/google/callback")
def auth_callback():
    try:
        # ... existing auth code
        security_logger.info(f"Successful login: {user.email}", extra={
            "event": "authentication_success",
            "user_email": user.email,
            "role": user.role
        })
    except Exception as e:
        security_logger.warning(f"Failed login attempt", extra={
            "event": "authentication_failure",
            "error": str(e)
        })
```

#### 1.4 Input Validation Layer (Priority: MEDIUM)

**Estimated Time:** 6 hours

```python
# server/validators.py (NEW FILE)
"""Input validation utilities"""

import re
from typing import Dict, Any, Optional
from flask import jsonify

class ValidationError(Exception):
    """Raised when input validation fails"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

def validate_seed(seed: Optional[int]) -> Optional[int]:
    """Validate seed parameter.

    Args:
        seed: Random seed value

    Returns:
        Validated seed or None

    Raises:
        ValidationError: If seed is invalid
    """
    if seed is None:
        return None

    try:
        seed = int(seed)
        if not 0 <= seed <= 2147483647:
            raise ValidationError("Seed must be between 0 and 2147483647")
        return seed
    except (ValueError, TypeError):
        raise ValidationError("Invalid seed value")

def validate_steps(steps: Optional[int]) -> Optional[int]:
    """Validate steps parameter."""
    if steps is None:
        return None

    try:
        steps = int(steps)
        if not 1 <= steps <= 150:
            raise ValidationError("Steps must be between 1 and 150")
        return steps
    except (ValueError, TypeError):
        raise ValidationError("Invalid steps value")

def validate_dimensions(width: Optional[int], height: Optional[int]) -> tuple:
    """Validate width and height parameters."""
    if width is not None:
        try:
            width = int(width)
            if width < 64 or width > 2048:
                raise ValidationError("Width must be between 64 and 2048")
            if width % 8 != 0:
                raise ValidationError("Width must be divisible by 8")
        except (ValueError, TypeError):
            raise ValidationError("Invalid width value")

    if height is not None:
        try:
            height = int(height)
            if height < 64 or height > 2048:
                raise ValidationError("Height must be between 64 and 2048")
            if height % 8 != 0:
                raise ValidationError("Height must be divisible by 8")
        except (ValueError, TypeError):
            raise ValidationError("Invalid height value")

    return width, height

def validate_prompt(prompt: str) -> str:
    """Validate prompt parameter."""
    if not prompt or not prompt.strip():
        raise ValidationError("Prompt cannot be empty")

    prompt = prompt.strip()

    if len(prompt) > 500:
        raise ValidationError("Prompt too long (max 500 characters)")

    return prompt

def validate_set_name(set_name: str) -> str:
    """Validate set name for path safety."""
    # Only allow alphanumeric, underscore, hyphen
    if not re.match(r'^[a-zA-Z0-9_-]+$', set_name):
        raise ValidationError(
            "Invalid set name. Only alphanumeric, underscore, and hyphen allowed."
        )

    if len(set_name) > 64:
        raise ValidationError("Set name too long (max 64 characters)")

    return set_name

def validate_lora_weight(weight: float) -> float:
    """Validate LoRA weight parameter."""
    try:
        weight = float(weight)
        if not -2.0 <= weight <= 2.0:
            raise ValidationError("LoRA weight must be between -2.0 and 2.0")
        return weight
    except (ValueError, TypeError):
        raise ValidationError("Invalid LoRA weight value")

def validate_generation_params(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate all generation parameters.

    Args:
        data: Request data dictionary

    Returns:
        Dictionary of validated parameters

    Raises:
        ValidationError: If any parameter is invalid
    """
    validated = {}

    # Required parameters
    validated['prompt'] = validate_prompt(data['prompt'])

    # Optional parameters
    if 'seed' in data:
        validated['seed'] = validate_seed(data.get('seed'))

    if 'steps' in data:
        validated['steps'] = validate_steps(data.get('steps'))

    if 'width' in data or 'height' in data:
        width, height = validate_dimensions(
            data.get('width'),
            data.get('height')
        )
        if width:
            validated['width'] = width
        if height:
            validated['height'] = height

    if 'guidance_scale' in data:
        try:
            guidance = float(data['guidance_scale'])
            if not 1.0 <= guidance <= 30.0:
                raise ValidationError("Guidance scale must be between 1.0 and 30.0")
            validated['guidance_scale'] = guidance
        except (ValueError, TypeError):
            raise ValidationError("Invalid guidance scale value")

    if 'lora_weight' in data:
        validated['lora_weight'] = validate_lora_weight(data['lora_weight'])

    if 'lora_weights' in data:
        validated['lora_weights'] = [
            validate_lora_weight(w) for w in data['lora_weights']
        ]

    return validated

# server/api.py - UPDATE routes to use validation

from server.validators import validate_generation_params, validate_set_name, ValidationError

@app.route("/api/generate", methods=["POST"])
@require_auth
def generate():
    """Submit single image generation job"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Request body required"}), 400

        # Validate all parameters
        params = validate_generation_params(data)

        # ... rest of existing logic using validated params

    except ValidationError as e:
        logger.warning(f"Validation error: {e.message}")
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        logger.error(f"Generation error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
```

**Phase 1 Deliverables:**
- ✅ All critical security vulnerabilities fixed
- ✅ API authentication enforced on all endpoints
- ✅ Users migrated from JSON to SQLite database
- ✅ Test coverage: Backend 50%+, Frontend 40%+
- ✅ Structured JSON logging in place
- ✅ Centralized input validation

---

### Phase 2: Queue Reliability & Architecture (Week 3-4, ~50 hours)

**Goal:** Replace in-memory queue with persistent Redis-backed system, add job persistence

#### 2.1 Redis-Backed Job Queue (Priority: HIGH)

**Estimated Time:** 16 hours

**Current Issues:**
- In-memory queue lost on restart (server/api.py:131-133)
- Single-threaded worker blocks on long jobs
- No job cancellation support
- No queue size limits

**Solution: Celery + Redis**

```bash
# 1. Add dependencies
# requirements.txt
celery>=5.3.0
redis>=5.0.0
flower>=2.0.0  # Optional: web UI for monitoring

# 2. Update docker-compose.yml
```

```yaml
# docker-compose.yml - ADD Redis service
services:
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - imagineer-network

  celery-worker:
    build: .
    command: celery -A server.celery_app worker --loglevel=info --concurrency=1
    depends_on:
      - redis
      - api
    environment:
      - REDIS_URL=redis://redis:6379/0
      - FLASK_ENV=${FLASK_ENV:-development}
    volumes:
      - .:/app
      - /mnt/speedy/imagineer:/mnt/speedy/imagineer
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    networks:
      - imagineer-network

  # Optional: Flower for queue monitoring
  flower:
    build: .
    command: celery -A server.celery_app flower --port=5555
    depends_on:
      - redis
      - celery-worker
    ports:
      - "5555:5555"
    environment:
      - REDIS_URL=redis://redis:6379/0
    networks:
      - imagineer-network

volumes:
  redis-data:
```

```python
# server/celery_app.py (NEW FILE)
"""Celery configuration for async task processing"""

from celery import Celery
import os

def make_celery():
    """Create Celery instance"""
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

    celery = Celery(
        'imagineer',
        broker=redis_url,
        backend=redis_url
    )

    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=600,  # 10 minute hard limit
        task_soft_time_limit=540,  # 9 minute soft limit
        worker_prefetch_multiplier=1,  # One task at a time per worker
        worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (memory cleanup)
    )

    return celery

celery = make_celery()

# server/tasks.py (NEW FILE)
"""Celery tasks for image generation"""

from server.celery_app import celery
from pathlib import Path
import subprocess
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@celery.task(bind=True, name='tasks.generate_image')
def generate_image_task(self, job_data):
    """
    Async image generation task.

    Args:
        job_data: Dictionary containing generation parameters

    Returns:
        Dictionary with result status and output path
    """
    try:
        logger.info(f"Starting generation task {self.request.id}")

        # Build command
        cmd = [
            'python',
            'examples/generate.py',
            '--prompt', job_data['prompt']
        ]

        # Add optional parameters
        if 'seed' in job_data:
            cmd.extend(['--seed', str(job_data['seed'])])

        if 'steps' in job_data:
            cmd.extend(['--steps', str(job_data['steps'])])

        if 'width' in job_data:
            cmd.extend(['--width', str(job_data['width'])])

        if 'height' in job_data:
            cmd.extend(['--height', str(job_data['height'])])

        # LoRA support
        if 'lora_paths' in job_data and job_data['lora_paths']:
            for lora_path in job_data['lora_paths']:
                cmd.extend(['--lora-path', lora_path])

            if 'lora_weights' in job_data:
                for weight in job_data['lora_weights']:
                    cmd.extend(['--lora-weight', str(weight)])
        elif 'lora_path' in job_data:
            cmd.extend(['--lora-path', job_data['lora_path']])
            if 'lora_weight' in job_data:
                cmd.extend(['--lora-weight', str(job_data['lora_weight'])])

        # Output path
        if 'output' in job_data:
            cmd.extend(['--output', job_data['output']])

        # Update task progress
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Running generation...'}
        )

        # Execute generation
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=job_data.get('timeout', 300),
            cwd=Path(__file__).parent.parent
        )

        if result.returncode == 0:
            logger.info(f"Task {self.request.id} completed successfully")

            # Parse output to get generated image path
            output_path = None
            for line in result.stdout.split('\n'):
                if 'Saved to:' in line:
                    output_path = line.split('Saved to:')[1].strip()
                    break

            return {
                'status': 'completed',
                'output_path': output_path,
                'stdout': result.stdout
            }
        else:
            logger.error(f"Task {self.request.id} failed: {result.stderr}")
            return {
                'status': 'failed',
                'error': result.stderr
            }

    except subprocess.TimeoutExpired:
        logger.error(f"Task {self.request.id} timed out")
        return {
            'status': 'failed',
            'error': 'Generation timed out'
        }

    except Exception as e:
        logger.exception(f"Task {self.request.id} error: {e}")
        return {
            'status': 'failed',
            'error': str(e)
        }

@celery.task(name='tasks.batch_generate')
def batch_generate_task(batch_id, set_name, items, config):
    """
    Batch generation task - spawns subtasks for each item.

    Args:
        batch_id: Unique batch identifier
        set_name: Name of the set being generated
        items: List of items to generate
        config: Generation configuration

    Returns:
        Dictionary with batch status
    """
    from celery import group

    # Create subtasks for each item
    job = group(
        generate_image_task.s({
            **config,
            'prompt': item['prompt'],
            'output': item['output_path'],
            'batch_item_name': item['name']
        })
        for item in items
    )

    # Execute batch
    result = job.apply_async()

    return {
        'status': 'submitted',
        'batch_id': batch_id,
        'total_items': len(items),
        'group_id': result.id
    }

# server/api.py - UPDATE to use Celery

from server.tasks import generate_image_task, batch_generate_task
from server.celery_app import celery as celery_app

# REMOVE old queue and worker
# job_queue = queue.Queue()
# current_job = None
# job_history = []

@app.route("/api/generate", methods=["POST"])
@require_auth
@limiter.limit("10 per minute")
def generate():
    """Submit single image generation job"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Request body required"}), 400

        # Validate parameters
        params = validate_generation_params(data)

        # Submit to Celery
        task = generate_image_task.delay(params)

        logger.info(f"Submitted generation task {task.id}")

        return jsonify({
            "success": True,
            "job_id": task.id,
            "status": "queued",
            "message": "Generation job submitted"
        }), 201

    except ValidationError as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        logger.error(f"Error submitting job: {e}", exc_info=True)
        return jsonify({"error": "Failed to submit job"}), 500

@app.route("/api/jobs/<task_id>", methods=["GET"])
@require_auth
def get_job_status(task_id):
    """Get job status"""
    try:
        task = celery_app.AsyncResult(task_id)

        response = {
            "id": task_id,
            "status": task.state,
        }

        if task.state == 'PENDING':
            response['message'] = 'Job is queued'
        elif task.state == 'STARTED':
            response['message'] = 'Job is running'
        elif task.state == 'PROGRESS':
            response['message'] = task.info.get('status', 'Processing...')
        elif task.state == 'SUCCESS':
            result = task.result
            response['result'] = result
            response['output_path'] = result.get('output_path')
        elif task.state == 'FAILURE':
            response['error'] = str(task.info)

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error fetching job status: {e}")
        return jsonify({"error": "Failed to fetch job status"}), 500

@app.route("/api/jobs/<task_id>", methods=["DELETE"])
@require_auth
def cancel_job(task_id):
    """Cancel a running job"""
    try:
        celery_app.control.revoke(task_id, terminate=True, signal='SIGKILL')

        logger.info(f"Job {task_id} cancelled")

        return jsonify({
            "success": True,
            "message": "Job cancelled"
        })

    except Exception as e:
        logger.error(f"Error cancelling job: {e}")
        return jsonify({"error": "Failed to cancel job"}), 500

@app.route("/api/jobs", methods=["GET"])
@require_auth
def list_jobs():
    """List recent jobs"""
    try:
        # Get active tasks
        inspector = celery_app.control.inspect()
        active = inspector.active()
        reserved = inspector.reserved()

        # Combine all tasks
        all_tasks = []

        if active:
            for worker, tasks in active.items():
                all_tasks.extend(tasks)

        if reserved:
            for worker, tasks in reserved.items():
                all_tasks.extend(tasks)

        return jsonify({
            "active_jobs": len(all_tasks),
            "jobs": all_tasks[:50]  # Limit to 50 most recent
        })

    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        return jsonify({"error": "Failed to list jobs"}), 500
```

**Benefits:**
- ✅ Job persistence (survive restarts)
- ✅ Proper cancellation support
- ✅ Task timeouts
- ✅ Worker auto-restart for memory cleanup
- ✅ Web UI for monitoring (Flower)
- ✅ Scalable to multiple workers

#### 2.2 Job Database (Priority: MEDIUM)

**Estimated Time:** 10 hours

**Why:** Track job history, enable analytics, user job tracking

```python
# server/models.py (NEW FILE)
"""Database models for job persistence"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Job(db.Model):
    """Job model for tracking generation requests"""
    __tablename__ = 'jobs'

    id = db.Column(db.String(36), primary_key=True)  # Celery task ID
    user_email = db.Column(db.String(255), nullable=False, index=True)

    # Job details
    prompt = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)

    # Parameters (stored as JSON)
    parameters = db.Column(db.JSON)

    # Results
    output_path = db.Column(db.String(500))
    error_message = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    # Metadata
    batch_id = db.Column(db.String(100), index=True)
    generation_time_seconds = db.Column(db.Float)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_email': self.user_email,
            'prompt': self.prompt,
            'status': self.status,
            'parameters': self.parameters,
            'output_path': self.output_path,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'batch_id': self.batch_id,
            'generation_time_seconds': self.generation_time_seconds
        }

class Batch(db.Model):
    """Batch generation tracking"""
    __tablename__ = 'batches'

    id = db.Column(db.String(100), primary_key=True)
    user_email = db.Column(db.String(255), nullable=False, index=True)
    set_name = db.Column(db.String(100), nullable=False)

    total_items = db.Column(db.Integer, nullable=False)
    completed_items = db.Column(db.Integer, default=0)
    failed_items = db.Column(db.Integer, default=0)

    status = db.Column(db.String(20), default='running', index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = db.Column(db.DateTime)

    # Configuration
    config = db.Column(db.JSON)

    def to_dict(self):
        return {
            'id': self.id,
            'user_email': self.user_email,
            'set_name': self.set_name,
            'total_items': self.total_items,
            'completed_items': self.completed_items,
            'failed_items': self.failed_items,
            'status': self.status,
            'progress_percentage': (self.completed_items / self.total_items * 100) if self.total_items > 0 else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

# server/api.py - Initialize database

from server.models import db, Job, Batch

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'sqlite:///imagineer.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()

# UPDATE generate endpoint to record jobs
@app.route("/api/generate", methods=["POST"])
@require_auth
@limiter.limit("10 per minute")
def generate():
    try:
        data = request.json
        params = validate_generation_params(data)

        # Submit to Celery
        task = generate_image_task.delay(params)

        # Record in database
        job = Job(
            id=task.id,
            user_email=current_user.email,
            prompt=params['prompt'],
            status='pending',
            parameters=params
        )
        db.session.add(job)
        db.session.commit()

        logger.info(f"Created job {task.id} for user {current_user.email}")

        return jsonify({
            "success": True,
            "job_id": task.id,
            "status": "queued"
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating job: {e}", exc_info=True)
        return jsonify({"error": "Failed to submit job"}), 500

# ADD job update callback
@celery.task(name='tasks.update_job_status')
def update_job_status(task_id, status, **kwargs):
    """Update job status in database"""
    from server.api import app
    from server.models import db, Job

    with app.app_context():
        job = Job.query.get(task_id)
        if job:
            job.status = status

            if status == 'started':
                job.started_at = datetime.utcnow()
            elif status in ['completed', 'failed']:
                job.completed_at = datetime.utcnow()
                if job.started_at:
                    job.generation_time_seconds = (
                        job.completed_at - job.started_at
                    ).total_seconds()

            if 'output_path' in kwargs:
                job.output_path = kwargs['output_path']

            if 'error_message' in kwargs:
                job.error_message = kwargs['error_message']

            db.session.commit()
```

#### 2.3 Rate Limiting (Priority: MEDIUM)

**Estimated Time:** 4 hours

```python
# requirements.txt - ADD
flask-limiter>=3.5.0

# server/api.py - ADD rate limiting

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize limiter
def get_user_identifier():
    """Use email for authenticated users, IP for others"""
    if current_user and current_user.is_authenticated:
        return current_user.email
    return get_remote_address()

limiter = Limiter(
    app=app,
    key_func=get_user_identifier,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.environ.get("REDIS_URL", "redis://localhost:6379/1"),
    strategy="fixed-window"
)

# Apply specific limits
@app.route("/api/generate", methods=["POST"])
@require_auth
@limiter.limit("10 per minute")  # 10 single generations per minute
def generate():
    ...

@app.route("/api/generate/batch", methods=["POST"])
@require_auth
@limiter.limit("3 per hour")  # 3 batch generations per hour
def generate_batch():
    ...

# Exempt admins from rate limits
@limiter.request_filter
def exempt_admins():
    """Admins are not rate limited"""
    return (current_user and
            current_user.is_authenticated and
            hasattr(current_user, 'role') and
            current_user.role == 'admin')

# Add queue size limits
MAX_QUEUE_SIZE = 100
MAX_JOBS_PER_USER = 10

# In generate() function
@app.route("/api/generate", methods=["POST"])
@require_auth
@limiter.limit("10 per minute")
def generate():
    # Check user's active job count
    active_jobs = Job.query.filter_by(
        user_email=current_user.email,
        status__in=['pending', 'started']
    ).count()

    if active_jobs >= MAX_JOBS_PER_USER:
        return jsonify({
            "error": f"You have {active_jobs} active jobs. Maximum is {MAX_JOBS_PER_USER}."
        }), 429

    # Rest of implementation...
```

#### 2.4 Monitoring & Observability (Priority: MEDIUM)

**Estimated Time:** 8 hours

```python
# requirements.txt - ADD
prometheus-client>=0.19.0
sentry-sdk[flask]>=1.40.0  # Optional but recommended

# server/metrics.py (NEW FILE)
"""Prometheus metrics for monitoring"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest
from flask import Response
import time

# Metrics
job_submissions = Counter(
    'imagineer_job_submissions_total',
    'Total number of job submissions',
    ['status', 'user_role']
)

job_duration = Histogram(
    'imagineer_job_duration_seconds',
    'Job execution duration in seconds',
    ['status']
)

active_jobs = Gauge(
    'imagineer_active_jobs',
    'Number of currently active jobs'
)

queue_size = Gauge(
    'imagineer_queue_size',
    'Number of jobs in queue'
)

generation_errors = Counter(
    'imagineer_generation_errors_total',
    'Total generation errors',
    ['error_type']
)

# server/api.py - ADD metrics endpoint

from server.metrics import (
    job_submissions,
    job_duration,
    active_jobs,
    queue_size,
    generation_errors
)

@app.route("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), mimetype='text/plain')

# UPDATE generate endpoint to track metrics
@app.route("/api/generate", methods=["POST"])
@require_auth
@limiter.limit("10 per minute")
def generate():
    try:
        # ... validation code ...

        task = generate_image_task.delay(params)

        # Record job submission
        job_submissions.labels(
            status='submitted',
            user_role=current_user.role
        ).inc()

        # Update active jobs gauge
        active_count = Job.query.filter(
            Job.status.in_(['pending', 'started'])
        ).count()
        active_jobs.set(active_count)

        # ... rest of code ...

    except ValidationError as e:
        generation_errors.labels(error_type='validation').inc()
        raise
    except Exception as e:
        generation_errors.labels(error_type='internal').inc()
        raise

# ADD Sentry integration (optional)
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

if os.environ.get('SENTRY_DSN'):
    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN'),
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.1,  # 10% of transactions
        environment=os.environ.get('FLASK_ENV', 'development')
    )
```

```yaml
# docker-compose.yml - ADD Prometheus
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    networks:
      - imagineer-network

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
    depends_on:
      - prometheus
    networks:
      - imagineer-network

volumes:
  prometheus-data:
  grafana-data:
```

```yaml
# prometheus.yml (NEW FILE)
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'imagineer-api'
    static_configs:
      - targets: ['api:10050']

  - job_name: 'celery'
    static_configs:
      - targets: ['flower:5555']
```

#### 2.5 Code Refactoring (Priority: MEDIUM)

**Estimated Time:** 12 hours

**Goal:** Break up monolithic server/api.py (1572 lines) into modules

```
server/
├── __init__.py
├── api.py              # Flask app init only (~100 lines)
├── celery_app.py       # Celery configuration
├── tasks.py            # Celery tasks
├── models.py           # Database models
├── auth.py             # Authentication (exists)
├── validators.py       # Input validation
├── metrics.py          # Prometheus metrics
├── logging_config.py   # Logging configuration
├── routes/
│   ├── __init__.py
│   ├── auth.py         # Auth routes (/auth/*)
│   ├── config.py       # Config routes (/api/config*)
│   ├── generate.py     # Generation routes (/api/generate*)
│   ├── jobs.py         # Job routes (/api/jobs*)
│   ├── batches.py      # Batch routes (/api/batches*)
│   ├── sets.py         # Set routes (/api/sets*)
│   ├── loras.py        # LoRA routes (/api/loras*)
│   └── outputs.py      # Output serving (/api/outputs*)
├── services/
│   ├── __init__.py
│   ├── set_manager.py      # Set loading and discovery
│   ├── lora_manager.py     # LoRA discovery and management
│   └── config_manager.py   # Config file operations
└── utils/
    ├── __init__.py
    └── path_utils.py       # Path validation utilities
```

**Example Refactoring:**

```python
# server/api.py (REFACTORED - ~100 lines)
"""Flask application initialization"""

from flask import Flask
from flask_cors import CORS
from server.models import db
from server.auth import init_auth
from server.celery_app import celery
from server.logging_config import configure_logging
import os

def create_app():
    """Create and configure Flask app"""
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL',
        'sqlite:///imagineer.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # CORS
    allowed_origins = os.environ.get('ALLOWED_ORIGINS', '').split(',')
    if not allowed_origins or allowed_origins == ['']:
        allowed_origins = [
            'http://localhost:3000',
            'http://localhost:5173'
        ]

    CORS(app,
         resources={r"/api/*": {"origins": allowed_origins}},
         supports_credentials=True)

    # Initialize extensions
    db.init_app(app)
    init_auth(app)
    configure_logging(app)

    # Register blueprints
    from server.routes import (
        auth_bp, config_bp, generate_bp, jobs_bp,
        batches_bp, sets_bp, loras_bp, outputs_bp
    )

    app.register_blueprint(auth_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(generate_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(batches_bp)
    app.register_blueprint(sets_bp)
    app.register_blueprint(loras_bp)
    app.register_blueprint(outputs_bp)

    # Create tables
    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("FLASK_RUN_PORT", 10050))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host="0.0.0.0", port=port, debug=debug)
```

```python
# server/routes/generate.py (NEW FILE)
"""Generation route handlers"""

from flask import Blueprint, request, jsonify
from server.auth import require_auth
from server.validators import validate_generation_params, ValidationError
from server.tasks import generate_image_task
from server.models import db, Job
from server.metrics import job_submissions, active_jobs
import logging

generate_bp = Blueprint('generate', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)

@generate_bp.route("/generate", methods=["POST"])
@require_auth
def generate():
    """Submit single image generation job"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Request body required"}), 400

        # Validate parameters
        params = validate_generation_params(data)

        # Submit to Celery
        task = generate_image_task.delay(params)

        # Record in database
        job = Job(
            id=task.id,
            user_email=current_user.email,
            prompt=params['prompt'],
            status='pending',
            parameters=params
        )
        db.session.add(job)
        db.session.commit()

        # Metrics
        job_submissions.labels(
            status='submitted',
            user_role=current_user.role
        ).inc()

        logger.info(f"Created job {task.id}")

        return jsonify({
            "success": True,
            "job_id": task.id,
            "status": "queued"
        }), 201

    except ValidationError as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error submitting job: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

# ... other generation endpoints
```

**Phase 2 Deliverables:**
- ✅ Redis-backed persistent job queue
- ✅ Celery workers for async processing
- ✅ Job database with history tracking
- ✅ Rate limiting on all endpoints
- ✅ Prometheus metrics + Grafana dashboards
- ✅ Modular code structure (routes, services, models)

---

### Phase 3: Performance & ML Pipeline (Week 5-6, ~45 hours)

**Goal:** Optimize generation throughput, support advanced ML features

#### 3.1 GPU Resource Management (Priority: HIGH)

**Estimated Time:** 12 hours

**Current Issues:**
- Model loaded fresh for each generation (slow startup)
- No model caching between jobs
- Memory not explicitly released

**Solution: Model Server Pattern**

```python
# server/model_server.py (NEW FILE)
"""Persistent model server for fast inference"""

import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from peft import PeftModel
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import threading
import time

logger = logging.getLogger(__name__)

class ModelServer:
    """
    Persistent model server that keeps model in memory.
    Supports hot-swapping LoRAs without reloading base model.
    """

    def __init__(self, config: Dict):
        self.config = config
        self.pipe = None
        self.loaded_loras = []
        self.lock = threading.Lock()
        self.last_used = time.time()

        # Load base model on initialization
        self._load_base_model()

    def _load_base_model(self):
        """Load base Stable Diffusion model"""
        logger.info("Loading base SD 1.5 model...")

        model_id = self.config["model"]["base"]
        cache_dir = self.config["model"].get("cache_dir")

        self.pipe = StableDiffusionPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            cache_dir=cache_dir,
            safety_checker=None  # Disable for performance
        )

        # Scheduler
        self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(
            self.pipe.scheduler.config
        )

        # Move to device
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.pipe = self.pipe.to(device)

        # Enable attention slicing for memory efficiency
        if torch.cuda.is_available():
            self.pipe.enable_attention_slicing()

        logger.info(f"Base model loaded on {device}")

    def load_loras(self, lora_configs: List[Tuple[str, float]]):
        """
        Load LoRAs into the pipeline.

        Args:
            lora_configs: List of (lora_path, weight) tuples
        """
        with self.lock:
            # Unload existing LoRAs if different
            if lora_configs != self.loaded_loras:
                self._unload_loras()

                # Load new LoRAs
                for lora_path, weight in lora_configs:
                    logger.info(f"Loading LoRA: {lora_path} (weight={weight})")
                    self.pipe.load_lora_weights(lora_path, weight_name=Path(lora_path).name)
                    self.pipe.fuse_lora(weight)

                self.loaded_loras = lora_configs

    def _unload_loras(self):
        """Unload currently loaded LoRAs"""
        if self.loaded_loras:
            logger.info("Unloading LoRAs...")
            self.pipe.unfuse_lora()
            self.loaded_loras = []

    def generate(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 512,
        height: int = 512,
        steps: int = 25,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None
    ) -> torch.Tensor:
        """
        Generate image with current model configuration.

        Returns:
            Generated image tensor
        """
        with self.lock:
            self.last_used = time.time()

            # Set seed if provided
            generator = None
            if seed is not None:
                generator = torch.Generator(device=self.pipe.device).manual_seed(seed)

            # Generate
            logger.info(f"Generating: {prompt[:50]}...")

            result = self.pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=steps,
                guidance_scale=guidance_scale,
                generator=generator
            )

            return result.images[0]

    def cleanup(self):
        """Release GPU memory"""
        with self.lock:
            if self.pipe:
                self._unload_loras()
                del self.pipe
                self.pipe = None

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()

                logger.info("Model server cleaned up")

    def is_idle(self, timeout_seconds: int = 300) -> bool:
        """Check if server has been idle for too long"""
        return (time.time() - self.last_used) > timeout_seconds

# Global model server instance
_model_server = None
_server_lock = threading.Lock()

def get_model_server(config: Dict) -> ModelServer:
    """Get or create global model server instance"""
    global _model_server

    with _server_lock:
        if _model_server is None:
            _model_server = ModelServer(config)
        return _model_server

def cleanup_model_server():
    """Cleanup global model server"""
    global _model_server

    with _server_lock:
        if _model_server:
            _model_server.cleanup()
            _model_server = None

# server/tasks.py - UPDATE to use model server

from server.model_server import get_model_server, cleanup_model_server

@celery.task(bind=True, name='tasks.generate_image_fast')
def generate_image_fast(self, job_data):
    """Fast image generation using persistent model server"""
    try:
        from server.api import app

        with app.app_context():
            config = load_config()

            # Get model server
            model_server = get_model_server(config)

            # Load LoRAs if specified
            lora_configs = []
            if 'lora_paths' in job_data and job_data['lora_paths']:
                lora_weights = job_data.get('lora_weights', [0.6] * len(job_data['lora_paths']))
                lora_configs = list(zip(job_data['lora_paths'], lora_weights))

            if lora_configs:
                model_server.load_loras(lora_configs)

            # Generate
            image = model_server.generate(
                prompt=job_data['prompt'],
                negative_prompt=job_data.get('negative_prompt'),
                width=job_data.get('width', 512),
                height=job_data.get('height', 512),
                steps=job_data.get('steps', 25),
                guidance_scale=job_data.get('guidance_scale', 7.5),
                seed=job_data.get('seed')
            )

            # Save image
            output_path = Path(job_data.get('output', 'output.png'))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(output_path)

            # Save metadata
            metadata = {
                'prompt': job_data['prompt'],
                'parameters': {
                    k: v for k, v in job_data.items()
                    if k not in ['prompt', 'output']
                },
                'generated_at': datetime.now().isoformat()
            }

            metadata_path = output_path.with_suffix('.json')
            metadata_path.write_text(json.dumps(metadata, indent=2))

            logger.info(f"Generated: {output_path}")

            return {
                'status': 'completed',
                'output_path': str(output_path)
            }

    except Exception as e:
        logger.exception(f"Generation error: {e}")
        return {
            'status': 'failed',
            'error': str(e)
        }

# ADD worker lifecycle hooks for cleanup
from celery.signals import worker_shutdown

@worker_shutdown.connect
def cleanup_on_shutdown(**kwargs):
    """Cleanup model server on worker shutdown"""
    logger.info("Worker shutting down, cleaning up model server...")
    cleanup_model_server()
```

**Benefits:**
- ✅ 5-10x faster generation (no model reload)
- ✅ Hot-swap LoRAs without reloading base
- ✅ Proper memory management
- ✅ Idle timeout for cleanup

#### 3.2 Batch Processing Optimization (Priority: HIGH)

**Estimated Time:** 10 hours

**Current Issue:** Batch items processed sequentially

**Solution:** Parallel batch processing with concurrency limits

```python
# server/tasks.py - OPTIMIZE batch processing

from celery import group, chord
from server.celery_app import celery

@celery.task(bind=True, name='tasks.batch_generate_optimized')
def batch_generate_optimized(self, batch_id, set_name, items, config):
    """
    Optimized batch generation with parallel processing.

    Args:
        batch_id: Unique batch identifier
        set_name: Name of set being generated
        items: List of items to generate
        config: Generation configuration
    """
    from server.api import app
    from server.models import db, Batch

    with app.app_context():
        # Create batch record
        batch = Batch(
            id=batch_id,
            user_email=config.get('user_email'),
            set_name=set_name,
            total_items=len(items),
            config=config
        )
        db.session.add(batch)
        db.session.commit()

    # Create parallel job group
    # Process items in chunks to avoid overwhelming GPU
    CHUNK_SIZE = 4  # Process 4 images concurrently

    job_groups = []
    for i in range(0, len(items), CHUNK_SIZE):
        chunk = items[i:i+CHUNK_SIZE]

        job_group = group(
            generate_image_fast.s({
                **config,
                'prompt': item['prompt'],
                'output': item['output_path'],
                'batch_item_name': item['name'],
                'batch_id': batch_id
            })
            for item in chunk
        )

        job_groups.append(job_group)

    # Chain groups sequentially (4 parallel, then next 4, etc.)
    from celery import chain

    pipeline = chain(
        *[group_job | batch_chunk_completed.s(batch_id)
          for group_job in job_groups]
    )

    result = pipeline.apply_async()

    return {
        'status': 'submitted',
        'batch_id': batch_id,
        'total_items': len(items),
        'pipeline_id': result.id
    }

@celery.task(name='tasks.batch_chunk_completed')
def batch_chunk_completed(results, batch_id):
    """Callback when a chunk of batch completes"""
    from server.api import app
    from server.models import db, Batch

    with app.app_context():
        batch = Batch.query.get(batch_id)
        if batch:
            # Count completed/failed
            completed = sum(1 for r in results if r.get('status') == 'completed')
            failed = sum(1 for r in results if r.get('status') == 'failed')

            batch.completed_items += completed
            batch.failed_items += failed

            # Check if batch is complete
            if (batch.completed_items + batch.failed_items) >= batch.total_items:
                batch.status = 'completed' if batch.failed_items == 0 else 'partial'
                batch.completed_at = datetime.utcnow()

            db.session.commit()

            logger.info(
                f"Batch {batch_id} progress: "
                f"{batch.completed_items}/{batch.total_items} completed, "
                f"{batch.failed_items} failed"
            )

    return results
```

#### 3.3 Model Versioning & Management (Priority: MEDIUM)

**Estimated Time:** 10 hours

**For your advanced ML roadmap:** Training, fine-tuning, model versioning

```python
# server/models.py - ADD model tracking

class ModelVersion(db.Model):
    """Track different model versions and LoRAs"""
    __tablename__ = 'model_versions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    type = db.Column(db.String(20), nullable=False)  # 'base', 'lora', 'checkpoint'

    # File information
    file_path = db.Column(db.String(500), nullable=False)
    file_size_bytes = db.Column(db.BigInteger)
    checksum = db.Column(db.String(64))  # SHA256

    # Metadata
    description = db.Column(db.Text)
    base_model = db.Column(db.String(100))  # For LoRAs, which base model
    training_config = db.Column(db.JSON)  # Training hyperparameters

    # Versioning
    version = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True, index=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.String(255))

    # Performance metrics (optional)
    metrics = db.Column(db.JSON)  # Loss, FID score, etc.

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'file_path': self.file_path,
            'file_size_mb': round(self.file_size_bytes / 1024 / 1024, 2) if self.file_size_bytes else None,
            'version': self.version,
            'is_active': self.is_active,
            'base_model': self.base_model,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'metrics': self.metrics
        }

class TrainingRun(db.Model):
    """Track LoRA training runs"""
    __tablename__ = 'training_runs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_email = db.Column(db.String(255), nullable=False, index=True)

    # Configuration
    base_model = db.Column(db.String(100), nullable=False)
    dataset_path = db.Column(db.String(500))
    config = db.Column(db.JSON)  # Training hyperparameters

    # Status
    status = db.Column(db.String(20), default='pending', index=True)
    progress_percentage = db.Column(db.Float, default=0)

    # Results
    output_model_id = db.Column(db.Integer, db.ForeignKey('model_versions.id'))
    output_model = db.relationship('ModelVersion', backref='training_run')

    training_logs = db.Column(db.Text)
    metrics = db.Column(db.JSON)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'user_email': self.user_email,
            'base_model': self.base_model,
            'dataset_path': self.dataset_path,
            'status': self.status,
            'progress_percentage': self.progress_percentage,
            'config': self.config,
            'output_model': self.output_model.to_dict() if self.output_model else None,
            'metrics': self.metrics,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

# server/routes/models.py (NEW FILE)
"""Model management endpoints"""

from flask import Blueprint, request, jsonify
from server.auth import require_auth, require_role, ROLE_EDITOR, ROLE_ADMIN
from server.models import db, ModelVersion, TrainingRun
from pathlib import Path
import hashlib

models_bp = Blueprint('models', __name__, url_prefix='/api/models')

@models_bp.route("", methods=["GET"])
@require_auth
def list_models():
    """List all available models"""
    model_type = request.args.get('type')  # Filter by type
    active_only = request.args.get('active', 'true').lower() == 'true'

    query = ModelVersion.query

    if model_type:
        query = query.filter_by(type=model_type)

    if active_only:
        query = query.filter_by(is_active=True)

    models = query.order_by(ModelVersion.created_at.desc()).all()

    return jsonify({
        'models': [m.to_dict() for m in models]
    })

@models_bp.route("/<int:model_id>", methods=["GET"])
@require_auth
def get_model(model_id):
    """Get model details"""
    model = ModelVersion.query.get_or_404(model_id)
    return jsonify(model.to_dict())

@models_bp.route("", methods=["POST"])
@require_role(ROLE_EDITOR)
def register_model():
    """Register a new model/LoRA"""
    data = request.json

    # Validate file exists
    file_path = Path(data['file_path'])
    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404

    # Calculate checksum
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    checksum = sha256.hexdigest()

    # Create model record
    model = ModelVersion(
        name=data['name'],
        type=data['type'],
        file_path=str(file_path),
        file_size_bytes=file_path.stat().st_size,
        checksum=checksum,
        description=data.get('description'),
        base_model=data.get('base_model'),
        version=data.get('version', '1.0.0'),
        created_by=current_user.email,
        training_config=data.get('training_config'),
        metrics=data.get('metrics')
    )

    db.session.add(model)
    db.session.commit()

    return jsonify(model.to_dict()), 201

@models_bp.route("/training", methods=["POST"])
@require_role(ROLE_EDITOR)
def start_training():
    """Start a LoRA training run"""
    data = request.json

    # Create training run record
    training_run = TrainingRun(
        name=data['name'],
        user_email=current_user.email,
        base_model=data['base_model'],
        dataset_path=data['dataset_path'],
        config=data.get('config', {})
    )

    db.session.add(training_run)
    db.session.commit()

    # Submit training task
    from server.tasks import train_lora_task
    task = train_lora_task.delay(training_run.id)

    return jsonify({
        'training_run_id': training_run.id,
        'task_id': task.id,
        'status': 'submitted'
    }), 201

@models_bp.route("/training/<int:run_id>", methods=["GET"])
@require_auth
def get_training_run(run_id):
    """Get training run status"""
    run = TrainingRun.query.get_or_404(run_id)

    # Check authorization - users can only see their own runs unless admin
    if run.user_email != current_user.email and current_user.role != 'admin':
        return jsonify({"error": "Access denied"}), 403

    return jsonify(run.to_dict())

# server/tasks.py - ADD training task

@celery.task(bind=True, name='tasks.train_lora')
def train_lora_task(self, training_run_id):
    """
    Execute LoRA training.

    This is a long-running task that can take hours.
    """
    from server.api import app
    from server.models import db, TrainingRun, ModelVersion
    import subprocess

    with app.app_context():
        run = TrainingRun.query.get(training_run_id)
        if not run:
            return {'status': 'failed', 'error': 'Training run not found'}

        run.status = 'running'
        run.started_at = datetime.utcnow()
        db.session.commit()

        try:
            # Build training command
            cmd = [
                'python', 'examples/train_lora.py',
                '--data-dir', run.dataset_path,
                '--output-dir', f'/mnt/speedy/imagineer/checkpoints/run_{run.id}',
                '--base-model', run.base_model
            ]

            # Add config parameters
            config = run.config or {}
            if 'steps' in config:
                cmd.extend(['--steps', str(config['steps'])])
            if 'learning_rate' in config:
                cmd.extend(['--learning-rate', str(config['learning_rate'])])
            if 'rank' in config:
                cmd.extend(['--rank', str(config['rank'])])

            # Execute training
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            # Stream output and update progress
            logs = []
            for line in process.stdout:
                logs.append(line)

                # Parse progress from output
                if 'Step' in line:
                    # Extract step number and calculate progress
                    # This depends on your training script output format
                    pass

                # Update database periodically
                if len(logs) % 10 == 0:
                    run.training_logs = '\n'.join(logs[-100:])  # Last 100 lines
                    db.session.commit()

            process.wait()

            if process.returncode == 0:
                # Training successful - register model
                output_dir = Path(f'/mnt/speedy/imagineer/checkpoints/run_{run.id}')
                lora_files = list(output_dir.glob('*.safetensors'))

                if lora_files:
                    lora_path = lora_files[0]

                    # Calculate checksum
                    sha256 = hashlib.sha256()
                    with open(lora_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(8192), b''):
                            sha256.update(chunk)

                    # Register model
                    model = ModelVersion(
                        name=run.name,
                        type='lora',
                        file_path=str(lora_path),
                        file_size_bytes=lora_path.stat().st_size,
                        checksum=sha256.hexdigest(),
                        base_model=run.base_model,
                        training_config=run.config,
                        created_by=run.user_email,
                        version='1.0.0'
                    )

                    db.session.add(model)
                    run.output_model = model

                run.status = 'completed'
                run.completed_at = datetime.utcnow()
                run.training_logs = '\n'.join(logs)
                db.session.commit()

                return {'status': 'completed', 'model_id': model.id if model else None}
            else:
                run.status = 'failed'
                run.completed_at = datetime.utcnow()
                run.training_logs = '\n'.join(logs)
                db.session.commit()

                return {'status': 'failed', 'error': 'Training failed'}

        except Exception as e:
            run.status = 'failed'
            run.completed_at = datetime.utcnow()
            run.training_logs = str(e)
            db.session.commit()

            return {'status': 'failed', 'error': str(e)}
```

#### 3.4 Frontend Performance (Priority: MEDIUM)

**Estimated Time:** 8 hours

```javascript
// web/src/App.jsx - OPTIMIZE polling

const pollJobStatus = useCallback((jobId) => {
  let retryCount = 0
  let timeoutId = null

  const checkStatus = async () => {
    try {
      const response = await fetch(`/api/jobs/${jobId}`)
      const job = await response.json()

      setJobs(prev => ({
        ...prev,
        [jobId]: job
      }))

      if (job.status === 'completed' || job.status === 'failed') {
        // Done, refresh images
        fetchImages()
        return
      }

      // Exponential backoff: 1s, 2s, 4s, 8s, max 30s
      const delay = Math.min(1000 * Math.pow(2, retryCount), 30000)
      retryCount++

      timeoutId = setTimeout(checkStatus, delay)
    } catch (error) {
      console.error('Polling error:', error)
      // Retry with exponential backoff on error too
      const delay = Math.min(1000 * Math.pow(2, retryCount), 30000)
      timeoutId = setTimeout(checkStatus, delay)
    }
  }

  checkStatus()

  // Return cleanup function
  return () => {
    if (timeoutId) {
      clearTimeout(timeoutId)
    }
  }
}, [fetchImages])

// ADD React Context for state management
// web/src/contexts/AppContext.jsx (NEW FILE)
import React, { createContext, useContext, useState, useCallback } from 'react'

const AppContext = createContext()

export function AppProvider({ children }) {
  const [config, setConfig] = useState(null)
  const [images, setImages] = useState([])
  const [batches, setBatches] = useState([])
  const [jobs, setJobs] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchConfig = useCallback(async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/config')
      const data = await response.json()
      setConfig(data)
      setError(null)
    } catch (err) {
      setError('Failed to load configuration')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

  // ... other API methods

  const value = {
    config,
    images,
    batches,
    jobs,
    loading,
    error,
    fetchConfig,
    // ... other methods
  }

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  const context = useContext(AppContext)
  if (!context) {
    throw new Error('useApp must be used within AppProvider')
  }
  return context
}

// web/src/main.jsx - Wrap app in provider
import { AppProvider } from './contexts/AppContext'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AppProvider>
      <App />
    </AppProvider>
  </React.StrictMode>
)

// web/src/services/api.js (NEW FILE) - API abstraction layer
const API_BASE = '/api'

class ApiError extends Error {
  constructor(message, status, data) {
    super(message)
    this.status = status
    this.data = data
  }
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`

  const config = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    },
    credentials: 'include'
  }

  if (options.body && typeof options.body === 'object') {
    config.body = JSON.stringify(options.body)
  }

  try {
    const response = await fetch(url, config)
    const data = await response.json()

    if (!response.ok) {
      throw new ApiError(
        data.error || 'Request failed',
        response.status,
        data
      )
    }

    return data
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    throw new ApiError('Network error', 0, null)
  }
}

export const api = {
  // Config endpoints
  config: {
    get: () => request('/config'),
    update: (data) => request('/config', { method: 'PUT', body: data })
  },

  // Generation endpoints
  generate: {
    single: (params) => request('/generate', { method: 'POST', body: params }),
    batch: (params) => request('/generate/batch', { method: 'POST', body: params })
  },

  // Job endpoints
  jobs: {
    get: (id) => request(`/jobs/${id}`),
    list: () => request('/jobs'),
    cancel: (id) => request(`/jobs/${id}`, { method: 'DELETE' })
  },

  // Batch endpoints
  batches: {
    list: () => request('/batches'),
    get: (id) => request(`/batches/${id}`)
  },

  // Set endpoints
  sets: {
    list: () => request('/sets'),
    get: (name) => request(`/sets/${name}/info`),
    updateLoras: (name, loras) => request(`/sets/${name}/loras`, {
      method: 'PUT',
      body: { loras }
    })
  },

  // LoRA endpoints
  loras: {
    list: () => request('/loras')
  },

  // Model endpoints
  models: {
    list: (type) => request(`/models${type ? `?type=${type}` : ''}`),
    get: (id) => request(`/models/${id}`),
    register: (data) => request('/models', { method: 'POST', body: data }),
    startTraining: (data) => request('/models/training', { method: 'POST', body: data }),
    getTrainingRun: (id) => request(`/models/training/${id}`)
  }
}

// web/src/components/GenerateForm.jsx - Use API layer
import { api } from '../services/api'
import { useApp } from '../contexts/AppContext'

function GenerateForm() {
  const { config, fetchImages } = useApp()

  const handleSubmit = async (e) => {
    e.preventDefault()

    try {
      const result = await api.generate.single({
        prompt: formData.prompt,
        steps: formData.steps,
        seed: formData.seed
      })

      toast.success(`Job ${result.job_id} submitted!`)

      // Start polling for status
      pollJobStatus(result.job_id)
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error(error.message)
      } else {
        toast.error('Failed to submit generation')
      }
    }
  }

  // ... rest of component
}
```

#### 3.5 Caching & CDN (Priority: LOW)

**Estimated Time:** 5 hours

```python
# For serving generated images efficiently

# requirements.txt - ADD
flask-caching>=2.1.0

# server/api.py - ADD caching

from flask_caching import Cache

cache = Cache(app, config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379/1'),
    'CACHE_DEFAULT_TIMEOUT': 300
})

# Cache config endpoint (rarely changes)
@app.route("/api/config", methods=["GET"])
@cache.cached(timeout=60)
def get_config():
    """Get configuration"""
    config = load_config()
    return jsonify(config)

# Cache LoRA list (changes infrequently)
@app.route("/api/loras", methods=["GET"])
@cache.cached(timeout=300)
def list_loras():
    """List available LoRAs"""
    # ... existing code

# For production: Use CloudFlare CDN for image serving
# Or implement signed URLs with expiration
```

**Phase 3 Deliverables:**
- ✅ Persistent model server (5-10x faster)
- ✅ Parallel batch processing
- ✅ Model versioning system
- ✅ Training run tracking
- ✅ Frontend performance optimizations
- ✅ API abstraction layer

---

### Phase 4: Production Readiness (Week 7-8, ~30 hours)

**Goal:** Polish, documentation, deployment automation

#### 4.1 Remaining Security Fixes (Priority: HIGH)

**Estimated Time:** 8 hours

See Security Audit Phase 1 for CRITICAL issues.
Phase 4 focuses on HIGH and MEDIUM severity items:

1. **Path traversal enhancements** (2 hours)
2. **HTTPS enforcement** (2 hours)
3. **Security headers (CSP, HSTS)** (2 hours)
4. **Docker security hardening** (2 hours)

```python
# server/api.py - ADD security headers

from flask_talisman import Talisman

if os.environ.get('FLASK_ENV') == 'production':
    Talisman(app,
        force_https=True,
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,
        content_security_policy={
            'default-src': "'self'",
            'script-src': ["'self'", "'unsafe-inline'", "accounts.google.com"],
            'style-src': ["'self'", "'unsafe-inline'"],
            'img-src': ["'self'", "data:", "*.googleusercontent.com"],
            'connect-src': ["'self'"],
            'frame-src': ["'none'"]
        },
        frame_options='DENY'
    )
```

```dockerfile
# Dockerfile - Security hardening
FROM python:3.12-slim

# Create non-root user
RUN useradd -m -u 1000 imagineer && \
    mkdir -p /app /mnt/speedy/imagineer && \
    chown -R imagineer:imagineer /app /mnt/speedy/imagineer

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY --chown=imagineer:imagineer . .

# Runtime user verification
RUN echo "if [ \$(id -u) -eq 0 ]; then echo 'ERROR: Running as root!'; exit 1; fi" >> /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

USER imagineer

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "server/api.py"]
```

```yaml
# docker-compose.yml - Security hardening
services:
  api:
    build: .
    user: "1000:1000"
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    read_only: true
    tmpfs:
      - /tmp
      - /app/logs
    # ... rest of config
```

#### 4.2 API Documentation (Priority: MEDIUM)

**Estimated Time:** 6 hours

```python
# requirements.txt - ADD
flask-restx>=1.3.0

# server/api_docs.py (NEW FILE)
"""OpenAPI/Swagger documentation"""

from flask_restx import Api, Resource, fields, Namespace

api = Api(
    version='1.0',
    title='Imagineer API',
    description='AI Image Generation Platform API',
    doc='/api/docs',
    prefix='/api'
)

# Define namespaces
ns_generate = Namespace('generate', description='Image generation operations')
ns_jobs = Namespace('jobs', description='Job management operations')
ns_models = Namespace('models', description='Model management operations')

api.add_namespace(ns_generate)
api.add_namespace(ns_jobs)
api.add_namespace(ns_models)

# Define models (schemas)
generate_params = api.model('GenerateParams', {
    'prompt': fields.String(required=True, description='Text prompt', example='A beautiful sunset over mountains'),
    'negative_prompt': fields.String(description='Negative prompt'),
    'steps': fields.Integer(description='Inference steps', min=1, max=150, example=25),
    'seed': fields.Integer(description='Random seed', min=0, example=42),
    'width': fields.Integer(description='Image width', example=512),
    'height': fields.Integer(description='Image height', example=768),
    'guidance_scale': fields.Float(description='Guidance scale', example=7.5),
    'lora_path': fields.String(description='Path to single LoRA'),
    'lora_weight': fields.Float(description='LoRA weight', example=0.6),
    'lora_paths': fields.List(fields.String, description='Multiple LoRA paths'),
    'lora_weights': fields.List(fields.Float, description='Multiple LoRA weights')
})

job_response = api.model('JobResponse', {
    'success': fields.Boolean(description='Request success'),
    'job_id': fields.String(description='Job identifier'),
    'status': fields.String(description='Job status', enum=['queued', 'running', 'completed', 'failed'])
})

# server/api.py - Integrate docs
from server.api_docs import api as api_docs

api_docs.init_app(app)
```

#### 4.3 Enhanced Testing (Priority: MEDIUM)

**Estimated Time:** 8 hours

```python
# tests/backend/test_integration.py (NEW FILE)
"""End-to-end integration tests"""

import pytest
import time
from server.api import app, db
from server.models import Job, Batch
from server.tasks import generate_image_fast

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()

def test_full_generation_workflow(client, mock_auth):
    """Test complete generation workflow from submission to completion"""

    # Submit generation
    response = client.post('/api/generate', json={
        'prompt': 'A test image',
        'steps': 1,  # Fast for testing
        'width': 256,
        'height': 256
    })

    assert response.status_code == 201
    data = response.json
    assert 'job_id' in data

    job_id = data['job_id']

    # Poll status until complete
    max_attempts = 60  # 1 minute max
    for _ in range(max_attempts):
        response = client.get(f'/api/jobs/{job_id}')
        status = response.json['status']

        if status in ['completed', 'failed']:
            break

        time.sleep(1)

    # Verify completion
    assert status == 'completed'
    assert 'output_path' in response.json

def test_batch_generation_workflow(client, mock_auth):
    """Test batch generation"""

    response = client.post('/api/generate/batch', json={
        'set_name': 'test_set',
        'user_theme': 'test theme'
    })

    assert response.status_code == 201
    # ... verify batch completion

def test_rate_limiting(client, mock_auth):
    """Test rate limiting enforcement"""

    # Submit 11 requests (limit is 10/minute)
    for i in range(11):
        response = client.post('/api/generate', json={
            'prompt': f'Test {i}'
        })

        if i < 10:
            assert response.status_code == 201
        else:
            assert response.status_code == 429  # Rate limited
```

#### 4.4 Deployment Automation (Priority: MEDIUM)

**Estimated Time:** 8 hours

```yaml
# .github/workflows/deploy-production.yml (NEW FILE)
name: Deploy to Production

on:
  push:
    branches:
      - main
    tags:
      - 'v*'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run tests
        run: |
          pytest tests/backend/ --cov=server --cov-report=xml

      - name: Check coverage threshold
        run: |
          coverage report --fail-under=80

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run security scan
        run: |
          pip install safety bandit
          safety check --json
          bandit -r server/ -f json

  deploy:
    needs: [test, security-scan]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v3

      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          script: |
            cd /opt/imagineer
            git pull origin main
            docker-compose down
            docker-compose build
            docker-compose up -d

            # Wait for health check
            timeout 60 bash -c 'until curl -f http://localhost:10050/api/health; do sleep 2; done'

# Makefile (NEW FILE) - Development commands
.PHONY: help setup test lint format clean deploy

help:
	@echo "Available commands:"
	@echo "  make setup       - Set up development environment"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run linters"
	@echo "  make format      - Format code"
	@echo "  make dev         - Start development servers"
	@echo "  make deploy      - Deploy to production"

setup:
	python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt
	. venv/bin/activate && pip install -e ".[dev]"
	cd web && npm install

test:
	pytest tests/backend/ --cov=server --cov-report=html
	cd web && npm test

lint:
	black --check server/ src/ examples/
	isort --check-only server/ src/ examples/
	flake8 server/ src/ examples/
	cd web && npm run lint

format:
	black server/ src/ examples/
	isort server/ src/ examples/
	cd web && npm run format

dev:
	@echo "Starting Redis..."
	docker-compose up -d redis
	@echo "Starting API server..."
	. venv/bin/activate && python server/api.py &
	@echo "Starting Celery worker..."
	. venv/bin/activate && celery -A server.celery_app worker --loglevel=info &
	@echo "Starting frontend..."
	cd web && npm run dev

deploy:
	@echo "Deploying to production..."
	git push origin main
	@echo "Deployment triggered via GitHub Actions"
```

**Phase 4 Deliverables:**
- ✅ All HIGH security issues resolved
- ✅ OpenAPI/Swagger documentation
- ✅ Integration test suite
- ✅ Automated deployment pipeline
- ✅ Production-ready Docker configuration

---

## Summary & Timeline

### Effort Summary

| Phase | Focus | Estimated Hours | Priority |
|-------|-------|----------------|----------|
| Phase 1 | Critical Security & Foundation | 40 | CRITICAL |
| Phase 2 | Queue Reliability & Architecture | 50 | HIGH |
| Phase 3 | Performance & ML Pipeline | 45 | HIGH |
| Phase 4 | Production Readiness | 30 | MEDIUM |
| **TOTAL** | **Complete Transformation** | **165 hours** | **~4-5 weeks** |

### Prioritized Quick Wins (Week 1)

If you need immediate impact, tackle these first:

1. **Security fixes** (12 hours) - CRITICAL
2. **Basic testing** (8 hours) - Prevent regressions
3. **Structured logging** (6 hours) - Debuggability
4. **Redis-backed queue** (16 hours) - Reliability
5. **Input validation** (6 hours) - Code quality

**Total: 48 hours (1 week sprint) - Addresses your top 3 pain points**

### Success Metrics

After full implementation, expect:

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Security Risk | HIGH | LOW | 90% vulnerability reduction |
| Test Coverage | 25% | 80%+ | 3.2x increase |
| Job Reliability | 0% (lost on restart) | 100% | Persistent queue |
| Generation Speed | 25-30s | 3-5s | 5-10x faster |
| Code Maintainability | 68/100 | 85/100 | 25% improvement |
| Production Readiness | 40% | 95% | Production-grade |

---

## Next Steps

1. **Review this plan** and adjust priorities based on your timeline
2. **Set up Phase 1 environment** (create `.env.production`, generate secrets)
3. **Begin with security fixes** - Non-negotiable for any deployment
4. **Implement testing alongside features** - Don't skip tests!
5. **Weekly checkpoints** - Review progress, adjust priorities

Would you like me to:
1. Create detailed implementation guides for specific phases?
2. Set up the initial infrastructure (Redis, database, etc.)?
3. Start with Phase 1 security fixes immediately?
4. Generate code for specific components?

Let me know which direction you'd like to take, and I'll help you get started!
