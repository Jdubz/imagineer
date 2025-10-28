# Next Steps - Imagineer

**Last Updated:** October 15, 2025

---

## 🔴 Critical (Before Public Release)

**All critical tasks completed!** ✅

~~1. Fix basic_inference.py Compatibility~~ ✅ **COMPLETED**
- Fixed dependency versions: `diffusers==0.30.3`, `transformers==4.40.0`
- Updated `requirements.txt` with working versions

~~2. Test Image Generation End-to-End~~ ✅ **COMPLETED**
- Successfully generated test image
- Generation time: ~4 seconds at 6.10 it/s
- All parameters working (seed, steps, guidance, etc.)

~~3. Update GitHub Repository URL~~ ✅ **COMPLETED**
- Updated README.md to use `https://github.com/Jdubz/imagineer.git`
- Updated issue tracker and discussions links

---

## 🟡 High Priority (First Week)

### 4. Clean Up Local Directories
**Task:** Convert models/ and outputs/ to symlinks (like checkpoints)
**Space to Free:** 4.3GB
**Commands:**
```bash
rm -rf models outputs
ln -s /mnt/speedy/imagineer/models models
ln -s /mnt/speedy/imagineer/outputs outputs
```

### 5. Add Screenshots to README
**Task:** Add visual examples of the web UI
**Recommended:**
- Screenshot of the generation form with controls
- Screenshot of the image gallery
- Example of generated image with metadata modal

### 6. Create Initial GitHub Release
**Task:** Tag version v1.0.0-mvp
**Commands:**
```bash
git tag -a v1.0.0-mvp -m "MVP Release - Complete AI Image Generation System"
git push origin v1.0.0-mvp
```

### 7. Test on Fresh Install
**Task:** Verify setup instructions work for new users
**Test:** Follow README.md on a clean system or VM

---

## 🟠 Authentication & Management Features (High Priority)

### 8. Implement Google OAuth with Role-Based Access Control

**Status:** Planned
**Estimated Time:** 8-12 hours
**Priority:** High - Required for production deployment with multiple users
**Replaces:** Current password gate (v1.0) with proper authentication

#### Overview
Upgrade from simple password gate to Google OAuth with role-based access control, enabling proper user management and editor-level permissions for administrative tasks. Leverages existing Cloudflare Tunnel for HTTPS - no Firebase required!

#### Why Google OAuth (Not Firebase)?

Since we already have Cloudflare Tunnel providing HTTPS to our backend:
- **Simpler:** No Firebase dependency, just Google OAuth
- **Faster:** ~8-12 hours vs 14-19 hours
- **More Control:** All auth logic on our server
- **Free:** No Firebase quotas or billing
- **Better for our setup:** Direct backend auth flow

#### Phase 1: Backend Google OAuth Setup (2-3 hours)

**Tasks:**
- Install OAuth dependencies (`authlib`, `flask-login`)
- Create Google OAuth client configuration
- Implement OAuth callback route and session management
- Create role definitions and permissions system
- Add user roles JSON file for editor account assignments
- Implement auth middleware decorators (`@require_auth`, `@require_role('editor')`)
- Create admin endpoints for user management

**Files to Create:**
- `server/auth.py` - OAuth flow, session management, role checking
- `server/users.json` - User roles database (simple JSON file)

**Files to Modify:**
- `requirements.txt` (add `authlib`, `flask-login`)
- `server/api.py` (add auth routes and middleware)

**New API Endpoints:**
- `GET /auth/login` - Redirect to Google OAuth
- `GET /auth/google/callback` - OAuth callback handler
- `GET /auth/logout` - End session
- `GET /auth/me` - Get current user info
- `POST /api/admin/users/:email/role` - Assign editor role (admin only)
- `GET /api/admin/users` - List users with roles (admin only)
- `DELETE /api/admin/users/:email` - Remove user access (admin only)

#### Phase 2: Frontend OAuth Integration (1-2 hours)

**Tasks:**
- Replace PasswordGate with simple login button
- Redirect to backend OAuth flow
- Handle OAuth callback and session
- Display user info and logout button
- Check user role from backend

**Files to Create:**
- `web/src/components/AuthGate.jsx` - Replacement for PasswordGate

**Files to Modify:**
- `web/src/App.jsx` (use new AuthGate)

**Files to Delete:**
- `web/src/components/PasswordGate.jsx`
- `web/src/styles/PasswordGate.css`

#### Phase 3: LoRA Management UI (3-4 hours)

**Tasks:**
- Enhance existing LorasTab with editor-only features
- Add drag-and-drop LoRA file upload (.safetensors)
- Enable delete functionality for LoRA models
- Allow editing LoRA metadata (name, description, default weight)
- Add preview regeneration button
- Implement backend upload/delete/update routes

