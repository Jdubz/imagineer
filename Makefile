.PHONY: help install install-web install-hooks dev api build start test test-backend test-frontend test-coverage lint lint-backend lint-frontend lint-fix clean reorganize kill lora-check lora-clean lora-organize lora-organize-fast lora-previews lora-previews-queue lora-previews-test lora-previews-regenerate lora-reconcile deploy-infra deploy-backend deploy-tunnel deploy-frontend-dev deploy-frontend-prod deploy-all deploy-all-dry-run deploy-backend-stack deploy-frontend-only deploy-status deploy-restart destroy-infra prod-setup prod-start prod-stop prod-restart prod-logs prod-status prod-deploy

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
	@echo "  make install-hooks  - Install git hooks (pre-commit, pre-push)"
	@echo "  make dev            - Start API + frontend dev servers"
	@echo "  make api            - Start Flask API server only (port $(API_PORT))"
	@echo "  make web-dev        - Start frontend dev server only (port $(WEB_PORT))"
	@echo "  make build          - Build frontend for production"
	@echo "  make start          - Start production server (API + built frontend)"
	@echo "  make generate       - Quick image generation (use PROMPT=...)"
	@echo "  make kill           - Kill all running Imagineer services"
	@echo "  make test           - Run all tests (backend + frontend)"
	@echo "  make test-backend   - Run backend tests only"
	@echo "  make test-frontend  - Run frontend tests only"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo "  make lint           - Lint all code (backend + frontend)"
	@echo "  make lint-backend   - Lint backend code only"
	@echo "  make lint-frontend  - Lint frontend code only"
	@echo "  make lint-fix       - Auto-fix linting issues"
	@echo ""
	@echo "LoRA Management:"
	@echo "  make lora-check                - Check LoRA compatibility (dry run)"
	@echo "  make lora-clean                - Move incompatible LoRAs to _incompatible/"
	@echo "  make lora-organize             - Organize new LoRAs with local preview generation"
	@echo "  make lora-organize-fast        - Organize new LoRAs without previews (fast)"
	@echo "  make lora-previews-queue       - Queue preview generation via API (recommended)"
	@echo "  make lora-previews             - Generate previews locally (synchronous)"
	@echo "  make lora-previews-test        - Test trigger word extraction (dry run)"
	@echo "  make lora-previews-regenerate  - Regenerate ALL previews with better prompts"
	@echo "  make lora-reconcile            - Reconcile index with folders (validation)"
	@echo ""
	@echo "Production Server (Docker/systemd):"
	@echo "  make prod-setup             - Complete production setup (Docker + webhook)"
	@echo "  make prod-start             - Start production services"
	@echo "  make prod-stop              - Stop production services"
	@echo "  make prod-restart           - Restart production services"
	@echo "  make prod-logs              - View production logs"
	@echo "  make prod-status            - Show production status"
	@echo "  make prod-deploy            - Manual deployment trigger"
	@echo ""
	@echo "Deployment (Infrastructure as Code):"
	@echo "  make deploy-all             - Full orchestrated deployment (all components)"
	@echo "  make deploy-all-dry-run     - Preview deployment without making changes"
	@echo "  make deploy-backend-stack   - Deploy backend + tunnel only"
	@echo "  make deploy-frontend-only   - Deploy frontend only (fast)"
	@echo "  make deploy-infra           - Deploy Cloudflare infrastructure (Terraform)"
	@echo "  make deploy-backend         - Setup backend API service (systemd)"
	@echo "  make deploy-tunnel          - Setup Cloudflare Tunnel (systemd)"
	@echo "  make deploy-frontend-dev    - Deploy frontend to Firebase (dev)"
	@echo "  make deploy-frontend-prod   - Deploy frontend to Firebase (prod)"
	@echo "  make deploy-status          - Show deployment status"
	@echo "  make deploy-restart         - Restart all services"
	@echo "  make destroy-infra          - Destroy Cloudflare infrastructure (Terraform)"
	@echo ""
	@echo "Other:"
	@echo "  make clean          - Clean build artifacts"
	@echo "  make reorganize     - Reorganize project structure"
	@echo ""
	@echo "Ports: API=$(API_PORT), Frontend=$(WEB_PORT)"
	@echo ""
	@echo "Examples:"
	@echo "  make dev                                    # Start development"
	@echo "  make generate PROMPT='a cute cat'           # Generate image"
	@echo "  make lora-organize-fast                     # Organize LoRAs (fast)"
	@echo "  make lora-previews-queue                    # Generate previews via API"
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

