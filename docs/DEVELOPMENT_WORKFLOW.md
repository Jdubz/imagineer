# Development Workflow

This document describes the proper development workflow for Imagineer, ensuring production remains stable and isolated.

## Overview

Imagineer has **TWO SEPARATE SERVER INSTANCES**:

1. **Production Server** (Port 10050) - systemd service, main branch only
2. **Development Server** (Port 5000) - Local process, develop branch

**CRITICAL**: Never restart, stop, or modify the production server during development!

## Server Comparison

| Aspect | Production (10050) | Development (5000) |
|--------|-------------------|-------------------|
| **Branch** | `main` ONLY | `develop` or feature branches |
| **Process** | systemd service (gunicorn) | Local Flask dev server |
| **Control** | CI/CD pipeline ONLY | `./run-dev.sh` |
| **Config** | `config.yaml` | `config.development.yaml` |
| **Database** | `instance/imagineer.db` | `instance/imagineer-dev.db` |
| **Outputs** | `/mnt/speedy/imagineer/outputs` | `/tmp/imagineer-dev/outputs` |
| **Scraped** | `/mnt/storage/imagineer/scraped` | `/tmp/imagineer-dev/scraped` |
| **Logs** | `/var/log/imagineer/` | `logs/` (local) |
| **CORS** | Production frontend only | `localhost:3000`, `localhost:5173` |
| **Restart** | **NEVER MANUALLY** | Ctrl+C or auto-reload |

## Development Server Usage

### Starting Development Server

```bash
# From project root
./run-dev.sh
```

This will:
- Start Flask on http://127.0.0.1:5000
- Use `config.development.yaml`
- Create separate dev database
- Auto-reload on code changes
- Save outputs to /tmp/imagineer-dev/

### Stopping Development Server

```bash
# Press Ctrl+C in the terminal running run-dev.sh
```

### Checking Server Status

```bash
# Development server
curl http://localhost:5000/api/health

# Production server (READ ONLY - never modify)
curl http://localhost:10050/api/health
```

## Production Server Rules

### ⚠️ NEVER DO THESE:

```bash
# ❌ WRONG - Never restart production manually
sudo systemctl restart imagineer-api

# ❌ WRONG - Never stop production
sudo systemctl stop imagineer-api

# ❌ WRONG - Never edit production config during development
vim config.yaml

# ❌ WRONG - Never commit changes to production paths
```

### ✅ Production is Updated By:

1. **Code changes**: Merge PR to `main` → CI/CD deploys → systemd reloads
2. **Config changes**: Update `config.yaml` in main branch → merge PR → deploy
3. **Dependencies**: Update `requirements.txt` → merge to main → CI/CD installs

## Directory Structure

```
/home/jdubz/Development/imagineer/
├── config.yaml                    # ⚠️  PRODUCTION config (main branch)
├── config.development.yaml        # ✅ Development config
├── .env.production               # ⚠️  Production secrets (gitignored)
├── .env.development              # ✅ Dev template (committed)
├── .env.development.local        # ✅ Local dev overrides (gitignored)
├── run-dev.sh                    # ✅ Development server launcher
├── instance/
│   ├── imagineer.db              # ⚠️  Production database
│   └── imagineer-dev.db          # ✅ Development database
└── server/
    └── api.py                    # Shared code (both envs)

/mnt/speedy/imagineer/            # ⚠️  Production storage
├── outputs/                      # Generated images (prod)
├── models/                       # Shared models (both envs)
└── sets/                         # Shared batch templates

/mnt/storage/imagineer/           # ⚠️  Production storage
└── scraped/                      # Scraped images (prod)

/tmp/imagineer-dev/               # ✅ Development storage
├── outputs/                      # Dev generated images
├── scraped/                      # Dev scraped images
├── checkpoints/                  # Dev training runs
└── bug_reports/                  # Dev bug reports
```

## Development Workflow

### 1. Start Development Session

```bash
# Ensure you're on develop or feature branch
git checkout develop
git pull origin develop

# Start development server
./run-dev.sh
```

### 2. Make Changes

```bash
# Edit code
vim server/api.py

# Server auto-reloads on save (Flask debug mode)
```

### 3. Test Changes

```bash
# Test via development server
curl http://localhost:5000/api/your-endpoint

# Frontend development
cd web
npm run dev  # Runs on port 3000, connects to dev server
```

### 4. Commit and Push

```bash
# Commit your changes
git add .
git commit -m "feat: your feature description"

# Push to develop branch
git push origin develop

# Create PR to main when ready
```

### 5. Production Deployment

```bash
# CI/CD handles this automatically after PR merge to main:
# 1. Runs tests
# 2. Builds if needed
# 3. Deploys to production
# 4. Restarts production server (systemd)
```

## Environment Variables

### Production (.env.production)