**Files to Create:**
- `web/src/components/LoraUpload.jsx` - Upload component with progress bar

**Files to Modify:**
- `web/src/components/LorasTab.jsx` - Add editor features
- `server/api.py` - Add management endpoints

**New API Endpoints (Editor Only):**
- `POST /api/loras/upload` - Upload new LoRA file
- `DELETE /api/loras/:folder` - Delete LoRA model
- `PUT /api/loras/:folder` - Update LoRA metadata
- `POST /api/loras/:folder/regenerate-preview` - Regenerate preview image

#### Phase 4: Training Data Management UI (3-4 hours)

**Tasks:**
- Create new TrainingDataTab component
- Build dataset manager interface
- Enable uploading training images with captions
- Allow creating and organizing datasets
- Provide caption editing interface (.txt files)
- Implement dataset preview functionality

**Files to Create:**
- `web/src/components/TrainingDataTab.jsx` - Main training data interface
- `web/src/components/DatasetManager.jsx` - Dataset management component

**Files to Modify:**
- `web/src/App.jsx` - Add TrainingDataTab to tabs
- `server/api.py` - Add training data endpoints

**New API Endpoints (Editor Only):**
- `GET /api/training/datasets` - List all datasets
- `POST /api/training/datasets` - Create new dataset
- `POST /api/training/datasets/:name/upload` - Upload training images
- `DELETE /api/training/datasets/:name` - Delete dataset
- `PUT /api/training/datasets/:name/images/:id/caption` - Edit image caption

#### Phase 5: Image Pack Management UI (2-3 hours)

**Tasks:**
- Create ImagePacksTab for managing CSV sets
- Build visual set configuration editor
- Implement LoRA assignment UI with drag-drop
- Add CSV file upload functionality
- Enable editing set configurations (prompts, dimensions, LoRAs)
- Provide live preview of prompt templates

**Files to Create:**
- `web/src/components/ImagePacksTab.jsx` - Set management interface
- `web/src/components/SetEditor.jsx` - Visual config editor

**Files to Modify:**
- `web/src/App.jsx` - Add ImagePacksTab to tabs
- `server/api.py` - Add set management endpoints

**New API Endpoints (Editor Only):**
- `GET /api/sets/:name/config` - Get full set configuration
- `PUT /api/sets/:name/config` - Update set configuration
- `POST /api/sets/upload` - Upload CSV set definition
- `DELETE /api/sets/:name` - Delete set

#### Phase 6: Gallery Delete Functionality (1-2 hours)

**Tasks:**
- Add delete buttons to ImageGrid component (editor-only)
- Add delete buttons to BatchGallery component (editor-only)
- Implement confirmation dialogs
- Enable deleting individual images
- Enable deleting entire batches
- Add backend delete endpoints with proper permissions

**Files to Modify:**
- `web/src/components/ImageGrid.jsx` - Add delete button
- `web/src/components/BatchGallery.jsx` - Add delete functionality
- `server/api.py` - Add delete endpoints

**New API Endpoints (Editor Only):**
- `DELETE /api/outputs/:filename` - Delete single image
- `DELETE /api/batches/:batch_id` - Delete entire batch
- `DELETE /api/batches/:batch_id/images/:filename` - Delete image from batch

#### Phase 7: Documentation (1 hour)

**Tasks:**
- Create Google OAuth setup guide
- Update architecture documentation
- Document role-based access control system
- Add authentication flow diagrams
- Update API endpoint permissions

**Files to Create:**
- `docs/guides/GOOGLE_OAUTH_SETUP.md` - Complete setup guide

**Files to Modify:**
- `docs/ARCHITECTURE.md` - Add auth flow and RBAC documentation
- `docs/guides/NEXT_STEPS.md` - This file (mark as completed when done)

#### Implementation Order (Recommended)

1. **Phase 1: Backend OAuth** (foundation - 2-3 hours)
2. **Phase 2: Frontend Auth** (login UI - 1-2 hours)
3. **Phase 6: Gallery Delete** (quick win to validate RBAC - 1-2 hours)
4. **Phase 3: LoRA Management** (high value - 3-4 hours)
5. **Phase 4: Training Data** (medium priority - 3-4 hours)
6. **Phase 5: Image Packs** (nice to have - 2-3 hours)
7. **Phase 7: Documentation** (polish - 1 hour)

**Minimum Viable Product:** Phases 1, 2, and 6 (4-7 hours)
**Full Feature Set:** All phases (8-12 hours)

#### Security Features

