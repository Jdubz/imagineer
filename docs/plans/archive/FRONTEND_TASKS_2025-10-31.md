# Frontend Outstanding Tasks

**Last Updated:** 2025-10-31 (Comprehensive Audit Completed)
**Status:** 29 tasks remaining (7 P0, 2 P1, 10 P2, 10 P3)

## 🔴 BREAKING: Post-Refactor Audit Findings (2025-10-31)

A comprehensive systematic investigation revealed the application is in a **critical transitional state** after the shadcn/ui design refactor. Multiple duplicate systems are running concurrently, creating maintenance burden, performance issues, and inconsistent UX.

**Overall Application Grade: C+ (70/100)**

### Critical Metrics
- **Test Coverage:** 58% (target: 80%)
- **TypeScript Coverage:** 100% (good)
- **Code Duplication:** ~15% (target: <5%)
- **Legacy CSS:** 4,616 lines across 18 files to delete
- **Performance Optimizations:** 0 (no useMemo/useCallback/React.memo)
- **Bundle Size:** ~200KB uncompressed (target: <150KB)

### Most Critical Issues
1. **Duplicate Toast Systems** - Two complete implementations running simultaneously
2. **No Error Boundaries** - Crashes propagate to users
3. **Aggressive Polling** - 1,800 API requests/hour causing OOM crashes
4. **Props Drilling** - 15+ props through multiple layers
5. **Mixed Styling** - 3 concurrent approaches (legacy CSS, Tailwind, shadcn)
6. **Zero Performance Optimizations** - Every component re-renders unnecessarily

**See:** Post-refactor audit reports in task descriptions below.
**Reference:** Comprehensive redundancy, best practices, and design consistency analysis completed 2025-10-31.

## Overview

This document consolidates outstanding frontend work across the October 2025 plans. Newly identified blockers focus on hardened admin auth flows and completing the bug reporting experience before returning to audit follow-ups and polish items.

**Related Documents:**
- Source: `FRONTEND_AUDIT_TASKS.md` – Detailed audit with completion status
- Source: `FRONTEND_CODE_AUDIT.md` – Original comprehensive audit
- Source: `FRONTEND_ADAPTATIONS_FOR_BACKEND_AUTH.md` – Auth gating requirements
- Source: `FRONTEND_QUEUE_SECURE_ACCESS.md` – Queue hardening checklist
- Source: `BUG_REPORT_IMPLEMENTATION_PLAN.md` – Bug reporter frontend phases
- Source: `BUG_REPORT_TOOL_PLAN.md` – Remaining telemetry gaps
- Source: `NSFW_FILTER_STATUS.md` – Global preference requirements
- Source: `SHARED_TYPES_VALIDATION_FIX.md` – Contract alignment tasks
- Source: `CONSOLIDATED_STATUS.md` – Overall project status
- Source: `SHADCN_REDESIGN_PLAN.md` – UI/system design guidance

---

## Critical Priority (P0)

### Task #35: URGENT - Consolidate Duplicate Toast Systems
- **Priority:** P0 (CRITICAL)
- **Estimated Time:** 4-6 hours (Small)
- **Status:** ✅ COMPLETE (2025-10-31)
- **Files:**
  - DELETE: `web/src/components/Toast.tsx`
  - DELETE: `web/src/contexts/ToastContext.tsx`
  - DELETE: `web/src/hooks/useToast.ts`
  - DELETE: `web/src/styles/Toast.css`
  - KEEP: `web/src/components/ui/toast.tsx`, `web/src/components/ui/toaster.tsx`, `web/src/hooks/use-toast.ts`
  - UPDATE: `web/src/App.tsx`, `web/src/contexts/BugReportContext.tsx`, `web/src/components/QueueTab.tsx`, `web/src/components/AlbumsTab.tsx`, `web/src/components/GenerateForm.tsx`
- **Issue:** TWO complete toast notification systems running simultaneously after shadcn refactor. Custom implementation (Toast.tsx, ToastContext) exists alongside shadcn/Radix UI implementation (ui/toast.tsx, use-toast.ts), causing developer confusion, larger bundle, and inconsistent UX.
- **Solution:**
  - Migrate all imports from `useToast` → `use-toast`
  - Replace `ToastContainer` with `Toaster` in App.tsx
  - Update toast API calls: `toast.success('Message')` → `toast({ title: 'Success', description: 'Message' })`
  - Delete 4 redundant files (Toast.tsx, ToastContext.tsx, hooks/useToast.ts, Toast.css)
  - Test all toast notifications across application
