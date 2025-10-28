# Claude CLI Migration Plan

## Overview

Migrate from Anthropic API to Claude CLI for AI image labeling. Each labeling job runs in an ephemeral Docker container to avoid context collisions and ensure clean state.

## Current Architecture

**File:** `server/services/labeling.py`
- Uses Anthropic Python SDK
- Base64 encodes images and sends via API
- Returns structured responses (description, NSFW rating, tags)
- Called from Celery tasks in `server/tasks/labeling.py`

## Target Architecture

```
Celery Task → Docker Container (Claude CLI) → Parse Output
     ↓              ↓                              ↓
  Mount         Read Image                   Return Results
  Volume        Run Prompt
                Exit Container
```

### Key Changes

1. **Replace API calls with subprocess/Docker commands**
2. **Mount image directory as read-only volume**
3. **Use Claude CLI's autonomous mode (`--dangerously-skip-permissions`)**
4. **Parse CLI output instead of API JSON**
5. **Auto-cleanup containers after each run**

## Implementation Plan

### Phase 1: Research & Setup

#### 1.1 Verify Claude CLI Capabilities

```bash
# Test Claude CLI installation
claude --version

# Test autonomous mode
claude --dangerously-skip-permissions "Describe this image" --image test.png

# Check available flags
claude --help
```

**Key flags to investigate:**
- `--dangerously-skip-permissions` - Run without prompts
- `--image <path>` - Image file input
- `--model <model>` - Model selection
- `--max-tokens <n>` - Response length limit
- `--json` - JSON output (if available)

#### 1.2 Create Base Docker Image

**File:** `docker/claude-cli/Dockerfile`

```dockerfile
FROM node:20-slim

# Install Claude CLI
RUN npm install -g @anthropic-ai/claude-code-cli

# Create working directory
WORKDIR /workspace

# Set API key at runtime via environment variable
ENV ANTHROPIC_API_KEY=""

# Default command
CMD ["claude", "--version"]
```

**Build:**
```bash
docker build -t imagineer-claude-cli:latest -f docker/claude-cli/Dockerfile .
```

### Phase 2: Core Service Refactor

#### 2.1 Create Docker-based Labeling Service

**File:** `server/services/labeling_cli.py`