- ✅ **Google OAuth** - Trusted authentication provider
- ✅ **Secure Sessions** - Flask session cookies with httponly flag
- ✅ **Role-Based Access Control** - Granular permissions system
- ✅ **Rate Limiting** - Prevent brute force attacks
- ✅ **Session Management** - Server-side session expiration
- ✅ **Audit Trail** - Track who performed administrative actions
- ✅ **HTTPS Required** - OAuth requires secure connection (via Cloudflare Tunnel)

#### Testing Checklist

- [ ] Non-authenticated users blocked from all pages
- [ ] Authenticated viewers can view but cannot delete/upload
- [ ] Editor role can delete images from gallery
- [ ] Editor role can upload LoRA files
- [ ] Editor role can manage training datasets
- [ ] Editor role can edit image pack configurations
- [ ] Role changes take effect immediately without re-login
- [ ] Session persists across page refreshes
- [ ] Logout clears session and redirects to login
- [ ] All protected API routes return 401 for non-authenticated requests
- [ ] All editor routes return 403 for authenticated non-editors

#### Configuration Requirements

**Google Cloud Console Setup:**
1. Go to https://console.cloud.google.com
2. Create a new project (or use existing)
3. Enable **Google+ API**
4. Go to **Credentials** > **Create Credentials** > **OAuth 2.0 Client ID**
5. Application type: **Web application**
6. Authorized redirect URIs:
   - Development: `http://localhost:10050/auth/google/callback`
   - Production: `https://imagineer.joshwentworth.com/auth/google/callback`
7. Copy **Client ID** and **Client Secret**

