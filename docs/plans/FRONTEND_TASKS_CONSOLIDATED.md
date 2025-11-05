# Frontend Tasks - Consolidated & Verified

**Last Updated:** 2025-11-05
**Status:** Active - Verified against codebase
**Context:** Solo developer with AI assistance

This document consolidates all outstanding frontend tasks from various planning documents, verified against the current codebase state.

---

## 🔴 Priority P0 - Critical

**All P0 tasks completed!** ✅

Recent completions (2025-11-01):
- NSFW filter controls with persistence
- ImageCard consolidation across gallery views
- AuthButton migration
- Tab navigation shadcn/ui migration
- Typed API client for admin surfaces

---

## 🟡 Priority P1 - High

### F-P1-1: Training Runs UI
**Source:** IMPROVEMENT_TASKS_2025Q1.md #5
**Status:** ⏳ Not started
**Effort:** 3-4 days
**Files:** Create `web/src/pages/TrainingRunsPage.tsx`, update `App.tsx`

**Current State:**
- ✅ Backend API complete (`/api/training/runs/*`)
- ✅ TrainingTab component exists (basic view)
- ❌ No comprehensive training management UI
- ❌ No training run submission form
- ❌ No progress/logs viewer
- ❌ No LoRA download functionality

**Tasks:**
- [ ] Create `TrainingRunsPage.tsx` with modern layout
- [ ] Add training run submission form with validation
- [ ] Create training progress viewer component
- [ ] Add training logs streaming component
- [ ] Add trained LoRA download functionality
- [ ] Create training run history list
- [ ] Add training run cleanup interface
- [ ] Show training metrics/statistics
- [ ] Add training configuration presets
- [ ] Document training workflow for users

**Acceptance Criteria:**
- Admin can start training runs from UI
- View real-time training progress
- Stream training logs live
- Download trained LoRA files
- Clean up old training artifacts

---

### F-P1-2: Bug Report Viewer UI
**Source:** IMPROVEMENT_TASKS_2025Q1.md #7
**Status:** ⏳ Not started
**Effort:** 2-3 days
**Files:** Create `web/src/pages/BugReportsPage.tsx`

**Current State:**
- ✅ Backend bug report system functional
- ✅ Agent remediation working
- ✅ Database storage and tracking
- ❌ No UI to view bug reports
- ❌ Must use API directly or CLI

**Tasks:**
- [ ] Create `BugReportsPage.tsx` with shadcn/ui
- [ ] Add bug report list with status filtering
- [ ] Create bug report detail viewer
- [ ] Add agent trigger button
- [ ] Show agent progress/logs in real-time
- [ ] Add bug report search/filter functionality
- [ ] Create bug report submission form (manual reports)
- [ ] Add bug report analytics dashboard
- [ ] Add keyboard shortcut (Ctrl+Shift+B) to bug report

**Acceptance Criteria:**
- View all bug reports in UI
- Trigger automated remediation
- View agent progress and results
- Filter and search bug reports
- Submit manual bug reports

---

### F-P1-3: Image Labeling UI Enhancements
**Source:** IMPROVEMENT_TASKS_2025Q1.md #6, FRONTEND_TASKS.md
**Status:** ⚠️ Basic UI exists, needs polish
**Effort:** 2-3 days
**Files:** `web/src/components/ImageCard.tsx`, `web/src/pages/ImageDetailPage.tsx`

**Current State:**
- ✅ Backend labeling complete
- ✅ Label display in ImageCard
- ✅ NSFW filtering works
- ⚠️ No UI to trigger labeling
- ⚠️ No label editing interface
- ❌ No bulk labeling UI
- ❌ No label search/filter

**Tasks:**
- [ ] Add "Label Image" button to ImageDetailPage
- [ ] Add "Label All" button to AlbumDetailPage
- [ ] Create label display/edit component
- [ ] Add NSFW filter toggle in all gallery views
- [ ] Create labeling queue status viewer
- [ ] Add labeling progress indicator
- [ ] Show labeling analytics on album page
- [ ] Add label search/filter to gallery
- [ ] Create labeling history viewer
- [ ] Add label confidence score display

**Acceptance Criteria:**
- Trigger image labeling from UI
- View and edit labels on images
- Filter by labels in gallery
- View labeling progress and statistics
- Bulk label entire albums

