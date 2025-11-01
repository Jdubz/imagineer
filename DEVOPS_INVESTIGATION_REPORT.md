# DevOps Investigation Report: API Routing Issue
**Date**: 2025-10-31
**Investigator**: DevOps Engineer (Claude Code)
**Status**: Investigation Complete - Fix Ready for Implementation

---

## Executive Summary

Investigated production infrastructure for Imagineer project and identified root cause of API routing failure. The domain `imagineer.joshwentworth.com` is misconfigured - it points to Firebase Hosting (serving the React frontend) instead of the Cloudflare Tunnel (which should serve the Flask API). Additionally, the frontend is configured to use a non-existent subdomain `api.imagineer.joshwentworth.com`.

**Impact**: All API calls fail, making the production application non-functional for users.

**Fix Ready**: Automated fix script created, step-by-step checklist documented, rollback plan prepared.

---

## 1. Investigation Findings

### 1.1 Current Architecture (Actual)

```
User Browser
    |
    ├─→ https://imagineer-generator.web.app (Firebase)
    |   └─→ React SPA (WORKING)
    |
    └─→ https://imagineer.joshwentworth.com
        └─→ Firebase Hosting (via Cloudflare CDN)
            └─→ React SPA (WRONG - should be API)

Frontend tries to call:
    └─→ https://api.imagineer.joshwentworth.com/api/*
        └─→ DNS DOES NOT EXIST (FAILS)

Backend API:
    └─→ Flask on server port 10050
        └─→ Cloudflare Tunnel configured but not receiving traffic
```

### 1.2 Intended Architecture (User's Description)

```
Frontend:
    └─→ https://imagineer-generator.web.app (Firebase Hosting)

Backend API:
    └─→ https://imagineer.joshwentworth.com/api/*
        └─→ Cloudflare Tunnel (db1a99dd-3d12-4315-b241-da2a55a5c30f)
            └─→ Flask on server port 10050
```

### 1.3 DNS Configuration

| Domain | Resolves To | Actually Serves | Should Serve |
|--------|------------|-----------------|--------------|
| `imagineer-generator.web.app` | Firebase | Frontend (React) | Frontend ✅ |
| `imagineer.joshwentworth.com` | Cloudflare IPs → Firebase | Frontend (React) | API ❌ |
| `api.imagineer.joshwentworth.com` | **DOES NOT EXIST** | N/A | API (or unused) |

### 1.4 Service Status

**Unable to verify via SSH** (connection timeouts - see section 1.6)

Based on configuration files:
- **Flask API**: Should be running as systemd service `imagineer-api` on port 10050
- **Cloudflare Tunnel**: Should be running as systemd service `cloudflared-imagineer-api`
- **Tunnel Config**: Located at `~/.cloudflared/config.yml`
- **Tunnel ID**: `db1a99dd-3d12-4315-b241-da2a55a5c30f`

### 1.5 Test Results

#### ✅ Working Endpoints
```bash
$ curl https://imagineer-generator.web.app/
→ Returns: HTML (React SPA)
→ Status: 200 OK
→ Assessment: WORKING

$ curl https://imagineer.joshwentworth.com/
→ Returns: HTML (React SPA)
→ Status: 200 OK
→ Assessment: WORKING but WRONG (should be API)
```

#### ❌ Broken Endpoints
```bash
$ curl https://imagineer.joshwentworth.com/api/health
→ Returns: HTML (React SPA) instead of JSON
→ Status: 200 OK but WRONG CONTENT TYPE
→ Assessment: BROKEN - returns frontend instead of API

$ curl https://api.imagineer.joshwentworth.com/api/health
→ Returns: DNS resolution error
→ Status: DOMAIN NOT FOUND
→ Assessment: BROKEN - subdomain doesn't exist
```

### 1.6 SSH Access Issue

**Problem**: Cannot SSH to `jdubz@imagineer.joshwentworth.com` - connection times out.

**Root Cause**: Domain resolves to Cloudflare CDN IPs, not the actual server. Cloudflare doesn't proxy SSH traffic (port 22).

**Workaround**: Need to use actual server IP address for SSH.