```python
"""
AI-powered image labeling using Claude CLI in Docker
"""

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ClaudeCliLabeler:
    """
    Runs Claude CLI in ephemeral Docker containers for image labeling
    """

    DOCKER_IMAGE = "imagineer-claude-cli:latest"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY required")

    def label_image(
        self,
        image_path: str,
        prompt_type: str = "default",
        timeout: int = 120
    ) -> Dict[str, Any]:
        """
        Label image using Claude CLI in Docker container

        Args:
            image_path: Absolute path to image file
            prompt_type: Type of labeling prompt to use
            timeout: Max seconds for Docker execution

        Returns:
            Dict with labeling results or error
        """
        image_path = Path(image_path).resolve()

        if not image_path.exists():
            return {"status": "error", "message": f"Image not found: {image_path}"}

        # Get prompt template
        prompt = self._get_prompt(prompt_type)

        # Create prompt file in temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            prompt_file = Path(tmpdir) / "prompt.txt"
            prompt_file.write_text(prompt)

            # Build Docker command
            docker_cmd = [
                "docker", "run",
                "--rm",  # Remove container after exit
                "--read-only",  # Read-only filesystem
                "--tmpfs", "/tmp",  # Writable temp directory
                "-v", f"{image_path.parent}:/images:ro",  # Mount image dir read-only
                "-v", f"{tmpdir}:/prompts:ro",  # Mount prompt file
                "-e", f"ANTHROPIC_API_KEY={self.api_key}",
                "--network", "host",  # For API access
                self.DOCKER_IMAGE,
                "claude",
                "--dangerously-skip-permissions",  # Autonomous mode
                "--model", "claude-3-5-sonnet-20241022",
                "--max-tokens", "1024",
                "--image", f"/images/{image_path.name}",
                "$(cat /prompts/prompt.txt)"
            ]

            try:
                logger.info(f"Labeling {image_path.name} with Claude CLI in Docker")

                result = subprocess.run(
                    docker_cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=True
                )

                # Parse CLI output
                return self._parse_response(result.stdout, result.stderr)

            except subprocess.TimeoutExpired:
                logger.error(f"Docker timeout after {timeout}s")
                return {"status": "error", "message": "Timeout"}

            except subprocess.CalledProcessError as e:
                logger.error(f"Docker failed: {e.stderr}")
                return {"status": "error", "message": f"Docker error: {e.stderr}"}

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return {"status": "error", "message": str(e)}

    def _get_prompt(self, prompt_type: str) -> str:
        """Get labeling prompt template"""
        prompts = {
            "default": """Analyze this image and provide:
1. A detailed description suitable for AI training (2-3 sentences)
2. NSFW rating: SAFE, SUGGESTIVE, ADULT, or EXPLICIT
3. 5-10 relevant tags (comma-separated)

Format your response EXACTLY as:
DESCRIPTION: [description]
NSFW: [rating]
TAGS: [tags]""",

            "sd_training": """You are creating training captions for Stable Diffusion 1.5.

Analyze this image and write a detailed, factual description suitable for AI training.

Format your response EXACTLY as:
CAPTION: [one detailed paragraph]
NSFW: [SAFE|SUGGESTIVE|ADULT|EXPLICIT]
TAGS: [tag1, tag2, tag3]"""
        }
        return prompts.get(prompt_type, prompts["default"])

    def _parse_response(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """
        Parse Claude CLI output

        Handles both formatted responses and free-form text
        """
        if stderr:
            logger.warning(f"Claude CLI stderr: {stderr}")

        # Parse structured output
        description = None
        nsfw_rating = "SAFE"
        tags = []

        for line in stdout.split("\n"):
            line = line.strip()
            if line.startswith("DESCRIPTION:") or line.startswith("CAPTION:"):
                description = line.split(":", 1)[1].strip()
            elif line.startswith("NSFW:"):
                nsfw_rating = line.split(":", 1)[1].strip()
            elif line.startswith("TAGS:"):
                tags_str = line.split(":", 1)[1].strip()
                tags = [tag.strip() for tag in tags_str.split(",")]

        return {
            "status": "success",
            "description": description,
            "nsfw_rating": nsfw_rating,
            "tags": tags,
            "raw_response": stdout
        }


def label_image_with_claude(image_path: str, prompt_type: str = "default") -> Dict[str, Any]:
    """
    Backward-compatible wrapper for existing code
    """
    labeler = ClaudeCliLabeler()
    return labeler.label_image(image_path, prompt_type)


def batch_label_images(image_paths, prompt_type="default", progress_callback=None):
    """
    Label multiple images in batch using Docker containers
    """
    labeler = ClaudeCliLabeler()
    results = {"total": len(image_paths), "success": 0, "failed": 0, "results": []}

    for i, image_path in enumerate(image_paths):
        if progress_callback:
            progress_callback(i + 1, len(image_paths))

        result = labeler.label_image(image_path, prompt_type)
        result["image_path"] = image_path

        if result["status"] == "success":
            results["success"] += 1
        else:
            results["failed"] += 1

        results["results"].append(result)

    return results
```

#### 2.2 Update Celery Tasks

**File:** `server/tasks/labeling.py`

```python
# Change import
from server.services.labeling_cli import label_image_with_claude
# Everything else stays the same!
```

### Phase 3: Testing & Validation

#### 3.1 Unit Tests

**File:** `tests/backend/test_cli_labeling.py`