```bash
FLASK_ENV=production
PORT=10050
DATABASE_URL=sqlite:///instance/imagineer.db
ALLOWED_ORIGINS=https://imagineer-generator.web.app
GOOGLE_CLIENT_ID=<production-oauth-client-id>
GOOGLE_CLIENT_SECRET=<production-oauth-secret>
```

### Development (.env.development.local)

```bash
FLASK_ENV=development
PORT=5000
DATABASE_URL=sqlite:///instance/imagineer-dev.db
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
# Optional: use dev OAuth or mock auth
# GOOGLE_CLIENT_ID=<dev-oauth-client-id>
# GOOGLE_CLIENT_SECRET=<dev-oauth-secret>
ANTHROPIC_API_KEY=<your-api-key>
```

## Configuration Files

### Production (config.yaml)

- Lives in `main` branch
- Points to production storage: `/mnt/speedy/imagineer/`, `/mnt/storage/imagineer/`
- Managed via PR process
- Changes require PR review and merge to main

### Development (config.development.yaml)

- Lives in repository (all branches)
- Points to dev storage: `/tmp/imagineer-dev/`
- Can be edited freely during development
- Changes can be committed if they improve dev experience

## Common Tasks

### Adding a New Feature

```bash
# 1. Create feature branch from develop
git checkout develop
git pull origin develop
git checkout -b feature/my-new-feature

# 2. Start dev server
./run-dev.sh

# 3. Develop and test
# Edit code, test at http://localhost:5000

# 4. Commit and push
git add .
git commit -m "feat: add new feature"
git push origin feature/my-new-feature

# 5. Create PR to develop
# 6. After review, merge to develop
# 7. When ready for production, create PR from develop to main
```

### Testing API Endpoints

```bash
# Development server (safe to test anything)
curl -X POST http://localhost:5000/api/scraping/start \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "max_images": 10}'

# Production server (READ ONLY - GET requests only for verification)
curl http://localhost:10050/api/health
curl http://localhost:10050/api/albums
```

### Debugging

```bash
# Development server logs (stdout)
./run-dev.sh  # Logs appear in terminal

# Production server logs (READ ONLY)
sudo journalctl -u imagineer-api -f  # Live logs
tail -f /var/log/imagineer/error.log  # Error logs
tail -f /var/log/imagineer/access.log # Access logs
```

### Clearing Development Data

```bash
# Clear dev database
rm instance/imagineer-dev.db

# Clear dev outputs
rm -rf /tmp/imagineer-dev/*

# Restart dev server (will recreate database)
./run-dev.sh
```

## Troubleshooting

### Port 5000 Already in Use

```bash
# Find process using port 5000
lsof -ti:5000

# Kill it
kill $(lsof -ti:5000)

# Or use different port
PORT=5001 ./run-dev.sh
```

### Development Server Not Auto-Reloading

```bash
# Ensure FLASK_DEBUG=1 is set
echo $FLASK_DEBUG

# Restart dev server
# Press Ctrl+C, then ./run-dev.sh again
```

### Wrong Configuration Loaded

```bash
# Check which config is being used
curl http://localhost:5000/api/config/stats

# Verify environment variable
echo $IMAGINEER_CONFIG_PATH

# Should point to config.development.yaml
```

### Accidentally Modified Production Config

```bash
# Revert changes to production config
git checkout main -- config.yaml

# Switch back to your branch
git checkout develop

# Production config should only change via main branch
```

## Best Practices

1. **Branch Management**
   - Work on `develop` or feature branches
   - Never commit directly to `main`
   - Keep `main` clean and deployable

2. **Configuration**
   - Use `config.development.yaml` for dev settings
   - Never edit `config.yaml` except via PR to main
   - Use `.env.development.local` for secrets (gitignored)

3. **Testing**
   - Always test on development server first
   - Use separate dev database for testing
   - Don't test destructive operations on production

4. **Storage**
   - Dev outputs go to `/tmp/imagineer-dev/`
   - Never write to production storage during development
   - Clean up `/tmp/imagineer-dev/` periodically

5. **Services**
   - Production runs as systemd service
   - Development runs as local Flask process
   - Never restart production service manually

## Summary

| Task | Command | Server |
|------|---------|--------|
| Start development | `./run-dev.sh` | Dev (5000) |
| Stop development | `Ctrl+C` | Dev (5000) |
| Check dev status | `curl http://localhost:5000/api/health` | Dev (5000) |
| Check prod status | `curl http://localhost:10050/api/health` | Prod (10050) |
| View dev logs | Terminal output from `./run-dev.sh` | Dev (5000) |
| View prod logs | `sudo journalctl -u imagineer-api -f` | Prod (10050) |
| Deploy to production | Merge PR to `main` | CI/CD → Prod |

**Remember**: Production is sacred. Development is your playground. Never cross the streams! 👻
