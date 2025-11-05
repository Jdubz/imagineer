# Improvement Tasks - 2025 Q1

**Generated:** 2025-11-05
**Updated:** 2025-11-05 (Revised after UI review)
**Status:** Draft for Review
**Priority:** High → Medium → Low
**Context:** Solo developer with AI assistance - no need for public API docs

This document outlines immediate improvement tasks identified from a comprehensive codebase review.

---

## 🔴 HIGH PRIORITY - Critical & Blocking

### 1. Training-Data Repository Production Setup
**Status:** Blocking scraping in production
**Effort:** 1 day
**Impact:** Critical - Scraping cannot work in production

**Current State:**
- ✅ Training-data repo exists at `/home/jdubz/Development/training-data`
- ✅ Dev config points to correct path
- ✅ Scraping UI fully implemented (683-line ScrapingTab component)
- ✅ Backend API functional
- ⚠️ Production config points to non-existent `/mnt/storage/imagineer/training-data`
- ❌ Production path doesn't exist
- ❌ No documentation on training-data setup

**Tasks:**
- [ ] Create production training-data repository location
- [ ] Clone/setup training-data in `/mnt/storage/imagineer/training-data`
- [ ] Install dependencies in production training-data venv
- [ ] Copy scraping_config.yaml to production
- [ ] Update production config.yaml (via PR to main)
- [ ] Test scraping in production environment
- [ ] Document training-data installation process
- [ ] Add training-data repo check to deployment script

**Acceptance Criteria:**
- Production scraping works with training-data integration
- Both dev and prod have properly configured training-data
- Documentation exists for setting up training-data repo
- Deployment script validates training-data setup

---

### 2. Production/Development Environment Isolation
**Status:** Partially addressed
**Effort:** 1 day
**Impact:** Critical - Prevents production accidents

**Current State:**
- ✅ Development server script created (`./run-dev.sh`)
- ✅ Separate configs (`config.development.yaml`)
- ✅ Documentation written (`docs/DEVELOPMENT_WORKFLOW.md`)
- ⚠️ Production server still has uncommitted changes from testing
- ⚠️ Develop branch being used on production server
- ⚠️ CI/CD already enforces main branch (`.github/workflows/ci.yml:150`)

**Tasks:**
- [ ] Clean up production server uncommitted changes
- [ ] Ensure production is on main branch
- [ ] Add branch protection rules in GitHub (require PR reviews)
- [ ] Add pre-commit hooks to prevent production config edits on develop
- [ ] Create deployment checklist document
- [ ] Add environment indicator in API health endpoint response
- [ ] Test development server thoroughly
- [ ] Verify CI/CD deployment flow

**Acceptance Criteria:**
- Production server only runs code from `main`
- Development changes never touch production
- Clear environment indicator in API responses
- Pre-commit hooks prevent accidental production config edits
- GitHub branch protection enforces PR review process

---

## 🟡 MEDIUM PRIORITY - Important Improvements

### 4. Frontend UI Modernization & Consistency
**Status:** Partially completed (shadcn/ui migration ongoing)
**Effort:** 1-2 weeks
**Impact:** Medium - User experience improvement

**Current State:**
- ✅ shadcn/ui components partially integrated
- ✅ Batch templates page redesigned
- ⚠️ Inconsistent styling across pages
- ⚠️ Some legacy components remain
- ❌ No scraping UI
- ❌ No training run management UI
- ❌ No bug report viewer UI

**Tasks:**
- [ ] Complete shadcn/ui migration for all pages
- [ ] Standardize layout components (headers, navigation, footers)
- [ ] Add dark mode support
- [ ] Improve mobile responsiveness
- [ ] Add loading skeletons for better perceived performance
- [ ] Standardize form validation patterns
- [ ] Add toast notifications for user feedback
- [ ] Create design system documentation

**Pages Needing Update:**
- [ ] AlbumDetailPage.tsx (modernize layout)
- [ ] ImageDetailPage.tsx (modernize layout)
- [ ] Create ScrapingPage.tsx (new)
- [ ] Create TrainingRunsPage.tsx (new)
- [ ] Create BugReportsPage.tsx (new)
- [ ] Create AdminDashboard.tsx (new)

**Acceptance Criteria:**
- Consistent look and feel across all pages
- Mobile-responsive design
- Accessible (WCAG 2.1 AA compliance)
- Dark mode support
- Modern, polished UI matching shadcn/ui aesthetic

---

### 5. Image Labeling & NSFW Detection UI
**Status:** Backend complete, no frontend
**Effort:** 3-4 days
**Impact:** Medium - Enables content moderation workflow

