.PHONY: help install install-web dev api build start test clean reorganize kill

# Port configuration (high ports to avoid conflicts)
API_PORT ?= 10050
WEB_PORT ?= 10051

# Default target
help:
	@echo "Imagineer - AI Image Generation Toolkit"
	@echo ""
	@echo "Available commands:"
	@echo "  make install        - Install Python dependencies"
	@echo "  make install-web    - Install frontend dependencies"
	@echo "  make dev            - Start API + frontend dev servers"
	@echo "  make api            - Start Flask API server only (port $(API_PORT))"
	@echo "  make web-dev        - Start frontend dev server only (port $(WEB_PORT))"
	@echo "  make build          - Build frontend for production"
	@echo "  make start          - Start production server (API + built frontend)"
	@echo "  make generate       - Quick image generation (use PROMPT=...)"
	@echo "  make kill           - Kill all running Imagineer services"
	@echo "  make test           - Run tests (future)"
	@echo "  make clean          - Clean build artifacts"
	@echo "  make reorganize     - Reorganize project structure"
	@echo ""
	@echo "Ports: API=$(API_PORT), Frontend=$(WEB_PORT)"
	@echo ""
	@echo "Examples:"
	@echo "  make dev                                    # Start development"
	@echo "  make generate PROMPT='a cute cat'           # Generate image"
	@echo "  make kill                                   # Stop all services"
	@echo "  API_PORT=6000 make api                      # Use custom port"

# Install Python dependencies
install:
	@echo "Installing Python dependencies..."
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
	. venv/bin/activate && pip install -r requirements.txt
	@echo "✓ Python dependencies installed"

# Install frontend dependencies
install-web:
	@echo "Installing frontend dependencies..."
	cd web && npm install
	@echo "✓ Frontend dependencies installed"

# Start both API and frontend dev servers
dev:
	@echo "Starting development environment..."
	@echo "API: http://localhost:$(API_PORT)"
	@echo "Frontend: http://localhost:$(WEB_PORT)"
	@echo ""
	@echo "Press Ctrl+C to stop (or use 'make kill' to force stop)"
	@bash -c 'trap "trap - SIGTERM && kill -- -$$$$" SIGINT SIGTERM EXIT; \
		. venv/bin/activate && FLASK_RUN_PORT=$(API_PORT) python server/api.py & \
		cd web && PORT=$(WEB_PORT) npm run dev & \
		wait'

# Start API server only
api:
	@echo "Starting Flask API server..."
	@echo "API: http://localhost:$(API_PORT)"
	@echo "Process will run in foreground. Press Ctrl+C to stop."
	. venv/bin/activate && FLASK_RUN_PORT=$(API_PORT) python server/api.py

# Start frontend dev server only (with API proxy)
web-dev:
	@echo "Starting frontend dev server..."
	@echo "Frontend: http://localhost:$(WEB_PORT)"
	@echo "API proxy: http://localhost:$(WEB_PORT)/api -> http://localhost:$(API_PORT)/api"
	@echo "Process will run in foreground. Press Ctrl+C to stop."
	cd web && PORT=$(WEB_PORT) npm run dev

# Kill all running services
kill:
	@echo "Killing Imagineer services..."
	@-pkill -f "python server/api.py" && echo "  ✓ Killed Flask API server" || echo "  - No Flask API server running"
	@-pkill -f "vite" && echo "  ✓ Killed Vite dev server" || echo "  - No Vite dev server running"
	@-lsof -ti:$(API_PORT) | xargs -r kill -9 && echo "  ✓ Killed process on port $(API_PORT)" || true
	@-lsof -ti:$(WEB_PORT) | xargs -r kill -9 && echo "  ✓ Killed process on port $(WEB_PORT)" || true
	@echo "✓ Cleanup complete"

# Build frontend for production
build:
	@echo "Building frontend for production..."
	cd web && npm run build
	@echo "✓ Frontend built to public/"

# Start production server (serve built frontend)
start: build
	@echo "Starting production server..."
	@echo "Server: http://localhost:$(API_PORT)"
	. venv/bin/activate && FLASK_RUN_PORT=$(API_PORT) python server/api.py

# Quick image generation
generate:
	@if [ -z "$(PROMPT)" ]; then \
		echo "Error: PROMPT not specified"; \
		echo "Usage: make generate PROMPT='your prompt here'"; \
		exit 1; \
	fi
	@echo "Generating image with prompt: $(PROMPT)"
	. venv/bin/activate && python examples/generate.py --prompt "$(PROMPT)"

# Run tests (placeholder for future)
test:
	@echo "Running tests..."
	@echo "Tests not yet implemented"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf public/
	rm -rf web/dist/
	rm -rf web/.vite/
	rm -rf web/node_modules/.vite/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Build artifacts cleaned"

# Reorganize project structure
reorganize:
	@echo "Running project reorganization..."
	bash reorganize.sh

# Setup drives and SMB (one-time setup)
setup-drives:
	@echo "Setting up drives..."
	sudo bash scripts/setup/setup_drives.sh

setup-samba:
	@echo "Setting up Samba..."
	sudo bash scripts/setup/setup_samba.sh

setup-speedy:
	@echo "Configuring Speedy drive..."
	bash scripts/setup/configure_speedy.sh

# Full setup (run after reorganization)
setup: install install-web
	@echo ""
	@echo "✓ Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. (Optional) Setup drives: make setup-drives"
	@echo "  2. (Optional) Setup SMB: make setup-samba"
	@echo "  3. Start development: make dev"

# Check system requirements
check:
	@echo "Checking system requirements..."
	@command -v python3 >/dev/null 2>&1 || { echo "❌ Python3 not found"; exit 1; }
	@command -v node >/dev/null 2>&1 || { echo "❌ Node.js not found"; exit 1; }
	@command -v npm >/dev/null 2>&1 || { echo "❌ npm not found"; exit 1; }
	@command -v nvidia-smi >/dev/null 2>&1 || { echo "⚠️  nvidia-smi not found (GPU may not be available)"; }
	@echo "✓ All requirements met"
	@echo ""
	@python3 --version
	@node --version
	@npm --version

# Show status
status:
	@echo "Imagineer Status"
	@echo "================"
	@echo ""
	@echo "Python Environment:"
	@[ -d venv ] && echo "  ✓ Virtual environment exists" || echo "  ❌ Virtual environment missing (run: make install)"
	@echo ""
	@echo "Frontend:"
	@[ -d web/node_modules ] && echo "  ✓ Node modules installed" || echo "  ❌ Node modules missing (run: make install-web)"
	@[ -d public ] && echo "  ✓ Production build exists" || echo "  ⚠️  No production build (run: make build)"
	@echo ""
	@echo "GPU:"
	@command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader || echo "  ⚠️  GPU not detected"
	@echo ""
	@echo "Outputs:"
	@[ -L outputs ] && echo "  ✓ Outputs symlink exists" || echo "  ⚠️  Outputs symlink missing"
	@[ -L models ] && echo "  ✓ Models symlink exists" || echo "  ⚠️  Models symlink missing"
