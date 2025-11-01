# Configuration Files

This directory contains configuration files for the Imagineer application.

## Structure

```
config/
└── deployment/          # Production deployment configurations
    ├── cloudflared-config.yml
    ├── cloudflared-imagineer-api.service
    ├── imagineer-api.service
    └── nginx-imagineer.conf
```

## Deployment Configuration

The `deployment/` subdirectory contains all files needed for production deployment.

### cloudflared-config.yml

**Purpose:** Cloudflare Tunnel routing configuration

**Location:** Copied to `/etc/cloudflared/config.yml` during setup

**What it does:**
- Routes traffic for `api.imagineer.joshwentworth.com` to the Flask API (localhost:10050)
- Provides a 404 fallback for any other host/path
- Uses tunnel ID: `db1a99dd-3d12-4315-b241-da2a55a5c30f`

**Key settings:**
```yaml
ingress:
  - hostname: api.imagineer.joshwentworth.com
    service: http://localhost:10050    # Flask API
```

---

> **Note:** The legacy nginx proxy (`nginx-imagineer.conf`) is no longer part of the production path because Firebase Hosting serves the SPA directly behind Cloudflare. Keep the file only if you plan to self-host the frontend again.

### imagineer-api.service

**Purpose:** systemd service definition for Flask API

**Location:** Copied to `/etc/systemd/system/imagineer-api.service` during setup

**What it does:**
- Manages Flask API as a systemd service
- Loads environment from `.env.production`
- Runs as user `jdubz`
- Auto-restarts on failure
- Logs to systemd journal

**Key settings:**
- Port: 10050
- Working directory: `/home/jdubz/Development/imagineer`
- Python: `venv/bin/python`
- Command: `server/api.py`

---

### cloudflared-imagineer-api.service

**Purpose:** systemd service definition for Cloudflare Tunnel

**Location:** Copied to `/etc/systemd/system/cloudflared-imagineer-api.service` during setup

**What it does:**
- Manages Cloudflare Tunnel as a systemd service
- Uses config from `/etc/cloudflared/config.yml`
- Runs as user `jdubz`
- Auto-restarts on failure
- Logs to systemd journal

**Key settings:**
- Config: `/etc/cloudflared/config.yml`
- Tunnel: `imagineer-api` (ID: db1a99dd-3d12-4315-b241-da2a55a5c30f)

## Usage

### Manual Installation

To manually install these configurations:

```bash
# Copy nginx config
sudo cp config/deployment/nginx-imagineer.conf /etc/nginx/sites-available/imagineer
sudo ln -sf /etc/nginx/sites-available/imagineer /etc/nginx/sites-enabled/imagineer

# Copy cloudflared config
sudo cp config/deployment/cloudflared-config.yml /etc/cloudflared/config.yml

# Copy systemd services
sudo cp config/deployment/imagineer-api.service /etc/systemd/system/
sudo cp config/deployment/cloudflared-imagineer-api.service /etc/systemd/system/

# Reload and restart
sudo systemctl daemon-reload
sudo nginx -t && sudo systemctl restart nginx
sudo systemctl restart imagineer-api cloudflared-imagineer-api
```

### Automated Installation

Use the setup scripts in `scripts/`:

```bash
bash scripts/RUN_THESE_COMMANDS.sh
```

## Modifying Configurations

### Changing Ports

**API Port (currently 10050):**
1. Update `cloudflared-config.yml` ingress rule
2. Update `imagineer-api.service` (if it references the port)
3. Update `.env.production` with `FLASK_RUN_PORT`

**nginx Port (currently 8080):**
1. Update `nginx-imagineer.conf` listen directive
2. Update `cloudflared-config.yml` ingress service URL

**Important:** After changing ports, restart affected services:
```bash
sudo systemctl restart nginx imagineer-api cloudflared-imagineer-api
```

### Changing Paths

**Public Directory (React build):**
1. Update `nginx-imagineer.conf` root directive
2. Update GitHub Actions workflow deployment path

**API Working Directory:**
1. Update `imagineer-api.service` WorkingDirectory
2. Update GitHub Actions deployment scripts

### Adding Security Headers

Edit `nginx-imagineer.conf` and add headers in the `server` block:

```nginx
add_header Header-Name "value" always;
```

Then test and reload:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

### Changing Tunnel Routing

Edit `cloudflared-config.yml` ingress rules:

```yaml
ingress:
  - hostname: your-domain.com
    path: /pattern/*
    service: http://localhost:port
```

Then restart:
```bash
sudo systemctl restart cloudflared-imagineer-api
```

## Testing Configuration

### Test nginx Config

```bash
sudo nginx -t
```

### Test Service Syntax

```bash
sudo systemd-analyze verify config/deployment/imagineer-api.service
sudo systemd-analyze verify config/deployment/cloudflared-imagineer-api.service
```

### Test Cloudflared Config

```bash
cloudflared tunnel --config config/deployment/cloudflared-config.yml ingress validate
```

## Troubleshooting

### nginx won't start

1. Check syntax: `sudo nginx -t`
2. Check port not in use: `sudo lsof -i :8080`
3. Check permissions on public/: `ls -la public/`

### API service won't start

1. Check logs: `sudo journalctl -u imagineer-api -n 50`
2. Check environment file exists: `ls -la .env.production`
3. Check Python path: `which python` (should be venv/bin/python)
4. Test manually: `venv/bin/python server/api.py`

### Cloudflared service won't start

1. Check logs: `sudo journalctl -u cloudflared-imagineer-api -n 50`
2. Check config exists: `ls -la /etc/cloudflared/config.yml`
3. Check credentials: `ls -la ~/.cloudflared/*.json`
4. Test manually: `cloudflared tunnel --config /etc/cloudflared/config.yml run`

### Changes not taking effect

After modifying configs:

1. **nginx:** `sudo nginx -t && sudo systemctl reload nginx`
2. **systemd services:** `sudo systemctl daemon-reload && sudo systemctl restart <service>`
3. **cloudflared:** `sudo systemctl restart cloudflared-imagineer-api`

## Related Documentation

- **Setup Scripts:** `scripts/README.md`
- **Deployment Guide:** `docs/deployment/PRODUCTION_DEPLOYMENT_GUIDE.md`
- **Architecture:** `docs/ARCHITECTURE.md`
- **Project Organization:** `docs/PROJECT_ORGANIZATION.md`