# Install git hooks
install-hooks:
	@echo "Installing git hooks..."
	bash scripts/install-hooks.sh

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

# Run all tests
test: test-backend test-frontend
	@echo "✓ All tests complete"

# Run backend tests
test-backend:
	@echo "Running backend tests..."
	. venv/bin/activate && pytest tests/backend/ -v

# Run frontend tests
test-frontend:
	@echo "Running frontend tests..."
	cd web && npm test

# Run tests with coverage
test-coverage:
	@echo "Running tests with coverage..."
	@echo ""
	@echo "Backend coverage:"
	. venv/bin/activate && pytest tests/backend/ --cov=server --cov=src --cov-report=term --cov-report=html:coverage/backend
	@echo ""
	@echo "Frontend coverage:"
	cd web && npm run test:coverage
	@echo ""
	@echo "✓ Coverage reports generated:"
	@echo "  Backend:  coverage/backend/index.html"
	@echo "  Frontend: web/coverage/index.html"

# Lint all code
lint: lint-backend lint-frontend
	@echo "✓ All linting complete"

# Lint backend code
lint-backend:
	@echo "Linting Python code..."
	. venv/bin/activate && black --check .
	. venv/bin/activate && flake8 .
	. venv/bin/activate && isort --check-only .
	@echo "✓ Backend linting passed"

# Lint frontend code
lint-frontend:
	@echo "Linting JavaScript code..."
	cd web && npm run lint
	@echo "✓ Frontend linting passed"

# Auto-fix linting issues
lint-fix:
	@echo "Auto-fixing linting issues..."
	@echo "Backend..."
	. venv/bin/activate && black .
	. venv/bin/activate && isort .
	@echo "Frontend..."
	cd web && npm run lint:fix
	@echo "✓ Linting fixes applied"

# Check LoRA compatibility (dry run)
lora-check:
	@echo "Checking LoRA compatibility..."
	. venv/bin/activate && python scripts/clean_loras.py

# Clean incompatible LoRAs (move to _incompatible/)
lora-clean:
	@echo "Cleaning incompatible LoRAs..."
	. venv/bin/activate && python scripts/clean_loras.py --clean
	@echo ""
	@echo "✓ LoRA cleanup complete"
	@echo "Review moved files in: /mnt/speedy/imagineer/models/lora/_incompatible/"

# Organize new LoRAs (auto-detect, folder, preview, index)
lora-organize:
	@echo "Organizing new LoRAs..."
	. venv/bin/activate && python scripts/organize_loras.py
	@echo ""
	@echo "✓ LoRA organization complete"

# Reconcile index (validation only)
lora-reconcile:
	@echo "Reconciling LoRA index..."
	. venv/bin/activate && python scripts/organize_loras.py --reconcile-only

lora-organize-fast:
	@echo "Organizing new LoRAs (skipping preview generation)..."
	. venv/bin/activate && python scripts/organize_loras.py --no-preview
	@echo ""
	@echo "✓ LoRA organization complete (no previews)"
	@echo "  To generate previews: make lora-previews-queue"

lora-previews-queue:
	@echo "Queueing preview generation jobs via API server..."
	@echo "(Requires API server running: python server/api.py)"
	. venv/bin/activate && python scripts/generate_previews.py --queue --missing-only
	@echo ""

lora-previews:
	@echo "Generating previews locally (synchronous, may be slow)..."
	. venv/bin/activate && python scripts/generate_previews.py --missing-only
	@echo ""

lora-previews-test:
	@echo "Testing trigger word extraction..."
	. venv/bin/activate && python scripts/test_trigger_words.py

lora-previews-regenerate:
	@echo "Regenerating ALL previews with auto-detected trigger words..."
	@echo "(This will replace existing previews)"
	. venv/bin/activate && python scripts/regenerate_previews.py --queue
	@echo ""

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

# ========================================
# Deployment Commands (IaC)
# ========================================