```python
"""
Tests for Claude CLI Docker labeling
"""

import pytest
from pathlib import Path
from server.services.labeling_cli import ClaudeCliLabeler


@pytest.fixture
def test_image():
    """Fixture for test image"""
    return Path(__file__).parent.parent / "fixtures" / "test_image.jpg"


def test_docker_image_exists():
    """Verify Docker image is built"""
    import subprocess
    result = subprocess.run(
        ["docker", "images", "-q", "imagineer-claude-cli:latest"],
        capture_output=True,
        text=True
    )
    assert result.stdout.strip(), "Docker image not found. Run: docker build ..."


def test_label_image_success(test_image):
    """Test successful image labeling"""
    labeler = ClaudeCliLabeler()
    result = labeler.label_image(str(test_image))

    assert result["status"] == "success"
    assert result["description"] is not None
    assert result["nsfw_rating"] in {"SAFE", "SUGGESTIVE", "ADULT", "EXPLICIT"}
    assert isinstance(result["tags"], list)


def test_label_missing_image():
    """Test error handling for missing image"""
    labeler = ClaudeCliLabeler()
    result = labeler.label_image("/nonexistent/image.jpg")

    assert result["status"] == "error"
    assert "not found" in result["message"].lower()


@pytest.mark.slow
def test_batch_labeling(tmp_path):
    """Test batch labeling with multiple images"""
    # Create test images
    # ... (implementation)
    pass
```

#### 3.2 Integration Tests

```bash
# Test Docker build
docker build -t imagineer-claude-cli:latest -f docker/claude-cli/Dockerfile .

# Test CLI directly
docker run --rm \
  -v $(pwd)/tests/fixtures:/images:ro \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  imagineer-claude-cli:latest \
  claude --dangerously-skip-permissions \
    --image /images/test.jpg \
    "Describe this image in one sentence"

# Test via Python
python -c "
from server.services.labeling_cli import ClaudeCliLabeler
labeler = ClaudeCliLabeler()
result = labeler.label_image('tests/fixtures/test.jpg')
print(result)
"
```

### Phase 4: Deployment

#### 4.1 Docker Image Distribution

**Option A: Build on server**
```bash
# On production server
cd /path/to/imagineer
docker build -t imagineer-claude-cli:latest -f docker/claude-cli/Dockerfile .
```

**Option B: Registry (recommended)**
```bash
# Tag and push to registry
docker tag imagineer-claude-cli:latest yourregistry.com/imagineer-claude-cli:latest
docker push yourregistry.com/imagineer-claude-cli:latest

# On production
docker pull yourregistry.com/imagineer-claude-cli:latest
```

#### 4.2 Environment Setup

**`.env.production`**
```bash
# Claude CLI Configuration
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_CLI_DOCKER_IMAGE=imagineer-claude-cli:latest
CLAUDE_CLI_TIMEOUT=120

# Existing config...
```

#### 4.3 Service Update

```bash
# Stop Celery workers
sudo systemctl stop imagineer-celery

# Pull latest code
git pull origin main

# Rebuild Docker image
docker build -t imagineer-claude-cli:latest -f docker/claude-cli/Dockerfile .

# Restart services
sudo systemctl restart imagineer-celery
```

### Phase 5: Monitoring & Optimization

#### 5.1 Monitoring

**Add metrics:**
- Docker container startup time
- Labeling duration per image
- Docker cleanup success rate
- Error rates by type

**File:** `server/services/labeling_cli.py` (add instrumentation)

```python
import time

def label_image(self, ...):
    start_time = time.time()

    try:
        # ... existing code ...

        duration = time.time() - start_time
        logger.info(f"Labeled {image_path.name} in {duration:.2f}s")

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Failed after {duration:.2f}s: {e}")
```

#### 5.2 Performance Optimization

**Parallel Docker Containers:**
```python
# Use ThreadPoolExecutor for parallel labeling
from concurrent.futures import ThreadPoolExecutor

def batch_label_images_parallel(image_paths, max_workers=3, ...):
    """Label images in parallel using multiple Docker containers"""
    labeler = ClaudeCliLabeler()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(labeler.label_image, path): path
            for path in image_paths
        }
        # ... collect results ...
```

