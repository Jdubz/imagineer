# Deployment Documentation

**Last Updated:** 2025-11-05
**Status:** Consolidated and Current

This directory contains the essential deployment documentation for Imagineer's production architecture.

## Current Architecture

Imagineer uses a modern decoupled architecture:
- **Frontend:** Firebase Hosting (Global CDN)
- **Backend API:** Cloudflare Tunnel → Gunicorn (localhost:10050)
- **Authentication:** Google OAuth 2.0
- **No Nginx, No Celery, No external dependencies**

## Essential Documentation

### 1. [CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md) 📘 **START HERE**
Complete overview of the production architecture with diagrams, component details, and deployment workflows.

### 2. [FIREBASE_SETUP.md](FIREBASE_SETUP.md)
Firebase Hosting configuration, deployment commands, and environment variables for the React frontend.

### 3. [CLOUDFLARE_TUNNEL_SETUP.md](CLOUDFLARE_TUNNEL_SETUP.md)
Cloudflare Tunnel configuration for secure backend API access without exposing public IP.

### 4. [GOOGLE_OAUTH_SETUP.md](GOOGLE_OAUTH_SETUP.md)
Google OAuth 2.0 credential configuration for authentication.

### 5. [CREDENTIALS_QUICK_REFERENCE.md](CREDENTIALS_QUICK_REFERENCE.md)
Quick reference for all required API keys, secrets, and service account credentials.

## Deployment Quick Commands

```bash
# Frontend (Firebase Hosting)
cd web
npm run build
firebase deploy --only hosting

# Backend (Local Server)
sudo systemctl restart imagineer-api
sudo systemctl status imagineer-api

# Check Cloudflare Tunnel
sudo systemctl status cloudflared-imagineer-api
```

## What's NOT Here Anymore

The following were removed during the 2025-11-05 documentation consolidation:

### Obsolete Architecture Docs
- ❌ Nginx configuration (we use Cloudflare Tunnel + Firebase instead)
- ❌ Celery worker docs (we use Python threading instead)
- ❌ training-data subprocess docs (we use internal async scraping)

### Duplicate/Historical Docs (24 files archived)
- Planning documents for features now implemented
- Multiple overlapping deployment guides
- Historical status/summary documents
- Old architecture diagrams

**Archived to:** `archive/obsolete_2025-11-05/`

## Architecture Evolution

```
Old (Pre-Nov 2025):
┌─────────────┐
│   Server    │
│  ┌────────┐ │
│  │ Nginx  │ │ ← Served both frontend and API
│  └────────┘ │
│  ┌────────┐ │
│  │ Flask  │ │
│  └────────┘ │
└─────────────┘

Current (Nov 2025):
┌──────────────┐      ┌────────────────┐
│   Firebase   │      │   Cloudflare   │
│   Hosting    │      │     Tunnel     │
│  (Frontend)  │      │   (API Only)   │
└──────────────┘      └────────┬───────┘
                               │
                        ┌──────▼───────┐
                        │   Gunicorn   │
                        │  (localhost) │
                        └──────────────┘
```

## Related Documentation

- **Architecture:** [docs/ARCHITECTURE.md](../ARCHITECTURE.md) - System-wide architecture
- **Development:** [docs/guides/SETUP.md](../guides/SETUP.md) - Local development setup
- **CLI Commands:** [docs/guides/CLI_QUICK_REFERENCE.md](../guides/CLI_QUICK_REFERENCE.md) - Operational commands
- **Testing:** [docs/guides/TESTING.md](../guides/TESTING.md) - Test suite documentation

## Need Help?

1. Start with [CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md)
2. Check [CLAUDE.md](../../CLAUDE.md) for AI-assisted development context
3. Review service logs: `sudo journalctl -u imagineer-api -f`
4. Check Cloudflare Tunnel: `sudo journalctl -u cloudflared-imagineer-api -f`