# Deploy Cloudflare infrastructure with Terraform
deploy-infra:
	@echo "🌐 Deploying Cloudflare infrastructure..."
	@if [ ! -f terraform/terraform.tfvars ]; then \
		echo "❌ terraform.tfvars not found"; \
		echo "   Copy terraform/terraform.tfvars.example to terraform/terraform.tfvars"; \
		echo "   and fill in your values"; \
		exit 1; \
	fi
	cd terraform && terraform init
	cd terraform && terraform plan
	@echo ""
	@read -p "Apply this plan? (yes/no): " confirm && [ "$$confirm" = "yes" ] || exit 1
	cd terraform && terraform apply -auto-approve
	@echo ""
	@echo "✅ Infrastructure deployed!"

# Destroy Cloudflare infrastructure
destroy-infra:
	@echo "⚠️  Destroying Cloudflare infrastructure..."
	@read -p "Are you sure? This will destroy all resources. (yes/no): " confirm && [ "$$confirm" = "yes" ] || exit 1
	cd terraform && terraform destroy
	@echo "✅ Infrastructure destroyed"

# Setup backend API server with systemd
deploy-backend:
	@echo "🚀 Setting up backend API server..."
	bash scripts/deploy/setup-backend.sh
	@echo ""
	@echo "✅ Backend deployed!"
	@echo "   Test: curl http://localhost:10050/api/health"

# Setup Cloudflare Tunnel with systemd
deploy-tunnel:
	@echo "🌐 Setting up Cloudflare Tunnel for imagineer.joshwentworth.com..."
	bash scripts/deploy/setup-cloudflare-tunnel-custom.sh
	@echo ""
	@echo "✅ Tunnel deployed!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Update terraform/terraform.tfvars with tunnel ID"
	@echo "  2. Add Cloudflare API token to terraform.tfvars"
	@echo "  3. Run: make deploy-infra"

# Deploy frontend to Firebase (development)
deploy-frontend-dev:
	@echo "🚀 Deploying frontend to Firebase (development)..."
	bash scripts/deploy/deploy-frontend.sh dev
	@echo ""
	@echo "✅ Frontend deployed to development!"

# Deploy frontend to Firebase (production)
deploy-frontend-prod:
	@echo "🚀 Deploying frontend to Firebase (production)..."
	bash scripts/deploy/deploy-frontend.sh prod
	@echo ""
	@echo "✅ Frontend deployed to production!"

# Full deployment (all components) - Orchestrated
deploy-all:
	@echo "🚀 Starting comprehensive deployment orchestration..."
	bash scripts/deploy/deploy-all.sh

# Full deployment with dry run (preview only)
deploy-all-dry-run:
	@echo "🔍 Dry run: showing what would be deployed..."
	bash scripts/deploy/deploy-all.sh --dry-run

# Deploy only backend and tunnel (skip infra and frontend)
deploy-backend-stack:
	@echo "🚀 Deploying backend stack..."
	bash scripts/deploy/deploy-all.sh --backend-only --tunnel-only

# Deploy only frontend
deploy-frontend-only:
	@echo "🚀 Deploying frontend only..."
	bash scripts/deploy/deploy-all.sh --frontend-only --skip-checks

# Show deployment status
deploy-status:
	@echo "Deployment Status"
	@echo "================="
	@echo ""
	@echo "Backend Service:"
	@-sudo systemctl is-active --quiet imagineer-api && \
		echo "  ✓ Running" || echo "  ❌ Not running"
	@-sudo systemctl is-active --quiet imagineer-api && \
		sudo systemctl status imagineer-api --no-pager -l | head -15
	@echo ""
	@echo "Cloudflare Tunnel:"
	@-sudo systemctl is-active --quiet cloudflared-imagineer-api && \
		echo "  ✓ Running" || echo "  ❌ Not running"
	@-sudo systemctl is-active --quiet cloudflared-imagineer-api && \
		sudo systemctl status cloudflared-imagineer-api --no-pager -l | head -15
	@echo ""
	@echo "Terraform State:"
	@-[ -f terraform/terraform.tfstate ] && \
		echo "  ✓ Infrastructure deployed" || echo "  ⚠️  No infrastructure deployed"
	@echo ""
	@echo "Firebase:"
	@-command -v firebase >/dev/null 2>&1 && \
		firebase projects:list 2>/dev/null | grep -q "." && \
		echo "  ✓ Logged in" || echo "  ⚠️  Not logged in (run: firebase login)"