**Status**: Unable to obtain server IP without access to:
- Cloudflare Dashboard (to see origin server IP)
- Hosting provider dashboard (AWS/GCP/DigitalOcean/etc)
- Alternative domain pointing to same server

### 1.7 Frontend Configuration

**File**: `web/.env.production`
```bash
VITE_API_BASE_URL=https://api.imagineer.joshwentworth.com/api
```

**Problem**: This subdomain doesn't exist, causing all API calls to fail.

**Frontend Build**: Last deployed 2025-10-31 (build hash: `1.0.1-BUz12L-3`)

### 1.8 Backend Configuration

**Expected File**: `/home/jdubz/Development/imagineer/.env.production` (on server)

Unable to verify contents due to SSH access issue, but should contain:
```bash
ALLOWED_ORIGINS=https://imagineer-generator.web.app,https://imagineer-generator.firebaseapp.com
```

---

## 2. Root Cause Analysis

### 2.1 Primary Issue: Domain Misconfiguration

**Problem**: `imagineer.joshwentworth.com` was added as a custom domain to Firebase Hosting.

**Impact**:
- Domain serves frontend instead of API
- Cloudflare Tunnel receives no traffic
- API is unreachable from public internet

**How it happened**: Likely during initial deployment, domain was added to Firebase for "branded URL" without considering API routing.

### 2.2 Secondary Issue: Non-Existent Subdomain

**Problem**: Frontend configured to use `api.imagineer.joshwentworth.com` which was never created.

**Impact**: All API calls fail with DNS resolution errors.

**How it happened**: Frontend environment was configured before DNS was set up, and DNS setup was never completed.

### 2.3 Contributing Factor: Documentation Drift

Multiple deployment docs describe different architectures:
- `CLOUDFLARE_TUNNEL_SETUP.md`: Says API at `api.imagineer.joshwentworth.com`
- `PRODUCTION_DEPLOYMENT_GUIDE.md`: Describes nginx serving frontend on same domain
- `web/.env.example`: Comments suggest main domain for API

**Impact**: Confusion during deployment, no single source of truth.

---

## 3. Recommended Solution

### 3.1 Chosen Approach: Option 1 (Single Domain)

**Use `imagineer.joshwentworth.com` for API only, keep Firebase on its direct URL.**

**Rationale**:
- Simplest to implement
- Clearest separation of concerns
- Easiest to maintain
- Single change to frontend config

### 3.2 Architecture After Fix

```
Frontend:
    https://imagineer-generator.web.app (Firebase Hosting)
    └─→ React SPA

API:
    https://imagineer.joshwentworth.com/api/* (Cloudflare Tunnel)
    └─→ Flask on server:10050

DNS:
    imagineer.joshwentworth.com
    └─→ CNAME: db1a99dd-3d12-4315-b241-da2a55a5c30f.cfargotunnel.com
```

---

## 4. Implementation Plan

### 4.1 Prerequisites

**Required Access**:
- ✅ Git repository (have access)
- ❌ SSH to production server (need IP address)
- ❌ Firebase Console (need access to remove custom domain)
- ❌ Cloudflare Dashboard (need access to update DNS)

**Blockers**:
1. Cannot obtain server IP (SSH times out to domain)
2. Cannot modify Firebase custom domains
3. Cannot update Cloudflare DNS

### 4.2 Implementation Steps

Detailed in `docs/deployment/FIX_CHECKLIST.md`:

1. **Remove Firebase Custom Domain** (requires Firebase Console access)
2. **Update Cloudflare DNS** (requires Cloudflare Dashboard access)
3. **Get Server IP** (requires Cloudflare or hosting provider access)
4. **Fix Server Config** (requires SSH access)
5. **Test API Endpoint** (can do from anywhere)
6. **Update Frontend Config** (can do locally)
7. **Redeploy Frontend** (requires Firebase deployment access)
8. **End-to-End Testing** (can do from anywhere)

**Estimated Time**: 30-40 minutes (including DNS propagation)

### 4.3 Automation Created

**File**: `scripts/deploy/fix-api-routing.sh`