**Current State:**
- ✅ Backend Celery tasks functional
- ✅ Claude CLI Docker integration working
- ✅ Label storage in database
- ✅ Album-level labeling analytics
- ❌ No UI to trigger labeling
- ❌ No UI to view/edit labels
- ❌ No NSFW filtering in gallery views
- ❌ No bulk labeling interface

**Tasks:**
- [ ] Add "Label Image" button to image detail page
- [ ] Add "Label All" button to album page
- [ ] Create label display/edit component
- [ ] Add NSFW filter toggle in gallery views
- [ ] Create labeling queue status viewer
- [ ] Add labeling progress indicator
- [ ] Show labeling analytics on album page
- [ ] Add label search/filter functionality
- [ ] Create labeling history viewer
- [ ] Add label confidence score display

**Acceptance Criteria:**
- Admin can trigger image labeling from UI
- View and edit labels on images
- Filter NSFW content in galleries
- View labeling progress and statistics
- Bulk label entire albums

---

### 6. Training Run Management
**Status:** Backend complete, no frontend
**Effort:** 3-4 days
**Impact:** Medium - Enables LoRA training workflow

**Current State:**
- ✅ Backend training task implementation
- ✅ TrainingRun database model
- ✅ Training retention/cleanup tasks
- ❌ No UI to start training runs
- ❌ No UI to view training progress
- ❌ No UI to download trained LoRAs
- ❌ No training run history viewer

**Tasks:**
- [ ] Create TrainingRunsPage.tsx
- [ ] Add training run submission form
- [ ] Create training progress viewer
- [ ] Add training logs viewer
- [ ] Add trained LoRA download functionality
- [ ] Create training run history list
- [ ] Add training run cleanup interface
- [ ] Show training metrics/statistics
- [ ] Add training configuration presets
- [ ] Document training workflow

**Acceptance Criteria:**
- Admin can start training runs from UI
- View real-time training progress
- Download trained LoRA files
- View training history and logs
- Clean up old training artifacts

---

### 7. Bug Report System UI
**Status:** Backend complete, no frontend
**Effort:** 2-3 days
**Impact:** Medium - Improves developer workflow

**Current State:**
- ✅ Bug report agent system functional
- ✅ Database storage and tracking
- ✅ Automated remediation via Docker
- ❌ No UI to view bug reports
- ❌ No UI to trigger agent
- ❌ Must use API directly

**Tasks:**
- [ ] Create BugReportsPage.tsx
- [ ] Add bug report list with status
- [ ] Create bug report detail viewer
- [ ] Add agent trigger button
- [ ] Show agent progress/logs
- [ ] Add bug report search/filter
- [ ] Create bug report submission form (for manual reports)
- [ ] Add bug report analytics dashboard

**Acceptance Criteria:**
- View all bug reports in UI
- Trigger automated remediation
- View agent progress and results
- Filter and search bug reports

---


## 🟢 LOW PRIORITY - Nice to Have

### 8. Performance Optimization
**Status:** Functional but unoptimized
**Effort:** 1 week
**Impact:** Low-Medium - Improves user experience

**Tasks:**
- [ ] Add database indexes for common queries
- [ ] Implement Redis caching for expensive queries
- [ ] Add pagination to all list endpoints
- [ ] Optimize image thumbnail generation
- [ ] Implement lazy loading in frontend
- [ ] Add image CDN integration
- [ ] Profile and optimize slow API endpoints
- [ ] Add database connection pooling
- [ ] Implement request caching headers
- [ ] Add API response compression

---

### 9. Enhanced Monitoring & Observability
**Status:** Basic logging only
**Effort:** 1 week
**Impact:** Low-Medium - Operations improvement

**Tasks:**
- [ ] Set up application metrics (Prometheus)
- [ ] Create Grafana dashboards
- [ ] Add structured logging (JSON format)
- [ ] Implement distributed tracing
- [ ] Add error tracking (Sentry)
- [ ] Create alerting rules for critical errors
- [ ] Add performance monitoring
- [ ] Create uptime monitoring
- [ ] Add audit logging for admin actions
- [ ] Create operational runbook

---

### 10. Security Hardening
**Status:** Basic security in place
**Effort:** 1 week
**Impact:** Medium - Security improvement

**Tasks:**
- [ ] Add rate limiting per user/IP
- [ ] Implement request throttling
- [ ] Add CSRF protection tokens
- [ ] Enhance input validation
- [ ] Add SQL injection prevention audit
- [ ] Implement file upload scanning
- [ ] Add security headers (CSP, etc.)
- [ ] Create security audit process
- [ ] Add dependency vulnerability scanning
- [ ] Implement secrets rotation strategy

---