- **Impact:** Eliminates 300+ lines of duplicate code, reduces bundle ~15KB, establishes single notification pattern
- **Reference:** Redundancy analysis 2025-10-31, Critical Issue #1

### Task #36: URGENT - Add Error Boundaries to Prevent Crashes
- **Priority:** P0 (CRITICAL)
- **Estimated Time:** 3-4 hours (Small)
- **Status:** ✅ COMPLETE (Already implemented)
- **Files:**
  - NEW: `web/src/components/ErrorBoundary.tsx`
  - UPDATE: `web/src/App.tsx`
  - UPDATE: Major components (GenerateForm, ImageGallery, JobQueue)
- **Issue:** Application has ZERO error boundaries. Any component error propagates to users as white screen crash. No error recovery, no user-friendly messages.
- **Solution:**
  - Create ErrorBoundary component with:
    - Error state capture
    - User-friendly error UI with reload button
    - Error logging to console (TODO: integrate with error tracking service)
  - Wrap App root in ErrorBoundary
  - Wrap each major feature in ErrorBoundary (GenerateForm, ImageGallery, JobQueue)
  - Add retry/reload functionality
  - Consider integration with bug report system (Task #33)
- **Impact:** Prevents complete application crashes, provides graceful error recovery, improves user experience
- **Reference:** Best practices analysis 2025-10-31, Critical Issue #2

### Task #37: URGENT - Stop Aggressive Polling Memory Leak
- **Priority:** P0 (CRITICAL)
- **Estimated Time:** 4-6 hours (Small)
- **Status:** ✅ COMPLETE (2025-10-31)
- **Files:**
  - UPDATE: `web/src/components/QueueTab.tsx`
  - NEW: `web/src/hooks/useAdaptivePolling.ts`
- **Issue:** QueueTab polls API every 2 seconds = **1,800 requests/hour**. Runs continuously even when tab inactive, no error backoff, causes memory leaks and contributed to OOM crashes (see codex crash investigation 2025-10-31).
- **Solution Implemented:** Adaptive Polling (Option B Enhanced)
  - Created `useAdaptivePolling` hook with intelligent interval adjustment
  - **Active polling (2s)** when job is running - 1,800 req/hour
  - **Medium polling (10s)** when jobs queued - 360 req/hour (80% reduction)
  - **Idle polling (30s)** when no activity - 120 req/hour (93% reduction)
  - Page Visibility API pauses when tab hidden
  - Immediate fetch when tab regains focus
  - Proper cleanup prevents memory leaks
  - Error handling with fallback to slow polling
- **Impact:** Reduces API calls by 70-93% depending on activity level (typical: 81% reduction). In typical usage (10% active, 20% medium, 70% idle): 1,800 req/hour → 336 req/hour. Prevents memory leaks, reduces server load, improves battery life on mobile.
- **Reference:** Best practices analysis 2025-10-31, Critical Issue #3, ADAPTIVE_POLLING_COMPLETE.md
- **Future:** Consider WebSocket implementation for v2.0 if true real-time needed

### Task #38: URGENT - Eliminate Props Drilling with Context
- **Priority:** P0 (CRITICAL)
- **Estimated Time:** 8-10 hours (Medium)
- **Status:** ✅ COMPLETE (2025-10-31)
- **Files:**
  - NEW: `web/src/contexts/AppContext.tsx` (315 lines)
  - UPDATE: `web/src/App.tsx` (444 → 250 lines, -44% reduction)
  - UPDATE: `web/src/components/GenerateTab.tsx` (6 props → 1 prop)
  - UPDATE: `web/src/components/GalleryTab.tsx` (6 props → 0 props)
- **Issue:** App.tsx passes 12 props through component layers causing tight coupling, difficult maintenance, and poor performance. GenerateTab received 6 props, GalleryTab received 6 props.
- **Solution Implemented:**
  - Created `AppContext` with centralized state management:
    - **Generation State:** config, loading, currentJob, queuePosition
    - **Gallery State:** images, batches, loadingImages, loadingBatches
    - **Actions:** handleGenerate, fetchConfig, fetchImages, fetchBatches
    - **NSFW Filter:** nsfwEnabled state
  - Created convenience hooks:
    - `useApp()` - Full context access
    - `useGeneration()` - Generation-specific state/actions
    - `useGallery()` - Gallery-specific state/actions
  - Simplified App.tsx from 444 to 250 lines (-194 lines, -44%)
  - Eliminated all props drilling to tab components
  - Preserved bug report collector with context values
  - Initial data fetching on mount with proper cleanup
- **Impact:** Eliminated 11 props, reduced App.tsx by 44%, improved maintainability, enabled future performance optimizations. Bundle size increase: +0.03 KB gzipped (negligible).
- **Reference:** Best practices analysis 2025-10-31, Critical Issue #4, CONTEXT_API_COMPLETE.md

### Task #39: Add Basic Performance Optimizations
- **Priority:** P0 (HIGH IMPACT)
- **Estimated Time:** 6-8 hours (Medium)
- **Status:** Not Started
- **Files:**
  - UPDATE: `web/src/components/ImageGallery.tsx`
  - UPDATE: `web/src/components/BatchGallery.tsx`
  - UPDATE: `web/src/components/GenerateForm.tsx`
  - UPDATE: `web/src/components/JobQueue.tsx`
  - NEW: `web/src/hooks/useDebounce.ts`
- **Issue:** ZERO performance optimizations in entire application:
  - No React.memo on any component
  - No useMemo for expensive computations
  - No useCallback for event handlers
  - All components re-render on every parent update
  - Inline event handlers recreated every render
- **Solution:**
  - Wrap ImageCard in React.memo with custom comparison
  - Add useMemo for filtered/sorted image lists
  - Add useCallback for all event handlers passed as props
  - Memoize expensive modal components
  - Add useDebounce for search/filter inputs
  - Measure performance improvement with React DevTools Profiler
- **Impact:** 50-70% reduction in unnecessary re-renders, faster UI interactions, reduced CPU/battery usage
- **Reference:** Best practices analysis 2025-10-31, Critical Issue #6

### Task #31: Harden AuthContext & secured fetch flows
- **Priority:** P0
- **Estimated Time:** 2-3 days (Large)
- **Status:** Not Started
- **Files:** `web/src/App.tsx`, `web/src/lib/api.ts`, `web/src/components/QueueTab.tsx`, `web/src/components/SettingsMenu.tsx`, `web/src/hooks/useAuth.ts`, shared fetch helpers
- **Issue:** Backend auth changes on 2025-10-29 now require admin credentials for `/api/config`, `/api/jobs*`, and `/api/sets/*`. The SPA still assumes anonymous access, leaks queue data to viewers, and continues polling after 401 responses.
- **Solution:**
  - Implement the shared `AuthContext` (see Task #14 dependency) and expose `isAdmin`, `login`, `logout`, and session refresh helpers.
  - Update all fetch helpers and direct `fetch` usage to include `credentials: 'include'`, honor `Retry-After`, bubble `trace_id`, and stop polling on 401/403.
  - Gate queue/config/LoRA controls behind admin checks, map sanitized backend fields (`output_filename`, `output_directory`), and surface a re-auth banner instead of silent failures.
  - Add regression tests (RTL) that cover viewer vs. admin flows for QueueTab and config editor.
- **Dependencies:** Task #14 (Eliminate Prop Drilling with Context) should land first to avoid duplicating context wiring.
- **Reference:** `FRONTEND_ADAPTATIONS_FOR_BACKEND_AUTH.md`, `FRONTEND_QUEUE_SECURE_ACCESS.md`

### Task #32: Realign AuthStatus schema and contract tests
- **Priority:** P0
- **Estimated Time:** 0.5 day (Small)
- **Status:** Not Started
- **Files:** `web/src/lib/schemas.ts`, `web/src/__tests__/sharedContract.test.ts`, `shared/schema/auth_status.json`
- **Issue:** The runtime Zod schema strips nullable fields (`email`, `picture`, `is_admin`, `trace_id`), causing validation errors after the backend contract update.
- **Solution:**
  - Update `AuthStatusSchema` to mirror the generated TypeScript types and JSON Schema (nullable fields, `is_admin`, `message`, `trace_id`).
  - Extend contract tests to diff Zod schemas against their JSON Schema counterparts so drift fails fast.
  - Document the regeneration workflow in the engineering handbook (link from `docs/plans/SHARED_TYPES_VALIDATION_FIX.md`).
- **Reference:** `SHARED_TYPES_VALIDATION_FIX.md`, `CONTRACT_TESTING_INSPECTION_REPORT.md`

---

## High Priority (P1)

### Task #33: Ship bug report UX integration
- **Priority:** P1
- **Estimated Time:** 1-2 days (Medium)
- **Status:** Not Started
- **Files:** `web/src/components/SettingsMenu.tsx`, `web/src/components/BugReportButton.tsx`, `web/src/hooks/useKeyboardShortcut.ts`, `web/src/components/ErrorBoundaryWithReporting.tsx`, `web/src/contexts/BugReportContext.tsx`, `web/src/lib/api.ts`
- **Issue:** Backend bug report endpoint is live, but the frontend lacks the settings menu entry, admin-only hotkey, trace ID surfacing, and error-boundary integration needed to collect useful reports.
- **Solution:**
  - Add the gear menu with admin-only “Report Bug” action, persist placement in `App.tsx`, and hide legacy standalone button.
  - Implement `useKeyboardShortcut` to register `Ctrl+Shift+B`/`Cmd+Shift+B` for admins.
  - Wire `ErrorBoundary` and toast system to offer “Report Bug” with prefilled context (include `trace_id`, component stack, recent logs).
  - Capture optional screenshot (`html2canvas`), redact sensitive payloads per plan, and ensure payload includes network events/trace IDs.
  - Backfill RTL tests for the new surfaces and update docs (`docs/guides/BUG_REPORT_WORKFLOW.md`).
- **Reference:** `BUG_REPORT_IMPLEMENTATION_PLAN.md`, `BUG_REPORT_TOOL_PLAN.md`

### Task #34: Roll out global NSFW preference controls
- **Priority:** P1
- **Estimated Time:** 1-2 days (Medium)
- **Status:** Not Started
- **Files:** `web/src/contexts/NSFWContext.tsx` (new), `web/src/components/SettingsMenu.tsx`, `web/src/components/AlbumsTab.tsx`, `web/src/components/ImageGallery.tsx`, `web/src/components/BatchGallery.tsx`
- **Issue:** NSFW filter preferences only exist inside `AlbumsTab`; other galleries ignore the setting and the gear toggle is a stub.
- **Solution:**
  - Create a global NSFW context with localStorage persistence and defaults (`blur`).
  - Drive the Settings menu toggle off the global context and update fetches to send `nsfw` query params.
  - Update gallery components to respect the shared setting and fall back to client-side filtering if results are cached.
  - Add regression tests to ensure preference persists across reloads and viewer/admin roles.
- **Reference:** `NSFW_FILTER_STATUS.md`, `BUG_REPORT_IMPLEMENTATION_PLAN.md`

---

## Medium Priority (10 tasks)

### Task #11: Implement Code Splitting
- **File:** `web/src/App.tsx:242-277`
- **Issue:** All tab components imported statically. Initial bundle includes code for all tabs even if user only uses one.
- **Solution:**
  - Replace static imports with `React.lazy()`
  - Wrap tab components in `Suspense`
  - Create loading fallback component
  - Test bundle size reduction
- **Estimated Time:** 1-2 days (Small)
- **Status:** Not Started
- **Reference:** FRONTEND_CODE_AUDIT.md:290-314

---

### Task #12: Optimize Component Re-renders
- **Files:**
  - `web/src/components/GenerateForm.tsx` (562 lines)
  - `web/src/components/AlbumsTab.tsx` (821 lines)
  - `web/src/components/TrainingTab.tsx` (814 lines)
- **Issue:** Large components re-render entirely on any state change. GenerateForm re-renders on every keystroke, AlbumsTab re-renders when any image label changes.
- **Solution:**
  - Split large components into smaller sub-components
  - Use `React.memo()` for expensive sub-components
  - Add `useCallback` for event handlers passed as props
  - Add `useMemo` for expensive computations
  - Measure render performance with React DevTools Profiler
- **Estimated Time:** 1-2 weeks (Large)
- **Status:** Not Started
- **Reference:** FRONTEND_CODE_AUDIT.md:317-334

---

### Task #13: Implement Image Optimization
- **Files:**
  - `web/src/components/BatchGallery.tsx`
  - `web/src/components/ImageGrid.tsx`
  - `web/src/components/AlbumsTab.tsx`
  - Backend: thumbnail API endpoints
- **Issue:** No responsive images, thumbnails loaded as full images, no lazy loading attributes, no image preloading for modals.
- **Solution:**
  - [x] Add `loading="lazy"` to all images
  - [x] Implement thumbnail API endpoints (if not exist)
  - [x] Use `<picture>` with multiple sources
  - [x] Add srcset for responsive images
  - [x] Preload modal images on hover
  - [x] Add blur-up placeholder effect
  - [x] Measure performance improvements (2025-10-30 build: main chunk 267.7 kB / 84.3 kB gzip; AlbumsTab chunk 29.4 kB / 8.1 kB gzip; GalleryTab chunk 30.8 kB / 10.1 kB gzip)
- **Estimated Time:** 3-5 days (Medium)
- **Status:** In Progress (frontend implementation landed; perf benchmarking outstanding)
- **Dependencies:** Backend thumbnail API endpoints (delivered via `/api/images/:id/thumbnail`)
- **Next Action:** Capture runtime metrics and establish pre-change baseline for comparison by 2025-11-05.
- **Reference:** FRONTEND_CODE_AUDIT.md:337-362

---

### Task #14: Eliminate Prop Drilling with Context
- **Files:**
  - `web/src/App.tsx`
  - New: `web/src/contexts/AuthContext.tsx`
  - New: `web/src/contexts/ConfigContext.tsx`
  - All child components receiving drilled props
- **Issue:** Props passed through multiple levels. Auth state computed 3 times and passed separately to different components.
- **Solution:**
  - Create `AuthContext` for user/auth state
  - Create `ConfigContext` for global config
  - Update App.tsx to provide contexts
  - Update child components to consume contexts
  - Remove prop drilling
  - Consider state management library (Zustand, Jotai) if needed
- **Estimated Time:** 3-5 days (Medium)
- **Status:** Not Started
- **Dependency:** Blocks P0 Task #31; ship AuthContext provider ahead of auth-gating changes
- **Reference:** FRONTEND_CODE_AUDIT.md:365-383

---

### Task #15: Create Centralized API Client
- **Files:**
  - `web/src/lib/api.ts` (partially exists)
  - `web/src/lib/apiClient.ts` (new)
  - All components with fetch calls
- **Issue:** API endpoints hardcoded throughout components. Can't easily change base URL, no environment-based configuration, difficult to mock in tests.
- **Solution:**
  - Create API client with base URL configuration
  - Use environment variables for base URL
  - Centralize all API endpoints
  - Add request/response interceptors
  - Add automatic error handling
  - Update all components to use API client
- **Estimated Time:** 3-5 days (Medium)
- **Status:** Not Started
- **Reference:** FRONTEND_CODE_AUDIT.md:386-407

---

### Task #16: Add Form Validation with React Hook Form
- **Files:**
  - `web/src/components/GenerateForm.tsx`
  - `web/src/components/ScrapingTab.tsx:389-499`
  - `web/src/components/TrainingTab.tsx:645-764`
- **Issue:** Forms provide minimal validation feedback. No inline error messages, only required attribute validation, no field-level validation, error states not visually indicated.
- **Solution:**
  - Install React Hook Form and Zod (Zod already installed)
  - Create validation schemas for all forms
  - Refactor forms to use React Hook Form
  - Add inline error messages per field
  - Add visual error states (red borders)
  - Show validation on blur and submit
- **Estimated Time:** 1-2 weeks (Large)
- **Status:** Not Started
- **Reference:** FRONTEND_CODE_AUDIT.md:410-427

---

### Task #17: Extract Reusable Components and Utilities
- **Files:**
  - New: `web/src/components/Modal.tsx`
  - New: `web/src/components/ImageCard.tsx`
  - New: `web/src/lib/dateUtils.ts`
  - `web/src/components/BatchGallery.tsx:110-172`
  - `web/src/components/ImageGrid.tsx:63-127`
  - `web/src/components/AlbumsTab.tsx:775-817`
- **Issue:** Duplicate code patterns across components. Modal pattern repeated 3 times, image card pattern repeated 3 times, date formatting duplicated 3 times.
- **Solution:**
  - Create reusable `<Modal>` component
  - Create reusable `<ImageCard>` component
  - Create date formatting utility
  - Extract common patterns into custom hooks
  - Update all components to use shared code
- **Estimated Time:** 3-5 days (Medium)
- **Status:** Not Started
- **Reference:** FRONTEND_CODE_AUDIT.md:429-456

---

### Task #18: Update Dependencies and Fix Security Issues
- **Files:**
  - `web/package.json`
  - `web/package-lock.json`
- **Issue:** Outdated packages and 2 moderate security vulnerabilities. React 19 available, testing libraries outdated, Vite and Vitest need updates.
- **Solution:**
  - Run `npm audit fix` for security patches
  - Review React 19 migration guide
  - Test React 19 upgrade in branch
  - Update testing libraries (@testing-library/react, vitest)
  - Update Vite to latest
  - Run full test suite after updates
  - Pin dependency versions
- **Estimated Time:** 1-2 weeks (Large)
- **Status:** Not Started
- **Reference:** FRONTEND_CODE_AUDIT.md:458-480

---

### Task #19: Optimize Polling Performance
- **Files:**
  - `web/src/components/ScrapingTab.tsx`
  - `web/src/components/QueueTab.tsx`
  - `web/src/components/TrainingTab.tsx`
  - `web/src/components/LabelingPanel.tsx`
  - `web/src/hooks/usePolling.ts` (already exists with visibility support)
- **Issue:** Aggressive polling every 2-5 seconds continues when tab not visible (partially solved), no exponential backoff, multiple polls running simultaneously, battery drain on mobile.
- **Solution:**
  - ✅ Use Page Visibility API to pause when tab hidden (DONE in usePolling hook)
  - Implement exponential backoff for errors
  - Coordinate polling across components
  - Consider WebSocket for real-time updates
  - Add "pull to refresh" as alternative
- **Estimated Time:** 3-5 days (Medium)
- **Status:** Partially Complete (Page Visibility done)
- **Reference:** FRONTEND_CODE_AUDIT.md:499-524

---

### Task #20: Add Build Optimization Configuration
- **File:** `web/vite.config.js`
- **Issue:** Reading VERSION file synchronously at build time, no build size analysis, no compression configuration, no bundle splitting strategy.
- **Solution:**
  - Fix VERSION file reading (use async or build-time env var)
  - Add rollup-plugin-visualizer for bundle analysis
  - Configure chunk splitting for vendor libs
  - Add compression configuration (gzip/brotli)
  - Set up source maps for production debugging
  - Document build optimization strategy
- **Estimated Time:** 1-2 days (Small)
- **Status:** Not Started
- **Reference:** FRONTEND_CODE_AUDIT.md:699-715

---

## Low Priority (10 tasks)

### Task #21: Enable Stricter TypeScript Options
- **File:** `web/tsconfig.json`
- **Issue:** TypeScript strict mode enabled but could be stricter with noUncheckedIndexedAccess and exactOptionalPropertyTypes.
- **Solution:**
  - Enable `noUncheckedIndexedAccess`
  - Enable `exactOptionalPropertyTypes`
  - Fix resulting type errors
  - Update code to handle undefined array access
- **Estimated Time:** 1-2 days (Small)
- **Status:** Not Started
- **Reference:** FRONTEND_CODE_AUDIT.md:528-546

---

### Task #22: Improve CSS Organization
- **Files:** All CSS files (11 files, 3,656 lines)
- **Issue:** No CSS modules or CSS-in-JS, global namespace pollution risk, no design tokens, duplicate color values, no responsive breakpoint variables.
- **Solution:**
  - Decide on CSS strategy (CSS Modules, CSS-in-JS, or Tailwind)
  - Extract design tokens to CSS variables
  - Create responsive breakpoint variables
  - Migrate to chosen CSS solution
  - Remove duplicate styles
  - Document CSS architecture
- **Estimated Time:** 2-4 weeks (Extra Large)
- **Status:** Not Started
- **Reference:** FRONTEND_CODE_AUDIT.md:550-567

---

### Task #23: Increase Test Coverage to 80%
- **Files:**
  - `web/src/components/BatchGallery.tsx` (0 tests)
  - `web/src/components/BatchList.tsx` (0 tests)
  - `web/src/components/ConfigDisplay.tsx` (0 tests)
  - `web/src/components/ImageGrid.tsx` (1 test, minimal)
  - `web/src/components/LorasTab.tsx` (0 tests)
  - `web/src/components/QueueTab.tsx` (0 tests)
  - `web/src/components/Tabs.tsx` (0 tests)
  - `web/src/components/LabelingPanel.tsx` (1 test)
  - `web/src/components/GalleryTab.tsx` (0 tests)
- **Issue:** Current coverage at 58% (2,595/4,468 statements). Many components have no tests at all.
- **Solution:**
  - Write tests for untested components
  - Add integration tests for user flows
  - Test error states and edge cases
  - Add visual regression tests (consider Chromatic)
  - Add accessibility tests
  - Set up coverage thresholds in CI
- **Estimated Time:** 2-4 weeks (Extra Large)
- **Status:** Not Started
- **Reference:** FRONTEND_CODE_AUDIT.md:570-598

---

### Task #24: Add Internationalization (i18n)
- **Files:** All components
- **Issue:** All text hardcoded in English. If multi-language support needed, requires complete refactor.
- **Solution:**
  - Install react-i18next
  - Extract all hardcoded strings
  - Create translation files
  - Set up i18n context
  - Update all components to use translations
  - Add language switcher
- **Estimated Time:** 2-4 weeks (Extra Large)
- **Status:** Not Started
- **Reference:** FRONTEND_CODE_AUDIT.md:602-614

---

### Task #25: Add Error Tracking and Analytics
- **Files:**
  - New: `web/src/lib/monitoring.ts`
  - `web/src/components/ErrorBoundary.tsx` (integrate Sentry)
  - `web/src/main.tsx` (add Web Vitals)
- **Issue:** No error tracking, performance monitoring, or user analytics.
- **Solution:**
  - Set up Sentry for error tracking
  - Integrate Sentry with ErrorBoundary
  - Add Web Vitals reporting
  - Add basic pageview tracking
  - Add feature usage tracking
  - Set up monitoring dashboard
- **Estimated Time:** 3-5 days (Medium)
- **Status:** Not Started
- **Reference:** FRONTEND_CODE_AUDIT.md:617-633

---

### Task #26: Improve Responsive Design
- **Files:** All CSS files, All components
- **Issue:** Minimal responsive breakpoints, no mobile-first design, no touch target sizing, no mobile navigation.
- **Solution:**
  - Audit on mobile devices
  - Implement mobile-first CSS
  - Add touch-friendly interactions (44px+ touch targets)
  - Implement hamburger menu for tabs on mobile
  - Add responsive images
  - Adopt shadcn/ui layout primitives (cards, navigation, sheets) per redesign plan
  - Test on various screen sizes
- **Estimated Time:** 1-2 weeks (Large)
- **Status:** Not Started
- **Reference:** FRONTEND_CODE_AUDIT.md:635-653, SHADCN_REDESIGN_PLAN.md

---

### Task #27: Add Dark Mode Support
- **Files:**
  - All CSS files
  - New: `web/src/hooks/useTheme.ts`
  - New: `web/src/contexts/ThemeContext.tsx`
- **Issue:** No dark mode implementation despite modern browser support.
- **Solution:**
  - Define dark mode color palette
  - Add CSS custom properties for theme
  - Add prefers-color-scheme media query support
  - Create theme context and hook
  - Add theme toggle button
  - Update all components to use theme colors
  - Persist user preference
- **Estimated Time:** 3-5 days (Medium)
- **Status:** Not Started
- **Reference:** FRONTEND_CODE_AUDIT.md:656-672, SHADCN_REDESIGN_PLAN.md

---

### Task #28: Add Essential Meta Tags
- **File:** `web/index.html`
- **Issue:** Missing or incomplete meta tags for SEO and social sharing.
- **Solution:**
  - Verify viewport meta tag
  - Add description meta tag
  - Add Open Graph tags
  - Add Twitter Card tags
  - Add favicon (multiple sizes)
  - Add web app manifest
- **Estimated Time:** 1-2 days (Small)
- **Status:** Not Started
- **Reference:** FRONTEND_CODE_AUDIT.md:675-685

---

### Task #29: Add Offline Support with Service Worker
- **Files:**
  - New: `web/public/service-worker.js`
  - New: `web/src/lib/registerServiceWorker.ts`
- **Issue:** No service worker, no offline functionality.
- **Solution:**
  - Create service worker
  - Cache static assets
  - Create offline fallback page
  - Add cache strategies for API calls
  - Register service worker
  - Add update notification
- **Estimated Time:** 3-5 days (Medium)
- **Status:** Not Started
- **Reference:** FRONTEND_CODE_AUDIT.md:688-696

---

### Task #30: Migrate to Progressive Web App (PWA)
- **Issue:** Application requires JavaScript to render anything. No SSR, no static fallback.
- **Solution:** This is an architectural decision. Consider Next.js or Remix for SSR if SEO becomes important. If not, at least add a `<noscript>` message.
- **Estimated Time:** Not Estimated (Architectural Decision)
- **Status:** Not Started
- **Reference:** FRONTEND_CODE_AUDIT.md:483-496

---

## Additional Frontend Tasks (From Other Documents)

### Bug Report Tool Integration
**Source:** BUG_REPORT_TOOL_PLAN.md
- **Issue:** Frontend bug report components exist but need integration
- **Files:**
  - `web/src/components/ErrorBoundary.tsx` - Add bug report button to error UI
  - `web/src/components/Toast.tsx` - Add bug report button to error toasts
  - New: Settings menu with bug report access
  - New: Keyboard shortcut (Ctrl+Shift+B) for bug reports
- **Status:** Backend endpoint needed first
- **Priority:** Medium
- **Estimated Time:** 2-3 days

---

### Frontend Auth Adaptations
**Source:** FRONTEND_ADAPTATIONS_FOR_BACKEND_AUTH.md
- **Issue:** Frontend needs to adapt to backend OAuth and rate limiting
- **Tasks:**
  - Handle 429 rate limit responses with retry-after
  - Update auth flow for OAuth redirects
  - Handle trace IDs in error responses
  - Add auth state management improvements (pending AuthContext from Task #14)
  - Gate queue/config mutations behind centralized admin checks
- **Status:** Mostly complete, verification blocked on Task #14 rollout
- **Priority:** High
- **Estimated Time:** 1-2 days

---

### Queue Tab Secure Access
**Source:** FRONTEND_QUEUE_SECURE_ACCESS.md
- **Issue:** Queue tab should be admin-only
- **Files:** `web/src/components/QueueTab.tsx`
- **Solution:** Add centralized admin guard (via AuthContext), halt polling after 401/403, and surface re-auth prompts
- **Status:** Not Started (depends on Task #14 completion)
- **Priority:** Medium
- **Estimated Time:** 1 hour

---

## Summary by Priority

| Priority | Count | Estimated Time |
|----------|-------|----------------|
| P2 (Medium) | 10 | 8-12 weeks |
| P3 (Low) | 10 | 10-14 weeks |
| Additional | 3 | 1 week |
| **Total** | **23** | **19-27 weeks** |

---

## Recommended Next Actions

### This Sprint (2 weeks)
1. **Task #20:** Build Optimization - Quick win, improves deployment
2. **Task #14:** Context for Prop Drilling - Unlocks API client refactor by removing duplicated prop wiring
3. **Frontend Auth Adaptations:** Verify OAuth/rate-limit handling end-to-end before closing the high-priority follow-up

### Next Sprint (2 weeks)
1. **Task #11:** Code Splitting - Reduces initial bundle size
2. **Task #15:** Centralized API Client - Builds on new contexts to consolidate API access
3. **Task #17:** Extract Reusable Components - Reduces code duplication

### Long-term (Quarterly Planning)
1. **Task #18:** Dependency Updates - Security and modernization
2. **Task #12:** Component Re-render Optimization - Performance
3. **Task #23:** Increase Test Coverage - Quality and confidence

---

## Notes

- All P0 and P1 tasks completed as of 2025-10-29 ✅
- Frontend is stable and production-ready
- Remaining tasks are enhancements and optimizations
- Consider business priorities when scheduling P2/P3 work
- Some tasks have dependencies (e.g., #14 should precede #15)
- Task #13 is blocked until backend thumbnail endpoints ship; coordinate cross-team scheduling before committing to sprint

---

**Document Owner:** Development Team
**Review Frequency:** Monthly for roadmap updates
**Last Audit:** 2025-10-28 (FRONTEND_CODE_AUDIT.md)
