# Project Organization

This document describes the organization of the Imagineer project directory structure.

## Directory Structure

```
imagineer/
├── config/                      # Configuration files
│   └── deployment/              # Deployment-related configs
│       ├── cloudflared-config.yml
│       ├── cloudflared-imagineer-api.service
│       ├── imagineer-api.service
│       └── nginx-imagineer.conf
├── data/                        # Training data
├── docs/                        # Documentation
│   ├── deployment/              # Deployment guides
│   ├── guides/                  # How-to guides
│   ├── lora/                    # LoRA documentation
│   └── plans/                   # Improvement plans
├── examples/                    # Example scripts
├── scripts/                     # Setup and utility scripts
│   ├── RUN_THESE_COMMANDS.sh
│   ├── complete-setup.sh
│   └── setup-production-services.sh
├── server/                      # Backend API
│   ├── api.py                   # Flask API server
│   ├── auth.py                  # Google OAuth implementation
│   └── users.json.example       # User roles template
├── src/                         # Core Python package
│   └── imagineer/
├── tests/                       # Test files
├── web/                         # React frontend
│   ├── src/
│   ├── public/
│   └── dist/                    # Build output (gitignored)
├── .github/                     # GitHub Actions workflows
├── terraform/                   # Infrastructure as code
├── config.yaml                  # Main application config
├── firebase.json                # Firebase Hosting config
├── docker-compose.yml           # Docker composition
├── Makefile                     # Common tasks
├── requirements.txt             # Python dependencies
├── README.md                    # Project README
└── CLAUDE.md                    # Claude Code instructions
```

## Key Files

### Root Level

- **README.md** - Project overview and quick start
- **CLAUDE.md** - Instructions for Claude Code when working with this codebase
- **config.yaml** - Main application configuration (model paths, settings)
- **Makefile** - Common development tasks
- **requirements.txt** - Python dependencies
- **pyproject.toml** / **setup.py** - Python package configuration

### Configuration (`config/`)