---

## 🟢 Priority P2 - Medium

### F-P2-1: Consolidate Polling Hooks
**Source:** FRONTEND_TASKS.md F-7
**Status:** ⏳ Not started
**Effort:** 1-2 days
**Files:** `web/src/hooks/usePolling.ts`, `web/src/hooks/useAdaptivePolling.ts`

**Current State:**
- ✅ Two polling hooks exist (usePolling, useAdaptivePolling)
- ✅ Both functional
- ⚠️ Duplicate logic and maintenance burden
- ❌ QueueTab uses adaptive, others use static
- ❌ Fixes must be applied to both

**Tasks:**
- [ ] Merge hooks into single `usePolling` with optional adaptive mode
- [ ] Add comprehensive tests covering both modes
- [ ] Update QueueTab to use unified API
- [ ] Update ScrapingTab to use unified API
- [ ] Update TrainingTab to use unified API
- [ ] Remove deprecated hook file
- [ ] Update documentation

**Acceptance Criteria:**
- Single polling hook with adaptive option
- All components use unified API
- Comprehensive test coverage
- No duplicate logic

---

### F-P2-2: Harmonise Layout Shell
**Source:** FRONTEND_TASKS.md F-9
**Status:** ⚠️ Partially complete
**Effort:** 2-3 days
**Files:** Various page components, `App.css`

**Current State:**
- ✅ ScrapingTab, TrainingTab, QueueTab use AppShell
- ⚠️ Other tabs still use legacy container/padding
- ⚠️ Inconsistent spacing across pages
- ❌ Some pages have bespoke backgrounds

**Tasks:**
- [ ] Replace top-level header/container with shared layout
- [ ] Create `AppShell`, `PageHeader`, `PageContent` components
- [ ] Migrate all tabs to shared layout
- [ ] Remove redundant CSS from App.css
- [ ] Verify dark-mode tokens respected
- [ ] Ensure consistent spacing
- [ ] Remove hard-coded light backgrounds

**Acceptance Criteria:**
- All pages use shared layout components
- Consistent spacing and padding
- Dark mode works everywhere
- Legacy CSS removed

---

### F-P2-3: Standardise Feedback & Loading States
**Source:** FRONTEND_TASKS.md F-10
**Status:** ⚠️ Partially complete
**Effort:** 2-3 days
**Files:** Various components

**Current State:**
- ✅ Toast system exists and used in many places
- ✅ Spinner components from shadcn/ui
- ⚠️ Some flows still use `alert()` or `console.log`
- ⚠️ Mix of bespoke spinners and shadcn skeletons

**Tasks:**
- [ ] Audit all components for `alert()` usage
- [ ] Replace alerts with toast notifications
- [ ] Replace console.log errors with proper error handling
- [ ] Standardize on Spinner/Skeleton components
- [ ] Add loading states to all async operations
- [ ] Add error boundaries where needed
- [ ] Update tests to cover feedback states

**Acceptance Criteria:**
- No `alert()` calls remain
- All errors use toast system
- Consistent loading indicators
- Error states properly handled

---

### F-P2-4: Regression Tests for Admin Workflows
**Source:** FRONTEND_TASKS.md F-3
**Status:** ⚠️ Partially complete (QueueTab done)
**Effort:** 1-2 days
**Files:** `web/src/components/SettingsMenu.test.tsx`, test utils

**Current State:**
- ✅ QueueTab tests complete (10 tests)
- ⚠️ Settings menu bug-report tests pending
- ⚠️ Auth error state tests need polling hook refactor

**Tasks:**
- [ ] Add tests for settings menu bug-report entry
- [ ] Add tests for Ctrl+Shift+B keyboard shortcut
- [ ] Improve auth error state testing (after F-P2-1)
- [ ] Add tests for training tab admin workflows
- [ ] Add tests for scraping tab admin workflows

**Acceptance Criteria:**
- Settings menu fully tested
- Keyboard shortcuts tested
- Admin-only features have test coverage

---

### F-P2-5: Frontend UI Modernization
**Source:** IMPROVEMENT_TASKS_2025Q1.md #4
**Status:** ⚠️ Ongoing (shadcn/ui migration)
**Effort:** 1-2 weeks
**Files:** Various

