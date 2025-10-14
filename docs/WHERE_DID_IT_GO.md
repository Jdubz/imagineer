# Where Did My File Go?

Quick reference for finding files after the October 14, 2024 reorganization.

## 📄 Documentation Files Moved

### From Root → docs/deployment/

| Old Location | New Location |
|-------------|--------------|
| `/CLOUDFLARE_TUNNEL_SETUP.md` | `/docs/deployment/CLOUDFLARE_TUNNEL_SETUP.md` |
| `/CREDENTIALS_QUICK_REFERENCE.md` | `/docs/deployment/CREDENTIALS_QUICK_REFERENCE.md` |
| `/DEPLOYMENT_CHEATSHEET.md` | `/docs/deployment/DEPLOYMENT_CHEATSHEET.md` |
| `/DEPLOYMENT_ORCHESTRATION_COMPLETE.md` | `/docs/deployment/DEPLOYMENT_ORCHESTRATION_COMPLETE.md` |
| `/DEPLOYMENT_README.md` | `/docs/deployment/DEPLOYMENT_README.md` |
| `/FIREBASE_QUICKSTART.md` | `/docs/deployment/FIREBASE_QUICKSTART.md` |
| `/PRODUCTION_README.md` | `/docs/deployment/PRODUCTION_README.md` |

### From Root → docs/lora/

| Old Location | New Location |
|-------------|--------------|
| `/LORA_SETUP.md` | `/docs/lora/LORA_SETUP.md` |

### From docs/ → docs/guides/

| Old Location | New Location |
|-------------|--------------|
| `/docs/SETUP.md` | `/docs/guides/SETUP.md` |
| `/docs/TESTING.md` | `/docs/guides/TESTING.md` |
| `/docs/LINTING.md` | `/docs/guides/LINTING.md` |
| `/docs/CONTRIBUTING.md` | `/docs/guides/CONTRIBUTING.md` |
| `/docs/MAKEFILE_REFERENCE.md` | `/docs/guides/MAKEFILE_REFERENCE.md` |
| `/docs/NEXT_STEPS.md` | `/docs/guides/NEXT_STEPS.md` |

### From docs/ → docs/deployment/

| Old Location | New Location |
|-------------|--------------|
| `/docs/DEPLOYMENT_GUIDE.md` | `/docs/deployment/DEPLOYMENT_GUIDE.md` |
| `/docs/DEPLOYMENT_ORCHESTRATION.md` | `/docs/deployment/DEPLOYMENT_ORCHESTRATION.md` |
| `/docs/DEPLOYMENT_ORCHESTRATION_SUMMARY.md` | `/docs/deployment/DEPLOYMENT_ORCHESTRATION_SUMMARY.md` |
| `/docs/FIREBASE_CLOUDFLARE_DEPLOYMENT.md` | `/docs/deployment/FIREBASE_CLOUDFLARE_DEPLOYMENT.md` |
| `/docs/FIREBASE_SETUP.md` | `/docs/deployment/FIREBASE_SETUP.md` |
| `/docs/PRODUCTION_SETUP.md` | `/docs/deployment/PRODUCTION_SETUP.md` |
| `/docs/REQUIRED_CREDENTIALS.md` | `/docs/deployment/REQUIRED_CREDENTIALS.md` |
| `/docs/SECURE_AUTHENTICATION_PLAN.md` | `/docs/deployment/SECURE_AUTHENTICATION_PLAN.md` |
| `/docs/CLI_QUICK_REFERENCE.md` | `/docs/deployment/CLI_QUICK_REFERENCE.md` |

### From docs/ → docs/lora/

| Old Location | New Location |
|-------------|--------------|
| `/docs/LORA_ORGANIZATION.md` | `/docs/lora/LORA_ORGANIZATION.md` |
| `/docs/LORA_PREVIEW_GENERATION.md` | `/docs/lora/LORA_PREVIEW_GENERATION.md` |

---

## 🗑️ Scripts Removed (Use Makefile Instead)

| Old Script | New Command |
|-----------|-------------|
| `scripts/start_api.sh` | `make api` |
| `scripts/start_server.sh` | `make api` |
| `scripts/start_dev.sh` | `make dev` |
| `scripts/generate.sh` | `make generate PROMPT="..."` |
| `scripts/deploy/setup-cloudflare-tunnel.sh` | Use custom version |

**Why?** All functionality is available through well-documented Makefile targets. Run `make help` to see all commands.

---

## 🔍 Can't Find Something?

**Option 1: Use the Documentation Index**
```bash
# Open the comprehensive index
cat docs/INDEX.md
# Or view in browser/editor
```

**Option 2: Search by name**
```bash
# Find any documentation file
find docs -name "*KEYWORD*.md"

# Example: Find deployment docs
find docs -name "*DEPLOY*.md"
```

**Option 3: Search by content**
```bash
# Search all markdown files for a keyword
grep -r "keyword" docs/*.md
```

---

## 📚 New Files Created

| File | Description |
|------|-------------|
| `/docs/INDEX.md` | Complete documentation catalog |
| `/REORGANIZATION_SUMMARY.md` | Detailed reorganization summary |
| `/docs/WHERE_DID_IT_GO.md` | This file! |
| `/scripts/reorganize-project.sh` | Reorganization automation script |

---

## ✅ Quick Verification

Everything is working correctly if:

```bash
# Root only has essential files
ls *.md
# Shows: CLAUDE.md, README.md, REORGANIZATION_SUMMARY.md

# Docs are organized
ls docs/
# Shows: INDEX.md, ARCHITECTURE.md, API.md, deployment/, lora/, guides/

# Makefile commands work
make help
make api
make dev
```

---

## 🎯 Most Common Lookups

**"Where's the deployment guide?"**
→ `docs/deployment/DEPLOYMENT_ORCHESTRATION_COMPLETE.md` (start here)
→ `docs/deployment/DEPLOYMENT_CHEATSHEET.md` (quick reference)

**"Where's the credentials guide?"**
→ `docs/deployment/CREDENTIALS_QUICK_REFERENCE.md` (quick)
→ `docs/deployment/REQUIRED_CREDENTIALS.md` (complete)

**"Where's the LoRA documentation?"**
→ `docs/lora/` (all LoRA docs)

**"Where's the setup guide?"**
→ `docs/guides/SETUP.md`

**"Where's the API documentation?"**
→ `docs/API.md` (unchanged, still in docs/)

**"Where's the architecture doc?"**
→ `docs/ARCHITECTURE.md` (unchanged, still in docs/)

---

## 📖 Start Here

**If you're looking for documentation**, start with:
- **[docs/INDEX.md](INDEX.md)** - Complete catalog of all documentation

**If you want to deploy**, start with:
- **[docs/deployment/DEPLOYMENT_CHEATSHEET.md](deployment/DEPLOYMENT_CHEATSHEET.md)** - Quick commands

**If you're developing**, start with:
- **[README.md](../README.md)** - Updated with new structure

---

**Everything is still here, just better organized!** 🎉