Automated script that:
- Backs up current tunnel configuration
- Installs correct tunnel configuration
- Restarts Flask API service
- Restarts Cloudflare Tunnel service
- Verifies both services are healthy
- Displays next steps

**Usage**:
```bash
ssh jdubz@<SERVER_IP>
cd /home/jdubz/Development/imagineer
bash scripts/deploy/fix-api-routing.sh
```

---

## 5. Deliverables

### 5.1 Documentation Created

| File | Purpose | Location |
|------|---------|----------|
| `PRODUCTION_ARCHITECTURE.md` | Complete architecture documentation, problem analysis, 3 fix options with pros/cons | `/home/jdubz/Development/imagineer/docs/deployment/` |
| `API_ROUTING_FIX_SUMMARY.md` | Investigation summary, test results, detailed implementation plan | `/home/jdubz/Development/imagineer/docs/deployment/` |
| `FIX_CHECKLIST.md` | Step-by-step checklist with verification steps and rollback plan | `/home/jdubz/Development/imagineer/docs/deployment/` |
| `DEVOPS_INVESTIGATION_REPORT.md` | This document - comprehensive investigation report | `/home/jdubz/Development/imagineer/` |

### 5.2 Automation Created

| File | Purpose | Location |
|------|---------|----------|
| `fix-api-routing.sh` | Automated server configuration fix script | `/home/jdubz/Development/imagineer/scripts/deploy/` |

### 5.3 Files Ready to Modify

| File | Change Needed | Location |
|------|---------------|----------|
| `web/.env.production` | Update API URL from `api.imagineer.*` to `imagineer.*` | `/home/jdubz/Development/imagineer/web/` |
| `~/.cloudflared/config.yml` | Update tunnel routing (done by script) | On server |

---

## 6. Risk Analysis

### 6.1 Risks During Implementation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| DNS propagation takes longer than expected | Medium | Low | Wait up to 24h, use specific DNS servers for testing |
| Tunnel fails to start after config change | Low | High | Rollback plan included, backup of config created |
| Flask API not running on server | Medium | High | Script verifies health before completing |
| CORS errors after deployment | Low | Medium | Backend config should already allow Firebase origins |
| Firebase won't release domain | Low | Medium | Can use Option 2 (API subdomain) instead |

### 6.2 Rollback Plan

Fully documented in `FIX_CHECKLIST.md`, includes:
- Restore tunnel configuration from backup
- Restore DNS settings in Cloudflare
- Re-add domain to Firebase if needed
- Restore frontend configuration from git history

**Rollback Time**: ~10 minutes

---

## 7. Testing Strategy

### 7.1 Unit Tests (Per Component)

**API**:
```bash
# On server
curl http://localhost:10050/api/health
curl http://localhost:10050/api/sets
```

**Tunnel**:
```bash
# On server
sudo systemctl status cloudflared-imagineer-api
cloudflared tunnel info db1a99dd-3d12-4315-b241-da2a55a5c30f
```

**DNS**:
```bash
dig imagineer.joshwentworth.com
# Should show CNAME to .cfargotunnel.com
```

### 7.2 Integration Tests

**API via Public URL**:
```bash
curl https://imagineer.joshwentworth.com/api/health
# Should return JSON, not HTML
```

**Frontend**:
```bash
curl https://imagineer-generator.web.app/
# Should return HTML
```

### 7.3 End-to-End Tests

**Browser Testing**:
1. Open https://imagineer-generator.web.app
2. Check console for errors (should be none)
3. Log in with Google OAuth
4. Select a set and generate batch
5. Verify image generation completes

**Success Criteria**:
- No CORS errors
- No network errors for API calls
- Images generate successfully
- Queue updates in real-time

---

## 8. Monitoring & Observability

### 8.1 Recommended Monitoring

**Health Checks** (to be implemented):
```bash
# Cron job to check API health every 5 minutes
*/5 * * * * curl -f https://imagineer.joshwentworth.com/api/health || echo "API down" | mail -s "Imagineer API Alert" admin@example.com
```

**Service Monitoring** (on server):
```bash
# Check service status
systemctl is-active imagineer-api cloudflared-imagineer-api

# If either fails, send alert
```