**GitHub Secrets (Required for production):**
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`

**Environment Variables:**
```bash
# Backend (.env or .env.production)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
FLASK_SECRET_KEY=random-secret-key-for-sessions
```

#### Benefits

**For Users:**
- Secure authentication with Google account
- Multi-factor authentication support (via Google account settings)
- No password management required
- Clear separation between viewer and editor capabilities
- Familiar "Sign in with Google" flow

**For Administrators:**
- Simple user management (edit users.json file)
- Granular permission control (viewer vs editor roles)
- Audit trail of all administrative actions
- Ability to revoke access instantly (remove from users.json)
- No shared passwords or credentials
- Full control - all data stays on your server

**For Developers:**
- Simple implementation (no Firebase SDK needed)
- Standard OAuth 2.0 flow
- All auth logic on our server (easier debugging)
- Leverages existing Cloudflare Tunnel HTTPS
- Just two dependencies: `authlib` + `flask-login`
- No external service quotas or billing

#### Migration Notes

**From Current Password Gate:**
- Password gate will be completely replaced
- No user data migration needed (fresh start)
- First user to sign in becomes admin (add to users.json)
- Admin can assign editor roles to other users

**Backward Compatibility:**
- No breaking changes to existing generated images
- All API endpoints remain functional
- LoRA files, datasets, and sets unaffected
- Job queue continues working as-is

#### Related Documentation

See also:
- `docs/deployment/SECURE_AUTHENTICATION_PLAN.md` - Auth strategy comparison
- Google OAuth 2.0 docs: https://developers.google.com/identity/protocols/oauth2
- Authlib documentation: https://docs.authlib.org/

---

## 🟢 Medium Priority (First Month)

### 9. Add CHANGELOG.md
**Purpose:** Track version history and changes
**Format:** Keep a Changelog standard

### 10. Create GitHub Issue Templates
**Templates Needed:**
- Bug report
- Feature request
- Documentation improvement

### 11. Add Pull Request Template
**Include:**
- Description of changes
- Testing checklist
- Related issues

### 12. Set Up GitHub Actions CI/CD
**Tests:**
- Python linting (flake8)
- Code formatting check (black)
- Frontend build verification
- Optional: Basic API tests

### 13. Improve Error Handling in API
**Current:** Generic error messages
**Enhancement:** More specific error codes and messages
**Location:** `server/api.py`

### 14. Add Rate Limiting
**Purpose:** Prevent API abuse
**Implementation:** Flask-Limiter middleware
**Recommended:** 10 requests per minute per IP

---

## 🔵 Low Priority (Future Enhancements)

### 15. Add Image Size Presets in UI
**Sizes:** 512x512, 768x768, 1024x1024, Custom
**Location:** `web/src/components/GenerateForm.jsx`

### 16. Make Negative Prompt Editable in UI
**Current:** Uses default from config.yaml
**Enhancement:** Add expandable textarea for custom negative prompts

### 17. Add Batch Generation from UI
**Feature:** Upload text file with multiple prompts
**Generate:** Process all prompts in sequence

### 18. Add Model Switching from UI
**Current:** Model selection only in config.yaml
**Enhancement:** Dropdown to switch between SD 1.5, SD 2.1, SDXL

### 19. Add WebSocket Support
**Purpose:** Real-time progress updates during generation
**Show:** Percentage complete, current step

### 20. Add Database for Job History
**Current:** In-memory job queue
**Enhancement:** SQLite or PostgreSQL for persistence
**Benefit:** Job history survives server restarts

### 21. Add Prompt History
**Feature:** Save and reuse previous prompts
**Storage:** Browser localStorage or database

### 22. Implement Image-to-Image
**Feature:** Use an input image as starting point
**Upload:** Image file in generation form

### 23. Add Inpainting Support
**Feature:** Edit specific parts of generated images
**Requires:** Mask drawing interface

---

## 📝 Documentation Tasks

### 24. Create Video Tutorial
**Content:** 5-10 minute walkthrough of setup and usage
**Platform:** YouTube or Vimeo
**Link:** Add to README.md

### 25. Add Example Prompts Gallery
**Create:** `docs/PROMPTS.md` with curated examples
**Include:** Prompt text + resulting images

### 26. Write Troubleshooting Guide
**Expand:** README troubleshooting section
**Add:** Common errors and solutions from user reports

### 27. Document Production Deployment
**Guide:** Nginx reverse proxy, SSL/TLS, systemd service
**Audience:** Users deploying on VPS/cloud

---

## 🧪 Testing & Quality

### 28. Add Unit Tests
**Framework:** pytest
**Coverage:** Core functions in `src/imagineer/utils.py`

### 29. Add API Endpoint Tests
**Test:** All `/api/*` endpoints
**Verify:** Status codes, response formats, error handling

### 30. Add Frontend Tests
**Framework:** React Testing Library
**Test:** Component rendering, user interactions

### 31. Browser Compatibility Testing
**Test in:** Firefox, Safari, Edge
**Current:** Only tested in Chrome-based browsers

---

## 🔧 Code Quality

### 32. Add Type Hints to Python Code
**Files:** All `.py` files
**Tool:** mypy for type checking

### 33. Implement Proper Logging
**Replace:** print statements with logging module
**Levels:** DEBUG, INFO, WARNING, ERROR
**Output:** Configurable log files

### 34. Code Coverage Report
**Tool:** pytest-cov
**Target:** 80% coverage minimum
**Display:** Badge in README.md

---

## 🎯 Performance Optimization

### 35. Implement Caching
**Cache:** Model loading (keep in memory between requests)
**Benefit:** Faster subsequent generations

### 36. Add Queue Priority System
**Feature:** Different priority levels for jobs
**Use case:** Premium users or urgent requests

### 37. Optimize Frontend Bundle Size
**Current:** 154KB JS
**Target:** <100KB with code splitting and tree shaking

---

## 📊 Monitoring & Analytics

### 38. Add Usage Metrics
**Track:** Number of generations, popular prompts, average time
**Privacy:** No PII, aggregate statistics only

### 39. Implement Health Monitoring
**Expand:** `/api/health` endpoint
**Add:** GPU temperature, VRAM usage, queue depth

### 40. Error Reporting
**Tool:** Sentry or similar
**Purpose:** Track and fix production errors

---

## 🌐 Community & Growth

### 41. Set Up GitHub Discussions
**Categories:** General, Q&A, Show & Tell, Ideas
**Purpose:** Community support and engagement

### 42. Create Project Roadmap
**Tool:** GitHub Projects board
**Visibility:** Public roadmap for transparency

### 43. Write Contributor Guide
**Expand:** CONTRIBUTING.md
**Add:** Development setup, code style, PR process

### 44. Add Code of Conduct
**Standard:** Contributor Covenant
**Purpose:** Welcoming, inclusive community

---

## 🎨 UI/UX Improvements

### 45. Add Dark Mode
**Toggle:** Light/dark theme switcher
**Persist:** Save preference in localStorage

### 46. Improve Mobile Responsiveness
**Test:** All features on mobile devices
**Enhance:** Touch-friendly controls

### 47. Add Keyboard Shortcuts
**Examples:** Cmd+Enter to generate, Esc to close modal
**Document:** Show shortcuts in help tooltip

### 48. Add Generation History in UI
**Feature:** View past generations with filters
**Filters:** By date, prompt keywords, parameters

### 49. Improve Loading States
**Add:** Skeleton screens, progress indicators
**Current:** Simple spinner

---

## Notes

- **Dependencies:** Keep dependencies updated monthly
- **Security:** Review security advisories manually during scheduled dependency audits
- **Backups:** Regular backups of `/mnt/speedy/imagineer/`
- **Community:** Respond to issues within 48 hours

---

**Priorities can shift based on user feedback and community needs.**
