# Deployment Scripts

This directory contains scripts for setting up and managing the Imagineer production deployment.

## Quick Start

To deploy Imagineer to production, run:

```bash
cd /home/jdubz/Development/imagineer
bash scripts/RUN_THESE_COMMANDS.sh
```

This will install nginx, configure all services, and start everything.

## Scripts

### RUN_THESE_COMMANDS.sh

**Purpose:** Quick setup script to install and configure all production services.

**What it does:**
- Installs nginx web server
- Copies deployment configs to system locations
- Installs and enables systemd services
- Restarts all services
- Tests endpoints

**Usage:**
```bash
bash scripts/RUN_THESE_COMMANDS.sh
```

**Requirements:** sudo access (you'll be prompted for password)

**Time:** ~2-3 minutes

---

### setup-production-services.sh

**Purpose:** Comprehensive setup script with detailed output and validation.

**What it does:**
- Checks for existing installations
- Installs nginx if needed
- Configures nginx site
- Validates nginx configuration
- Installs systemd services for API and Cloudflare Tunnel
- Enables services for auto-start on boot
- Starts/restarts all services
- Tests all endpoints (local and public)
- Displays service status

**Usage:**
```bash
bash scripts/setup-production-services.sh
```

**Requirements:** sudo access

**Time:** ~3-5 minutes

---

### complete-setup.sh

**Purpose:** Alternative setup script with simplified output.

**What it does:**
- Similar to `setup-production-services.sh` but with less verbose output
- Focuses on essential steps
- Good for re-running setup after changes

**Usage:**
```bash
bash scripts/complete-setup.sh
```

**Requirements:** sudo access

**Time:** ~2-3 minutes

---

### test_all_loras.sh (in root directory)

**Purpose:** Test all LoRA models in the models directory.

**Location:** `/home/jdubz/Development/imagineer/test_all_loras.sh`

**What it does:**
- Iterates through all LoRA files in `/mnt/speedy/imagineer/models/lora/`
- Generates test images with each LoRA
- Saves results to `/mnt/speedy/imagineer/outputs/lora_tests/`

**Usage:**
```bash
./test_all_loras.sh
```

**Requirements:** Virtual environment activated, LoRA files available

## Configuration Files Used

All scripts reference configuration files in `config/deployment/`:

- **cloudflared-config.yml** - Cloudflare Tunnel routing rules
- **nginx-imagineer.conf** - nginx web server configuration
- **imagineer-api.service** - systemd service for Flask API
- **cloudflared-imagineer-api.service** - systemd service for Cloudflare Tunnel

## After Running Setup

### 1. Verify Services

Check that all services are running:

```bash
sudo systemctl status nginx imagineer-api cloudflared-imagineer-api
```

### 2. Test Endpoints

Local:
```bash
curl http://localhost:8080/health          # nginx
curl http://localhost:10050/api/health     # API
```

Public (wait 30 seconds for tunnel):
```bash
curl https://imagineer.joshwentworth.com/health
curl https://imagineer-api.joshwentworth.com/api/health
```

### 3. View Logs

If something isn't working:

```bash
sudo journalctl -u nginx -f
sudo journalctl -u imagineer-api -f
sudo journalctl -u cloudflared-imagineer-api -f
```

### 4. Configure GitHub Secrets

For auto-deployment to work, add these secrets to GitHub:

Go to: https://github.com/joshbwentworth/imagineer/settings/secrets/actions

- **SSH_PRIVATE_KEY** - Contents of `~/.ssh/imagineer_deploy`
- **SSH_HOST** - Your server IP (e.g., `192.168.86.35`)
- **SSH_USER** - `jdubz`

### 5. Test Auto-Deployment

```bash
# Make a change
git add .
git commit -m "test: Verify deployment"
git push origin main

# Watch deployment
# https://github.com/joshbwentworth/imagineer/actions
```

## Troubleshooting

### Services won't start

Check logs:
```bash
sudo journalctl -u <service-name> -n 50
```

Common issues:
- Port already in use
- Config file syntax error
- Missing environment variables

### Public endpoint not responding

1. Check tunnel status:
   ```bash
   cloudflared tunnel info imagineer-api
   ps aux | grep cloudflared
   ```

2. Wait 1-2 minutes for tunnel to establish connections

3. Check tunnel logs:
   ```bash
   sudo journalctl -u cloudflared-imagineer-api -f
   ```

### nginx errors

1. Test configuration:
   ```bash
   sudo nginx -t
   ```

2. Check if `public/` directory exists and has files:
   ```bash
   ls -la /home/jdubz/Development/imagineer/public/
   ```

3. Rebuild frontend if needed:
   ```bash
   cd web && npm run build && cd ..
   ```

### Permission errors

Make sure you're running scripts from the project root:
```bash
cd /home/jdubz/Development/imagineer
bash scripts/<script-name>.sh
```

## Re-running Scripts

It's safe to re-run any of these scripts. They will:
- Overwrite existing config files with latest versions
- Restart services to pick up changes
- Update systemd service definitions

This is useful after:
- Updating configuration files
- Pulling changes from git
- Modifying service definitions

## Manual Steps

If you prefer to run commands individually instead of using scripts:

```bash
# Install nginx
sudo apt update && sudo apt install -y nginx

# Copy configs
sudo cp config/deployment/nginx-imagineer.conf /etc/nginx/sites-available/imagineer
sudo ln -sf /etc/nginx/sites-available/imagineer /etc/nginx/sites-enabled/imagineer
sudo cp config/deployment/cloudflared-config.yml /etc/cloudflared/config.yml

# Install services
sudo cp config/deployment/imagineer-api.service /etc/systemd/system/
sudo cp config/deployment/cloudflared-imagineer-api.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable nginx imagineer-api cloudflared-imagineer-api
sudo systemctl restart nginx imagineer-api cloudflared-imagineer-api
```

## Documentation

For more detailed information:

- **Quick Start:** `docs/deployment/DEPLOYMENT_QUICK_START.md`
- **Complete Guide:** `docs/deployment/PRODUCTION_DEPLOYMENT_GUIDE.md`
- **Setup Instructions:** `docs/deployment/SETUP_INSTRUCTIONS.md`
- **Changes Summary:** `docs/deployment/DEPLOYMENT_CHANGES_SUMMARY.md`