### 11. User Management & Permissions
**Status:** Simple admin/non-admin model
**Effort:** 1 week
**Impact:** Low - Scalability improvement

**Current State:**
- ✅ Google OAuth authentication
- ✅ Admin role defined in users.json
- ⚠️ Only two admins supported
- ❌ No role-based access control (RBAC)
- ❌ No user management UI
- ❌ No permission granularity

**Tasks:**
- [ ] Implement RBAC system
- [ ] Create user management UI
- [ ] Add role assignment interface
- [ ] Create permission matrix
- [ ] Add user activity logging
- [ ] Implement user quotas/limits
- [ ] Add API key management
- [ ] Create invite system for new users

---

### 12. Batch Generation Improvements
**Status:** Functional, could be enhanced
**Effort:** 1 week
**Impact:** Low - Feature enhancement

**Tasks:**
- [ ] Add batch template preview before generation
- [ ] Support batch template versioning
- [ ] Add template cloning/duplication
- [ ] Improve CSV editor UI
- [ ] Add template validation
- [ ] Support template importing/exporting
- [ ] Add template marketplace/sharing
- [ ] Implement generation history per template
- [ ] Add cost estimation for batch runs

---

### 13. Album Management Enhancements
**Status:** Basic functionality present
**Effort:** 1 week
**Impact:** Low - User experience improvement

**Tasks:**
- [ ] Add album tags/categories
- [ ] Implement album search
- [ ] Add album sharing (public links)
- [ ] Support album cover image selection
- [ ] Add album sorting options
- [ ] Implement album merging
- [ ] Add album export (ZIP download)
- [ ] Support album deletion with confirmation
- [ ] Add album statistics dashboard

---

### 14. Code Quality Improvements
**Status:** Good but could be better
**Effort:** Ongoing
**Impact:** Low - Maintenance improvement

**Current State:**
- ✅ 272 test cases
- ✅ CI/CD with linting and tests
- ⚠️ 355 TODO/FIXME comments
- ⚠️ No test coverage reporting
- ❌ Inconsistent code style in places

**Tasks:**
- [ ] Resolve high-priority TODO comments
- [ ] Add test coverage reporting in CI
- [ ] Increase backend test coverage to 80%+
- [ ] Increase frontend test coverage to 70%+
- [ ] Add integration test suite
- [ ] Add E2E test suite (Playwright/Cypress)
- [ ] Standardize error handling patterns
- [ ] Add TypeScript strict mode in frontend
- [ ] Create code review checklist
- [ ] Add pre-commit hooks for formatting

---

## 📊 Summary Statistics

**Codebase Metrics:**
- Backend: 45 Python files, 36 dependencies
- Frontend: 57 React components, 21 dependencies
- API Endpoints: 97 routes
- Database Models: 9 models
- Test Files: 24 backend, 29 frontend
- Test Cases: 272+ total
- Major UI Components: Scraping (683 lines), fully functional

**Technical Debt:**
- 355 TODO/FIXME comments
- 2 major features without UI (training runs, bug reports)
- Limited monitoring/observability
- Some inconsistent styling (shadcn/ui migration in progress)

---

## 🎯 Recommended Prioritization

**Sprint 1 (Week 1):** Critical Infrastructure
1. Training-data repository production setup (HIGH - 1 day)
2. Production/Development isolation cleanup (HIGH - 1 day)
3. Test and verify scraping in production (HIGH - 1 day)

**Sprint 2 (Week 2-3):** Essential Features
4. Training run management UI (MEDIUM - 3-4 days)
5. Image labeling UI improvements (MEDIUM - 3-4 days)

**Sprint 3 (Week 4-5):** Polish & Enhancement
6. Frontend UI modernization (MEDIUM - 1-2 weeks)
7. Bug report UI (MEDIUM - 2-3 days)

**Sprint 4+:** Lower Priority
8. Performance optimization (LOW)
9. Security hardening (MEDIUM)
10. Monitoring & observability (LOW)
11. Code quality improvements (LOW - ongoing)

---

## 📝 Notes

- All HIGH priority tasks are blockers for production scraping functionality
- MEDIUM priority tasks significantly improve user experience and admin capabilities
- LOW priority tasks are enhancements and technical debt reduction
- Estimated efforts are for solo developer with AI assistance
- Actual timelines may vary based on unforeseen complexities
- No public API documentation needed (solo developer context)

---

**Last Updated:** 2025-11-05 (Revised)
**Review Status:** Ready for review
**Next Review:** After Sprint 1 completion
**Key Changes:**
- Removed scraping UI task (already implemented - 683 line component)
- Removed public API documentation task (not needed for solo dev)
- Renumbered remaining tasks
- Updated priorities based on actual implementation status
