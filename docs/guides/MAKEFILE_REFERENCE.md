# Makefile Reference

Complete reference for all Makefile commands in Imagineer.

## Quick Reference

```bash
make help           # Show all available commands
make status         # Check project status
make check          # Verify system requirements
```

## Installation Commands

### `make install`
Install Python dependencies in virtual environment.

```bash
make install
```

**What it does:**
- Creates Python virtual environment
- Upgrades pip
- Installs PyTorch with CUDA support
- Installs all requirements from requirements.txt

### `make install-web`
Install frontend Node.js dependencies.

```bash
make install-web
```

**What it does:**
- Runs `npm install` in web/ directory
- Installs React, Vite, Axios, and dev dependencies

### `make setup`
Complete installation (Python + Frontend).

```bash
make setup
```

Equivalent to: `make install && make install-web`

## Development Commands

### `make dev`
Start both API and frontend dev servers simultaneously.

```bash
make dev
```

**Runs:**
- Flask API server on http://localhost:5000
- Vite dev server on http://localhost:5173 (with API proxy)

**Use when:**
- Developing frontend
- Need hot module replacement
- Working on API + UI together

**Press Ctrl+C to stop both servers**

### `make api`
Start Flask API server only.

```bash
make api
```

**Runs:**
- Flask API on http://localhost:5000
- Serves built frontend from public/

**Use when:**
- Testing API endpoints
- Frontend already built
- Backend development only

### `make web-dev`
Start frontend dev server only.

```bash
make web-dev
```

**Runs:**
- Vite dev server on http://localhost:5173
- Proxies /api/* to http://localhost:5000

**Use when:**
- API is already running
- Frontend development only
- Need separate terminal for API logs

## Build Commands

### `make build`
Build frontend for production.

```bash
make build
```

**What it does:**
- Runs `npm run build` in web/
- Outputs to public/ directory
- Minifies and optimizes assets

### `make start`
Build and start production server.

```bash
make start
```

Equivalent to: `make build && make api`

**Use when:**
- Testing production build
- Deploying to production
- Want optimized assets

## Generation Commands

### `make generate`
Quick image generation via command line.

```bash
make generate PROMPT="a beautiful sunset"
make generate PROMPT="a cute cat" SEED=42
```

**Parameters:**
- `PROMPT` (required) - Text prompt for generation
- Other params via examples/generate.py args

**Examples:**
```bash
# Basic generation
make generate PROMPT="a dog jumping"

# With seed
make generate PROMPT="landscape" SEED=42

# Advanced (edit Makefile or use script directly)
python examples/generate.py --prompt "..." --steps 50 --width 768
```

## Maintenance Commands

### `make clean`
Clean build artifacts and cache.

```bash
make clean
```

**Removes:**
- public/ (built frontend)
- web/dist/ (alternative build output)
- web/.vite/ (Vite cache)
- __pycache__/ directories
- *.pyc files

### `make reorganize`
Reorganize project structure.

```bash
make reorganize
```

Runs the reorganization script that:
- Creates docs/, scripts/, web/ directories
- Moves files to appropriate locations
- Updates configurations
- Creates backups

## Setup Commands (One-Time)

### `make setup-drives`
Format and mount additional drives.

```bash
make setup-drives
```

**Requires sudo**. Runs scripts/setup/setup_drives.sh

### `make setup-samba`
Configure SMB network shares.

```bash
make setup-samba
```

**Requires sudo**. Runs scripts/setup/setup_samba.sh

### `make setup-speedy`
Configure Imagineer to use Speedy drive.

```bash
make setup-speedy
```

Runs scripts/setup/configure_speedy.sh

## Diagnostic Commands

### `make status`
Show project status.

```bash
make status
```

**Displays:**
- Python environment status
- Frontend build status
- GPU information
- Symlink status

**Example output:**
```
Imagineer Status
================

Python Environment:
  ✓ Virtual environment exists

Frontend:
  ✓ Node modules installed
  ⚠️  No production build (run: make build)

GPU:
NVIDIA GeForce RTX 3080, 580.65.06, 10240 MiB

Outputs:
  ✓ Outputs symlink exists
  ✓ Models symlink exists
```

### `make check`
Verify system requirements.

```bash
make check
```

**Checks for:**
- Python 3
- Node.js
- npm
- nvidia-smi (GPU)

**Shows versions:**
```
✓ All requirements met

Python 3.12.3
v20.11.0
10.2.4
```

### `make test`
Run test suite (placeholder).

```bash
make test
```

Currently shows "Tests not yet implemented". Will run pytest when tests are added.

## Common Workflows

### First Time Setup
```bash
# 1. Check requirements
make check

# 2. Install dependencies
make setup

# 3. (Optional) Setup drives
make setup-drives
make setup-samba
make setup-speedy

# 4. Start development
make dev
```

### Daily Development
```bash
# Start dev servers
make dev

# In another terminal, generate test images
make generate PROMPT="test image"
```

### Frontend Development
```bash
# Terminal 1: API server
make api

# Terminal 2: Frontend dev server
make web-dev
```

### Production Deployment
```bash
# Build and start
make build
make api

# Or combined
make start
```

### Cleanup
```bash
# Clean build artifacts
make clean

# Reinstall if needed
make setup
```

## Tips

**Parallel Execution:**
Makefile runs commands in parallel when possible. `make dev` starts both servers simultaneously.

**Background Jobs:**
Use `&` to run in background:
```bash
make api &
make web-dev
```

**Environment Variables:**
Pass variables to commands:
```bash
PROMPT="my prompt" make generate
PORT=5001 make api
```

**Stop Servers:**
Always use **Ctrl+C** to gracefully stop servers. The Makefile handles cleanup.

**Check Before Running:**
Use `make status` and `make check` to verify setup before starting servers.

## Troubleshooting

**"make: command not found"**
```bash
# Install make
sudo apt install build-essential
```

**"No rule to make target"**
Check spelling of command: `make help` to see all available commands.

**Port already in use**
```bash
# Find and kill process using port 5000
sudo lsof -i :5000
kill -9 <PID>
```

**Permission denied**
Some commands require sudo:
```bash
make setup-drives    # Requires sudo prompt
make setup-samba     # Requires sudo prompt
```

**Build fails**
```bash
# Clean and rebuild
make clean
make install-web
make build
```

## Advanced Usage

### Custom Targets
Edit Makefile to add your own targets:

```makefile
# Add custom command
my-command:
	@echo "Running custom command"
	./my-script.sh
```

### Chaining Commands
```bash
# Multiple commands
make clean && make setup && make build && make start

# Conditional execution
make check && make dev || echo "Requirements not met"
```

### Scripting
Use Makefile commands in scripts:

```bash
#!/bin/bash
make check || exit 1
make setup
make build
make start
```

## Environment Variables

Set these in `.env` or export in shell:

```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
export PORT=5000
```

Then use in Makefile or scripts.

## See Also

- **README.md** - Project overview
- **QUICKSTART.md** - Getting started guide
- **docs/API.md** - API documentation
- **docs/SETUP.md** - Detailed setup instructions