# Restart all services
deploy-restart:
	@echo "Restarting services..."
	@-sudo systemctl restart imagineer-api && echo "  ✓ Backend restarted"
	@-sudo systemctl restart cloudflared-imagineer-api && echo "  ✓ Tunnel restarted"
	@echo "✅ Services restarted"

# ========================================
# Production Server Commands
# ========================================

# Complete production setup
prod-setup:
	@echo "🚀 Setting up production environment..."
	bash scripts/deploy/setup-production.sh
	@echo ""
	@echo "✅ Production setup complete!"
	@echo "   Run 'make prod-status' to check status"

# Start production services
prod-start:
	@echo "🚀 Starting production services..."
	@if docker ps -a | grep -q imagineer-api; then \
		echo "Using Docker..."; \
		docker-compose up -d; \
	elif systemctl list-units --full -all | grep -q imagineer-api; then \
		echo "Using systemd..."; \
		sudo systemctl start imagineer-api; \
		sudo systemctl start imagineer-webhook 2>/dev/null || true; \
	else \
		echo "❌ No production services found. Run 'make prod-setup' first"; \
		exit 1; \
	fi
	@echo "✅ Production services started"

# Stop production services
prod-stop:
	@echo "🛑 Stopping production services..."
	@if docker ps -a | grep -q imagineer-api; then \
		echo "Using Docker..."; \
		docker-compose down; \
	elif systemctl list-units --full -all | grep -q imagineer-api; then \
		echo "Using systemd..."; \
		sudo systemctl stop imagineer-api; \
		sudo systemctl stop imagineer-webhook 2>/dev/null || true; \
	else \
		echo "❌ No production services found"; \
		exit 1; \
	fi
	@echo "✅ Production services stopped"

# Restart production services
prod-restart:
	@echo "🔄 Restarting production services..."
	@if docker ps -a | grep -q imagineer-api; then \
		echo "Using Docker..."; \
		docker-compose restart; \
	elif systemctl list-units --full -all | grep -q imagineer-api; then \
		echo "Using systemd..."; \
		sudo systemctl restart imagineer-api; \
		sudo systemctl restart imagineer-webhook 2>/dev/null || true; \
	else \
		echo "❌ No production services found"; \
		exit 1; \
	fi
	@echo "✅ Production services restarted"

# View production logs
prod-logs:
	@if docker ps -a | grep -q imagineer-api; then \
		echo "Showing Docker logs (Ctrl+C to exit)..."; \
		docker-compose logs -f; \
	elif systemctl list-units --full -all | grep -q imagineer-api; then \
		echo "Showing systemd logs (Ctrl+C to exit)..."; \
		sudo journalctl -u imagineer-api -f; \
	else \
		echo "❌ No production services found"; \
		exit 1; \
	fi

# Show production status
prod-status:
	@echo "Production Status"
	@echo "================="
	@echo ""
	@if docker ps -a | grep -q imagineer-api; then \
		echo "Deployment: Docker"; \
		echo ""; \
		docker-compose ps; \
		echo ""; \
		echo "Health:"; \
		curl -s http://localhost:10050/api/health | python3 -m json.tool 2>/dev/null || echo "  ❌ API not responding"; \
	elif systemctl list-units --full -all | grep -q imagineer-api; then \
		echo "Deployment: systemd"; \
		echo ""; \
		echo "Backend Service:"; \
		sudo systemctl status imagineer-api --no-pager | head -15; \
		echo ""; \
		echo "Webhook Service:"; \
		sudo systemctl status imagineer-webhook --no-pager 2>/dev/null | head -10 || echo "  - Not running"; \
		echo ""; \
		echo "Health:"; \
		curl -s http://localhost:10050/api/health | python3 -m json.tool 2>/dev/null || echo "  ❌ API not responding"; \
	else \
		echo "❌ No production services found"; \
		echo "   Run 'make prod-setup' to set up production environment"; \
	fi

# Manual deployment trigger
prod-deploy:
	@echo "🚀 Triggering manual deployment..."
	bash scripts/deploy/backend-release.sh
	@echo ""
	@echo "✅ Deployment complete!"
	@echo "   Run 'make prod-status' to verify"
