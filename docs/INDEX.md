# Imagineer Documentation Index

Complete guide to all Imagineer documentation.

## 📖 Quick Start

**New to Imagineer?** Start here:
1. [README.md](../README.md) - Project overview
2. [guides/SETUP.md](guides/SETUP.md) - Installation and setup
3. [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture

**Deploying to production?** Start here:
1. [deployment/DEPLOYMENT_CHEATSHEET.md](deployment/DEPLOYMENT_CHEATSHEET.md) - Quick reference
2. [deployment/CREDENTIALS_QUICK_REFERENCE.md](deployment/CREDENTIALS_QUICK_REFERENCE.md) - Required credentials
3. [deployment/DEPLOYMENT_ORCHESTRATION_COMPLETE.md](deployment/DEPLOYMENT_ORCHESTRATION_COMPLETE.md) - Get started

## 📂 Documentation Structure

```
docs/
├── INDEX.md                        (this file)
├── ARCHITECTURE.md                 (system architecture)
├── API.md                          (API reference)
│
├── deployment/                     (Production deployment docs)
│   ├── DEPLOYMENT_CHEATSHEET.md
│   ├── DEPLOYMENT_ORCHESTRATION_COMPLETE.md
│   ├── DEPLOYMENT_ORCHESTRATION.md
│   ├── DEPLOYMENT_ORCHESTRATION_SUMMARY.md
│   ├── DEPLOYMENT_GUIDE.md
│   ├── DEPLOYMENT_README.md
│   ├── CLOUDFLARE_TUNNEL_SETUP.md
│   ├── FIREBASE_QUICKSTART.md
│   ├── FIREBASE_SETUP.md
│   ├── FIREBASE_CLOUDFLARE_DEPLOYMENT.md
│   ├── PRODUCTION_README.md
│   ├── PRODUCTION_SETUP.md
│   ├── CREDENTIALS_QUICK_REFERENCE.md
│   ├── REQUIRED_CREDENTIALS.md
│   ├── SECURE_AUTHENTICATION_PLAN.md
│   └── CLI_QUICK_REFERENCE.md
│
├── lora/                           (LoRA management docs)
│   ├── LORA_SETUP.md
│   ├── LORA_ORGANIZATION.md
│   └── LORA_PREVIEW_GENERATION.md
│
├── guides/                         (Development guides)
│   ├── SETUP.md
│   ├── TESTING.md
│   ├── LINTING.md
│   ├── CONTRIBUTING.md
│   ├── MAKEFILE_REFERENCE.md
│   └── NEXT_STEPS.md
│
└── plans/                          (Planning & audit documents)
    └── FRONTEND_CODE_AUDIT.md
```

---

## 🏗️ Core Documentation

### [ARCHITECTURE.md](ARCHITECTURE.md)
**Complete system architecture documentation**
- v1.0.0 features (multi-LoRA support, React gallery, REST API)
- Component breakdown (backend, frontend, storage)
- Data flow and directory structure
- File organization patterns

### [API.md](API.md)
**REST API reference**
- Endpoint documentation
- Request/response formats
- Authentication
- Error handling

---

## 🚀 Deployment Documentation

### Quick Start
- **[DEPLOYMENT_CHEATSHEET.md](deployment/DEPLOYMENT_CHEATSHEET.md)** - One-page command reference
- **[CREDENTIALS_QUICK_REFERENCE.md](deployment/CREDENTIALS_QUICK_REFERENCE.md)** - Required credentials at a glance

### Getting Started with Deployment
- **[DEPLOYMENT_ORCHESTRATION_COMPLETE.md](deployment/DEPLOYMENT_ORCHESTRATION_COMPLETE.md)** - Start here for orchestrated deployment
- **[DEPLOYMENT_ORCHESTRATION_SUMMARY.md](deployment/DEPLOYMENT_ORCHESTRATION_SUMMARY.md)** - System overview

### Complete Guides
- **[DEPLOYMENT_ORCHESTRATION.md](deployment/DEPLOYMENT_ORCHESTRATION.md)** - Complete orchestration guide (~10,000 words)
- **[DEPLOYMENT_GUIDE.md](deployment/DEPLOYMENT_GUIDE.md)** - Original comprehensive deployment guide
- **[DEPLOYMENT_README.md](deployment/DEPLOYMENT_README.md)** - IaC deployment overview

### Component-Specific Deployment
- **[CLOUDFLARE_TUNNEL_SETUP.md](deployment/CLOUDFLARE_TUNNEL_SETUP.md)** - Cloudflare Tunnel for imagineer.joshwentworth.com
- **[FIREBASE_QUICKSTART.md](deployment/FIREBASE_QUICKSTART.md)** - Firebase deployment quick reference
- **[FIREBASE_SETUP.md](deployment/FIREBASE_SETUP.md)** - Complete Firebase setup guide
- **[FIREBASE_CLOUDFLARE_DEPLOYMENT.md](deployment/FIREBASE_CLOUDFLARE_DEPLOYMENT.md)** - Planning document
- **[PRODUCTION_README.md](deployment/PRODUCTION_README.md)** - Production server quick start
- **[PRODUCTION_SETUP.md](deployment/PRODUCTION_SETUP.md)** - Complete production server guide

### Credentials & Security
- **[REQUIRED_CREDENTIALS.md](deployment/REQUIRED_CREDENTIALS.md)** - Complete credentials guide with troubleshooting
- **[SECURE_AUTHENTICATION_PLAN.md](deployment/SECURE_AUTHENTICATION_PLAN.md)** - Authentication upgrade roadmap

### Command Reference
- **[CLI_QUICK_REFERENCE.md](deployment/CLI_QUICK_REFERENCE.md)** - All deployment commands

---

## 🎨 LoRA Management Documentation

### [LORA_SETUP.md](lora/LORA_SETUP.md)
**Getting started with LoRAs**
- What are LoRAs
- Downloading and installing
- Compatibility checking

### [LORA_ORGANIZATION.md](lora/LORA_ORGANIZATION.md)
**LoRA management system**
- Automatic organization
- Folder structure
- Index management
- Compatibility detection

### [LORA_PREVIEW_GENERATION.md](lora/LORA_PREVIEW_GENERATION.md)
**Generating LoRA previews**
- Automatic trigger word extraction
- Preview generation methods
- Batch processing
- Troubleshooting

---

## 📚 Development Guides

### [guides/SETUP.md](guides/SETUP.md)
**Initial project setup**
- Prerequisites
- Installation steps
- Configuration
- First run

### [guides/TESTING.md](guides/TESTING.md)
**Testing guide**
- Running tests
- Writing tests
- Test coverage
- CI/CD integration

### [guides/LINTING.md](guides/LINTING.md)
**Code quality and linting**
- Linting tools (black, flake8, isort)
- Running linters
- Auto-fixing issues
- Pre-commit hooks

### [guides/TRAINING_OPERATIONS.md](guides/TRAINING_OPERATIONS.md)
**Manage LoRA training runs**
- Asset locations surfaced in the UI
- Accessing and downloading training logs
- Cleanup / retention workflow

### [guides/CONTRIBUTING.md](guides/CONTRIBUTING.md)
**Contributing to Imagineer**
- Development workflow
- Code style
- Pull request process
- Issue guidelines

### [guides/MAKEFILE_REFERENCE.md](guides/MAKEFILE_REFERENCE.md)
**Complete Makefile command reference**
- All `make` commands
- Usage examples
- Port configuration

### [guides/NEXT_STEPS.md](guides/NEXT_STEPS.md)
**Roadmap and future improvements**
- Planned features
- Known issues
- Enhancement ideas

---

## 📋 Planning & Audits

### [plans/FRONTEND_CODE_AUDIT.md](plans/FRONTEND_CODE_AUDIT.md)
**Comprehensive frontend code audit (2025-10-28)**
- 30 prioritized issues (P0-P3)
- Code quality, performance, accessibility analysis
- Memory leaks, error handling, security issues
- Test coverage gaps and recommendations
- Immediate actions and long-term roadmap

---

## 🎯 Documentation by Task

### I want to...

**...set up the project for the first time**
1. [guides/SETUP.md](guides/SETUP.md)
2. [ARCHITECTURE.md](ARCHITECTURE.md)
3. [lora/LORA_SETUP.md](lora/LORA_SETUP.md)

**...deploy to production**
1. [deployment/DEPLOYMENT_CHEATSHEET.md](deployment/DEPLOYMENT_CHEATSHEET.md)
2. [deployment/CREDENTIALS_QUICK_REFERENCE.md](deployment/CREDENTIALS_QUICK_REFERENCE.md)
3. [deployment/DEPLOYMENT_ORCHESTRATION_COMPLETE.md](deployment/DEPLOYMENT_ORCHESTRATION_COMPLETE.md)

**...manage LoRAs**
1. [lora/LORA_ORGANIZATION.md](lora/LORA_ORGANIZATION.md)
2. [lora/LORA_PREVIEW_GENERATION.md](lora/LORA_PREVIEW_GENERATION.md)

**...use the API**
1. [API.md](API.md)
2. [../README.md](../README.md) (examples)

**...contribute code**
1. [guides/CONTRIBUTING.md](guides/CONTRIBUTING.md)
2. [guides/TESTING.md](guides/TESTING.md)
3. [guides/LINTING.md](guides/LINTING.md)

**...understand the architecture**
1. [ARCHITECTURE.md](ARCHITECTURE.md)
2. [../CLAUDE.md](../CLAUDE.md) (Claude Code instructions)

**...improve frontend code quality**
1. [plans/FRONTEND_CODE_AUDIT.md](plans/FRONTEND_CODE_AUDIT.md)
2. [guides/TESTING.md](guides/TESTING.md)
3. [guides/LINTING.md](guides/LINTING.md)

**...troubleshoot issues**
- Deployment: [deployment/DEPLOYMENT_ORCHESTRATION.md](deployment/DEPLOYMENT_ORCHESTRATION.md#troubleshooting)
- Credentials: [deployment/REQUIRED_CREDENTIALS.md](deployment/REQUIRED_CREDENTIALS.md#troubleshooting-authentication-issues)
- LoRAs: [lora/LORA_PREVIEW_GENERATION.md](lora/LORA_PREVIEW_GENERATION.md#troubleshooting)

---

## 📊 Documentation Statistics

- **Total documentation files**: 28
- **Deployment docs**: 18 files (~40,000 words)
- **LoRA docs**: 3 files (~3,000 words)
- **Development guides**: 6 files (~5,000 words)
- **Planning & audits**: 1 file (~9,000 words)
- **Core docs**: 2 files (~7,000 words)

---

## 🔄 Recently Reorganized

**2024-10-14**: Major reorganization
- Moved all deployment docs from root to `docs/deployment/`
- Organized LoRA docs into `docs/lora/`
- Consolidated development guides into `docs/guides/`
- Removed redundant scripts (replaced by Makefile targets)
- Created this index

**Before reorganization**: 8 markdown files in root
**After reorganization**: Clean root with only README, CLAUDE.md, LICENSE

---

## 💡 Quick Tips

**For daily development:**
```bash
make help                    # See all available commands
make dev                     # Start development environment
make lora-organize-fast      # Organize new LoRAs
```

**For deployment:**
```bash
make deploy-all-dry-run      # Preview deployment
make deploy-all              # Full deployment
make prod-status             # Check production status
```

**For documentation:**
- Start with this index to find what you need
- Use quick reference sheets for common tasks
- Refer to complete guides for detailed information

---

## 📝 Contributing to Documentation

Found an error or want to improve the docs?

1. See [guides/CONTRIBUTING.md](guides/CONTRIBUTING.md)
2. Documentation follows GitHub-flavored Markdown
3. Keep code examples up to date
4. Update this index when adding new docs

---

**Need help?** Open an issue at https://github.com/yourusername/imagineer/issues
