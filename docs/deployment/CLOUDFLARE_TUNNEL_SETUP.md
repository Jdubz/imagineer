# Cloudflare Tunnel Setup - imagineer.joshwentworth.com

Quick guide for setting up your Cloudflare Tunnel.

## 🚀 Quick Setup

### Step 1: Setup Cloudflare Tunnel

```bash
# Run the custom setup script
bash scripts/deploy/setup-cloudflare-tunnel-custom.sh
```

This will:
1. Install `cloudflared` (if needed)
2. Authenticate with Cloudflare
3. Create tunnel named `imagineer-api`
4. Configure tunnel for `imagineer.joshwentworth.com`
5. Create and start systemd service

**Save the Tunnel ID** that's displayed at the end!

### Step 2: Get Cloudflare API Token

1. Go to: https://dash.cloudflare.com/profile/api-tokens
2. Click **Create Token**
3. Use template: **Edit zone DNS**
4. Or create custom token with:
   - Zone.DNS: Edit
   - Zone.Firewall Services: Edit
   - Zone: `joshwentworth.com`
5. Copy the token

### Step 3: Update Terraform Configuration

Edit `terraform/terraform.tfvars`:

```bash
# Add your Cloudflare API token
cloudflare_api_token = "YOUR_TOKEN_HERE"

# Add the tunnel ID (from step 1)
tunnel_id = "YOUR_TUNNEL_ID_HERE"

# Domain is already configured
domain = "joshwentworth.com"
api_subdomain = "imagineer"
```

### Step 4: Deploy Cloudflare Infrastructure

```bash
# This will create DNS records and firewall rules
make deploy-infra
```

### Step 5: Verify Everything Works

```bash
# Check tunnel status
sudo systemctl status cloudflared-imagineer-api

# Test local API
curl http://localhost:10050/api/health

# Wait 1-2 minutes for DNS propagation, then test public API
curl https://imagineer.joshwentworth.com/api/health
```

---

## 🔧 Configuration Details

**Domain:** `imagineer.joshwentworth.com`
**Tunnel Name:** `imagineer-api`
**Local Backend:** `http://127.0.0.1:10050`

**What gets created:**
- DNS CNAME: `imagineer.joshwentworth.com` → Cloudflare Tunnel
- Rate limiting rules
- WAF protection
- Security headers

---

## 📝 Management Commands

```bash
# Status
sudo systemctl status cloudflared-imagineer-api

# Logs (real-time)
sudo journalctl -u cloudflared-imagineer-api -f

# Restart
sudo systemctl restart cloudflared-imagineer-api

# Stop
sudo systemctl stop cloudflared-imagineer-api

# Start
sudo systemctl start cloudflared-imagineer-api
```

---

## 🧪 Testing

```bash
# 1. Test local backend
curl http://localhost:10050/api/health

# 2. Check tunnel service
sudo systemctl status cloudflared-imagineer-api

# 3. Test public endpoint (after DNS propagates)
curl https://imagineer.joshwentworth.com/api/health

# 4. Test from browser
# Visit: https://imagineer-generator.web.app
# Should connect to API at https://imagineer.joshwentworth.com
```

---

## 🔐 Update Frontend

The frontend configuration has been updated to use your domain:

**File:** `web/.env.production`
```bash
VITE_API_BASE_URL=https://imagineer.joshwentworth.com/api
```

After deploying the frontend, it will automatically connect to your API through the tunnel.

---

## 🐛 Troubleshooting

**Tunnel not connecting:**
```bash
# Check tunnel status
cloudflared tunnel list
cloudflared tunnel info imagineer-api

# Check service logs
sudo journalctl -u cloudflared-imagineer-api -n 50

# Restart tunnel
sudo systemctl restart cloudflared-imagineer-api
```

**DNS not resolving:**
```bash
# Check DNS
dig imagineer.joshwentworth.com

# Verify Terraform created the record
cd terraform
terraform show | grep imagineer

# Check Cloudflare dashboard
# https://dash.cloudflare.com/
# Select joshwentworth.com → DNS → Records
```

**502 Bad Gateway:**
```bash
# Make sure backend is running
curl http://localhost:10050/api/health

# Check backend service
make prod-status

# Restart backend
make prod-restart
```

---

## 📋 Complete Setup Checklist

- [ ] Run tunnel setup script
- [ ] Get Cloudflare API token
- [ ] Update `terraform/terraform.tfvars` with token and tunnel ID
- [ ] Run `make deploy-infra`
- [ ] Verify tunnel is running
- [ ] Test local API endpoint
- [ ] Wait for DNS propagation (1-2 minutes)
- [ ] Test public API endpoint
- [ ] Deploy frontend: `make deploy-frontend-prod`
- [ ] Test end-to-end from frontend

---

## 🌐 Your URLs

**API Endpoint:**
- https://imagineer.joshwentworth.com/api/health
- https://imagineer.joshwentworth.com/api/generate
- https://imagineer.joshwentworth.com/api/jobs

**Frontend:**
- https://imagineer-generator.web.app
- https://imagineer-generator.firebaseapp.com

**Cloudflare Dashboard:**
- https://dash.cloudflare.com/

---

## 🔗 Related Documentation

- **Complete Guide:** [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)
- **Production Setup:** [PRODUCTION_README.md](PRODUCTION_README.md)
- **Firebase Setup:** [FIREBASE_QUICKSTART.md](FIREBASE_QUICKSTART.md)

---

**Quick Reference:**

```bash
# Setup tunnel
bash scripts/deploy/setup-cloudflare-tunnel-custom.sh

# Deploy infrastructure
make deploy-infra

# Check status
sudo systemctl status cloudflared-imagineer-api

# View logs
sudo journalctl -u cloudflared-imagineer-api -f

# Test
curl https://imagineer.joshwentworth.com/api/health
```