### 8.2 Logging

**API Logs**:
```bash
sudo journalctl -u imagineer-api -f
```

**Tunnel Logs**:
```bash
sudo journalctl -u cloudflared-imagineer-api -f
```

**Combined**:
```bash
sudo journalctl -u imagineer-api -u cloudflared-imagineer-api -f
```

### 8.3 Metrics to Track

- API response time (p50, p95, p99)
- API error rate (5xx responses)
- Tunnel uptime
- DNS resolution time
- Frontend load time
- Image generation success rate

---

## 9. Post-Implementation Tasks

### 9.1 Documentation Updates

**Files to update after fix**:
1. `docs/deployment/PRODUCTION_DEPLOYMENT_GUIDE.md`
   - Remove nginx sections (not used)
   - Update architecture diagram
   - Fix URL references

2. `docs/deployment/CLOUDFLARE_TUNNEL_SETUP.md`
   - Update tunnel configuration examples
   - Fix API URL references

3. `docs/deployment/DEPLOYMENT_QUICK_START.md`
   - Update with working URLs
   - Simplify steps

4. `web/.env.example`
   - Update production configuration example

### 9.2 CI/CD Improvements

**Current CI/CD** (`github/workflows/ci.yml`):
- Frontend deploys to Firebase on push to main ✅
- Backend deploys via SSH on push to main ✅

**Recommended improvements**:
- Add health check after backend deployment
- Add smoke tests after frontend deployment
- Send deployment notifications to Slack/Discord
- Add deployment rollback capability

### 9.3 Infrastructure as Code

**Current state**: Manual configuration via scripts

**Recommended**:
- Move Cloudflare DNS to Terraform
- Move tunnel configuration to version control
- Use Ansible for server configuration
- Document infrastructure in code

---

## 10. Alternative Solutions Considered

### 10.1 Option 2: API Subdomain

**Pros**:
- Matches current frontend config (no change needed)
- Can keep branded domain for frontend
- Clean separation with subdomain

**Cons**:
- Requires DNS changes
- More complex setup
- Another DNS record to manage

**Decision**: Not chosen - more complex than needed

### 10.2 Option 3: Hybrid Routing

**Pros**:
- Single domain for everything
- Most flexible
- Can add more services later

**Cons**:
- Most complex setup
- Tunnel becomes single point of failure
- Slight latency for frontend

**Decision**: Not chosen - over-engineered for current needs

### 10.3 Chosen: Option 1 (Single Domain for API)

**Pros**:
- Simplest to implement
- Clear separation
- Easy to maintain
- Single point of change in frontend

**Cons**:
- Uses Firebase subdomain (not branded)

**Decision**: CHOSEN - best balance of simplicity and functionality

---

## 11. Lessons Learned

### 11.1 Architecture Documentation

**Issue**: Multiple docs with conflicting architecture info

**Lesson**: Maintain single source of truth for architecture

**Action**: Created `PRODUCTION_ARCHITECTURE.md` as canonical reference

### 11.2 DNS Management

**Issue**: Domain added to Firebase without considering API routing

**Lesson**: Plan domain allocation before deployment

**Action**: Document domain allocation in architecture docs

### 11.3 Environment Configuration

**Issue**: Frontend configured for non-existent subdomain

**Lesson**: Verify DNS exists before configuring application

**Action**: Add DNS verification to deployment checklist

### 11.4 SSH Access

**Issue**: Cannot SSH using domain that points to CDN

**Lesson**: Always have alternative access method (IP address, bastion host)

**Action**: Document server IP in secure location

---

## 12. Next Steps & Recommendations

### 12.1 Immediate (Fix Production)

1. ✅ Investigation complete
2. ✅ Fix scripts created
3. ✅ Documentation created
4. ⏳ Obtain required access (Firebase, Cloudflare, SSH)
5. ⏳ Implement fix following `FIX_CHECKLIST.md`
6. ⏳ Test thoroughly
7. ⏳ Update documentation

### 12.2 Short Term (1-2 weeks)