- **config/deployment/** - All deployment-related configuration files
  - `cloudflared-config.yml` - Cloudflare Tunnel routing rules
  - `*.service` - systemd service definitions
  - `nginx-imagineer.conf` - nginx web server configuration

### Scripts (`scripts/`)

- **RUN_THESE_COMMANDS.sh** - Quick setup script (requires sudo)
- **complete-setup.sh** - Full automated setup
- **setup-production-services.sh** - Production services installation
- **test_all_loras.sh** (root) - LoRA testing utility

### Documentation (`docs/`)

- **docs/deployment/** - Deployment guides and instructions
  - `PRODUCTION_DEPLOYMENT_GUIDE.md` - Comprehensive deployment guide
  - `DEPLOYMENT_QUICK_START.md` - 20-minute quick start
  - `SETUP_INSTRUCTIONS.md` - Step-by-step setup
  - `DEPLOYMENT_CHANGES_SUMMARY.md` - Summary of all deployment changes
  - `DEPLOYMENT_STATUS_AND_NEXT_STEPS.md` - Status checklist
- **docs/plans/** - Project improvement plans
  - `REVISED_IMPROVEMENT_PLAN.md` - 5-phase roadmap (90-115 hours)
  - `COMPREHENSIVE_IMPROVEMENT_PLAN.md` - Initial audit-based plan
- **docs/guides/** - How-to guides and tutorials
- **docs/lora/** - LoRA training and usage documentation
- **docs/ARCHITECTURE.md** - System architecture documentation

### Backend (`server/`)

- **api.py** - Flask REST API (port 10050)
- **auth.py** - Google OAuth authentication
- **users.json** - User roles database (gitignored, use users.json.example)

### Frontend (`web/`)

- **src/** - React source code
- **public/** - Static assets
- **dist/** - Production build (gitignored)
- **.env.example** - Environment variables template

## Ignored Files

The following are in `.gitignore` and should NOT be committed:

### Secrets and Environment
- `.env`, `.env.production` - Environment variables with secrets
- `web/.env.development`, `web/.env.production` - Frontend environment
- `server/users.json` - User database (use `users.json.example` as template)
- `.ssh/imagineer_deploy*` - SSH deployment keys

### Build Artifacts
- `public/` - Built frontend (generated from `web/dist/`)
- `web/dist/` - Vite build output
- `venv/` - Python virtual environment
- `node_modules/` - Node.js dependencies
- `__pycache__/` - Python bytecode cache

### Data Directories
- `models/` - LoRA model files (stored on external drive)
- `outputs/` - Generated images (stored on external drive)
- `checkpoints/` - Training checkpoints (stored on external drive)
- `data/training/*` - Training datasets (except README)

### Terraform State
- `terraform/.terraform/` - Terraform plugins
- `terraform/terraform.tfstate*` - State files (contain sensitive data)

### Logs
- `logs/` - Application logs
- `*.log` - All log files

## External Storage

Large files are stored on an external drive at `/mnt/speedy/imagineer/`:

- **models/lora/** - LoRA weight files (*.safetensors)
- **outputs/** - Generated images organized by batch
- **sets/** - Set definitions and prompt templates
- **checkpoints/** - Training checkpoints

## Development Workflow

### Local Development

1. Activate virtual environment: `source venv/bin/activate`
2. Run API: `python server/api.py` (port 10050)
3. Run frontend dev server: `cd web && npm run dev` (port 3000)

### Production Deployment

1. Run setup script: `bash scripts/RUN_THESE_COMMANDS.sh`
2. Build frontend: `cd web && npm run build`
3. Push to main: Git push triggers auto-deployment

### Making Changes

1. Update code in appropriate directory (`server/`, `web/`, `src/`)
2. Update documentation in `docs/` if needed
3. Test locally
4. Commit and push to GitHub
5. GitHub Actions auto-deploys to production

## Service Management

### systemd Services (Production)

- **nginx** - Serves React frontend on port 8080
- **imagineer-api** - Flask API on port 10050
- **cloudflared-imagineer-api** - Cloudflare Tunnel

Commands:
```bash
sudo systemctl status <service>
sudo systemctl restart <service>
sudo journalctl -u <service> -f
```

## Configuration Files by Purpose

### Application Configuration
- `config.yaml` - Main app config (model paths, generation settings)
- `.env.production` - Backend environment (OAuth, secrets)
- `web/.env.production` - Frontend environment (API URL)

### Deployment Configuration
- `config/deployment/cloudflared-config.yml` - Tunnel routing
- `config/deployment/nginx-imagineer.conf` - Web server config
- `config/deployment/*.service` - systemd service definitions

### Infrastructure Configuration
- `firebase.json` - Firebase Hosting (legacy, being deprecated)
- `docker-compose.yml` - Docker services
- `terraform/` - Cloudflare DNS and WAF

### Build Configuration
- `Makefile` - Common tasks
- `web/vite.config.js` - Frontend build
- `pyproject.toml` - Python package
- `.github/workflows/` - CI/CD pipelines

## Key Improvements Made

This organization was established on 2025-10-27 with the following improvements:

1. **Separated concerns** - Deployment configs in `config/`, scripts in `scripts/`, docs in `docs/`
2. **Centralized documentation** - All guides in `docs/` subdirectories
3. **Protected secrets** - Added `users.json` and SSH keys to `.gitignore`
4. **Clear deployment path** - Step-by-step scripts and guides
5. **Removed redundancy** - Consolidated overlapping documents

## Next Steps

After organization is complete:

1. **Complete deployment** - Run `scripts/RUN_THESE_COMMANDS.sh`
2. **Test everything** - Verify all endpoints work
3. **Start improvements** - Follow `docs/plans/REVISED_IMPROVEMENT_PLAN.md`
4. **Add features** - Album system, AI labeling, training pipeline

## Questions?

- **Deployment:** See `docs/deployment/PRODUCTION_DEPLOYMENT_GUIDE.md`
- **Architecture:** See `docs/ARCHITECTURE.md`
- **Improvement plan:** See `docs/plans/REVISED_IMPROVEMENT_PLAN.md`
- **Claude Code usage:** See `CLAUDE.md`