**Current State:**
- ✅ shadcn/ui partially integrated
- ✅ Batch templates page redesigned
- ✅ Admin tabs modernized (Scraping, Training, Queue)
- ⚠️ Inconsistent styling across pages
- ⚠️ Some legacy components remain
- ❌ No dark mode toggle
- ❌ Mobile responsiveness needs work

**Tasks:**
- [ ] Complete shadcn/ui migration for all pages
- [ ] Modernize AlbumDetailPage layout
- [ ] Modernize ImageDetailPage layout
- [ ] Modernize GalleryTab layout
- [ ] Add dark mode toggle to settings
- [ ] Improve mobile responsiveness
- [ ] Add loading skeletons for better UX
- [ ] Standardize form validation patterns
- [ ] Create design system documentation

**Acceptance Criteria:**
- Consistent look and feel across all pages
- Dark mode fully functional
- Mobile-responsive design
- All pages use shadcn/ui components

---

## 🔵 Priority P3 - Low

### F-P3-1: Album Management Enhancements
**Source:** IMPROVEMENT_TASKS_2025Q1.md #13
**Status:** ⏳ Not started
**Effort:** 1 week
**Files:** `web/src/pages/AlbumDetailPage.tsx`, album components

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

### F-P3-2: Batch Generation Improvements
**Source:** IMPROVEMENT_TASKS_2025Q1.md #12
**Status:** ⏳ Not started
**Effort:** 1 week
**Files:** `web/src/pages/BatchTemplatesPage.tsx`

**Tasks:**
- [ ] Add batch template preview before generation
- [ ] Support batch template versioning
- [ ] Add template cloning/duplication
- [ ] Improve CSV editor UI
- [ ] Add template validation
- [ ] Support template importing/exporting
- [ ] Implement generation history per template
- [ ] Add cost estimation for batch runs

---

### F-P3-3: Accessibility Improvements
**Status:** ⏳ Not started
**Effort:** 1 week

**Tasks:**
- [ ] Add ARIA labels to all interactive elements
- [ ] Ensure keyboard navigation works everywhere
- [ ] Add focus-visible states
- [ ] Test with screen readers
- [ ] Ensure color contrast meets WCAG 2.1 AA
- [ ] Add skip-to-content links
- [ ] Add alt text to all images
- [ ] Document accessibility features

---

## 📋 Completed (Archive Ready)

### ✅ F-DONE-1: NSFW Filter Controls and Persistence
**Completed:** 2025-11-01
**Source:** FRONTEND_TASKS.md F-1

### ✅ F-DONE-2: ImageCard Consistency Across Gallery Surfaces
**Completed:** 2025-11-01
**Source:** FRONTEND_TASKS.md F-2

### ✅ F-DONE-3: AuthButton Migration
**Completed:** 2025-11-01
**Source:** FRONTEND_TASKS.md F-4

### ✅ F-DONE-4: Tab Navigation shadcn/ui Migration
**Completed:** 2025-11-01
**Source:** FRONTEND_TASKS.md F-5

### ✅ F-DONE-5: Typed API Client for Admin Surfaces
**Completed:** 2025-11-01
**Source:** FRONTEND_TASKS.md F-6

### ✅ F-DONE-6: Retire Shadcn Test Route
**Completed:** 2025-11-01
**Source:** FRONTEND_TASKS.md F-8

---

## 📊 Summary

| Priority | Total | Not Started | In Progress | Blocked |
|----------|-------|-------------|-------------|---------|
| P0 (Critical) | 0 | 0 | 0 | 0 |
| P1 (High) | 3 | 2 | 1 | 0 |
| P2 (Medium) | 5 | 2 | 3 | 0 |
| P3 (Low) | 3 | 3 | 0 | 0 |
| **Total** | **11** | **7** | **4** | **0** |

**Next Review:** After P1 tasks complete or 2025-11-15, whichever comes first

---

**Notes:**
- All tasks verified against codebase as of 2025-11-05
- Removed completed tasks (moved to archive)
- Consolidated duplicate tasks from multiple planning docs
- Solo developer context - focused on admin/developer UX
- ScrapingTab fully functional (683 lines) - no work needed