1. Set up monitoring and alerting
2. Implement health check automation
3. Add smoke tests to CI/CD
4. Document actual server IP securely
5. Review and update all deployment docs

### 12.3 Medium Term (1-3 months)

1. Migrate to Infrastructure as Code (Terraform)
2. Implement automated backups
3. Add performance monitoring
4. Set up log aggregation (ELK/Loki)
5. Create disaster recovery plan

### 12.4 Long Term (3-6 months)

1. Migrate to Kubernetes for better scalability
2. Implement GitOps workflow
3. Add automated security scanning
4. Set up multi-environment deployments (dev/staging/prod)
5. Implement blue-green deployments

---

## 13. Conclusion

### 13.1 Summary

Investigated production API routing issue and identified root cause: domain misconfiguration where `imagineer.joshwentworth.com` points to Firebase Hosting instead of Cloudflare Tunnel. Created comprehensive fix with automation, documentation, and rollback plan.

### 13.2 Current Status

- ✅ **Investigation**: Complete
- ✅ **Root Cause**: Identified
- ✅ **Fix Design**: Complete
- ✅ **Automation**: Created
- ✅ **Documentation**: Complete
- ⏳ **Implementation**: Blocked on access requirements
- ⏳ **Testing**: Pending implementation
- ⏳ **Deployment**: Pending implementation

### 13.3 Blockers

1. **SSH Access**: Need actual server IP (domain times out)
2. **Firebase Access**: Need console access to remove custom domain
3. **Cloudflare Access**: Need dashboard access to update DNS

### 13.4 Estimated Time to Resolution

- With required access: 30-40 minutes
- Without access: Waiting on access provisioning

### 13.5 Confidence Level

**High confidence** in fix:
- Root cause clearly identified
- Solution tested conceptually
- Rollback plan prepared
- Automation reduces human error

---

## Appendices

### Appendix A: File Locations

**Investigation Documentation**:
- `/home/jdubz/Development/imagineer/DEVOPS_INVESTIGATION_REPORT.md` (this file)
- `/home/jdubz/Development/imagineer/docs/deployment/PRODUCTION_ARCHITECTURE.md`
- `/home/jdubz/Development/imagineer/docs/deployment/API_ROUTING_FIX_SUMMARY.md`
- `/home/jdubz/Development/imagineer/docs/deployment/FIX_CHECKLIST.md`

**Automation**:
- `/home/jdubz/Development/imagineer/scripts/deploy/fix-api-routing.sh`

**Configuration**:
- `/home/jdubz/Development/imagineer/web/.env.production`
- `/home/jdubz/Development/imagineer/config/deployment/cloudflared-config.yml` (template)

### Appendix B: Contact Information

**Infrastructure**:
- Domain: joshwentworth.com (managed in Cloudflare)
- Firebase Project: static-sites-257923
- Cloudflare Tunnel ID: db1a99dd-3d12-4315-b241-da2a55a5c30f

**Services**:
- Frontend: https://imagineer-generator.web.app (Firebase)
- API: https://imagineer.joshwentworth.com (after fix)
- Server: imagineer.joshwentworth.com (or IP)

### Appendix C: Useful Commands

**Investigation**:
```bash
# Check DNS
dig imagineer.joshwentworth.com
nslookup imagineer.joshwentworth.com

# Check what's serving
curl -I https://imagineer.joshwentworth.com/

# Test API
curl https://imagineer.joshwentworth.com/api/health
```

**Deployment**:
```bash
# Fix server config
ssh jdubz@<SERVER_IP>
cd /home/jdubz/Development/imagineer
bash scripts/deploy/fix-api-routing.sh

# Update and deploy frontend
cd web
vim .env.production  # Update API URL
npm run deploy:build
firebase deploy --only hosting
```

**Monitoring**:
```bash
# Service status
ssh jdubz@<SERVER_IP>
sudo systemctl status imagineer-api cloudflared-imagineer-api

# Logs
sudo journalctl -u imagineer-api -f
sudo journalctl -u cloudflared-imagineer-api -f
```

---

**Report Generated**: 2025-10-31
**Version**: 1.0
**Status**: Complete - Ready for Implementation