**Docker Image Caching:**
- Keep base image built and cached
- Pre-pull on server startup

#### 5.3 Resource Limits

**Add Docker resource constraints:**
```python
docker_cmd = [
    "docker", "run",
    "--rm",
    "--memory", "1g",  # Memory limit
    "--cpus", "1.0",   # CPU limit
    "--pids-limit", "100",  # Process limit
    # ... rest of command ...
]
```

## Migration Checklist

### Pre-Migration
- [ ] Install Docker on all servers
- [ ] Test Claude CLI installation in container
- [ ] Verify `--dangerously-skip-permissions` flag works
- [ ] Build and test Docker image locally
- [ ] Run unit tests
- [ ] Run integration tests with sample images

### Migration
- [ ] Create `docker/claude-cli/Dockerfile`
- [ ] Create `server/services/labeling_cli.py`
- [ ] Update `server/tasks/labeling.py` imports
- [ ] Add tests in `tests/backend/test_cli_labeling.py`
- [ ] Update `.env.example` with new config
- [ ] Update documentation

### Post-Migration
- [ ] Deploy Docker image to production
- [ ] Update environment variables
- [ ] Restart Celery workers
- [ ] Monitor first 10 labeling jobs
- [ ] Verify Docker cleanup (no orphaned containers)
- [ ] Check API key usage hasn't changed
- [ ] Performance comparison with old method

### Rollback Plan
If issues occur:
1. Revert `server/tasks/labeling.py` import
2. Restart Celery workers
3. System falls back to API-based labeling

## Benefits

### 1. **Context Isolation**
- Each labeling job runs in fresh Docker container
- No state pollution between images
- Eliminates potential context leaks

### 2. **Resource Control**
- Docker memory/CPU limits prevent resource exhaustion
- Easy to scale by adjusting max_workers

### 3. **Security**
- Read-only image mounts
- Isolated network namespace options
- No persistent state

### 4. **Debugging**
- Easy to reproduce issues with same Docker command
- CLI output easier to debug than API responses
- Can test manually without code changes

## Potential Issues & Solutions

### Issue 1: Docker Overhead
**Problem:** Container startup adds latency
**Solution:**
- Use parallel workers to offset startup time
- Consider keeping warm containers in pool

### Issue 2: CLI Flag Changes
**Problem:** Claude CLI flags might change
**Solution:**
- Pin Claude CLI version in Dockerfile
- Test before upgrading CLI version

### Issue 3: Output Parsing
**Problem:** CLI output format less structured than API
**Solution:**
- Use strict prompt formatting
- Add fallback parsers
- Validate output before returning

### Issue 4: API Key Exposure
**Problem:** API key passed via environment variable
**Solution:**
- Use Docker secrets in production
- Ensure containers are removed (--rm flag)
- Audit Docker logs for key leakage

## Cost Analysis

**API Method:**
- Direct API calls
- Pay per token

**CLI Method:**
- Still uses API under the hood
- Same cost per token
- Additional: Docker overhead (CPU/memory)

**Conclusion:** Costs similar, but better isolation and debugging.

## Timeline

- **Week 1:** Research, Docker setup, initial implementation
- **Week 2:** Testing, refinement, parallel processing
- **Week 3:** Deployment, monitoring, optimization
- **Week 4:** Rollout to production, monitoring

## Next Steps

1. **Validate Claude CLI autonomous mode** - Test `--dangerously-skip-permissions` flag
2. **Build Docker image** - Create and test Dockerfile
3. **Implement core service** - Create `labeling_cli.py`
4. **Add tests** - Unit and integration tests
5. **Deploy to staging** - Test with real workload
6. **Production rollout** - Gradual migration with monitoring
