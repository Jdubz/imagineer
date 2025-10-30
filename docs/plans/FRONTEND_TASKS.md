# Frontend Outstanding Tasks

**Last Updated:** 2025-10-30
**Status:** 20 tasks remaining (10 P2, 10 P3)

## Overview

This document consolidates all outstanding frontend tasks from the comprehensive code audit. All P0 (Critical) and P1 (High Priority) tasks have been completed. Remaining work focuses on performance optimization, code organization, and nice-to-have enhancements.

**Related Documents:**
- Source: `FRONTEND_AUDIT_TASKS.md` - Detailed audit with completion status
- Source: `FRONTEND_CODE_AUDIT.md` - Original comprehensive audit
- Source: `CONSOLIDATED_STATUS.md` - Overall project status

---

## Critical Priority (Blockers)

**Status:** All P0 tasks completed! ✅

Recent completions:
- Error Boundaries ✅ (2025-10-29)
- State mutation fixes in AlbumsTab ✅
- Memory leak fixes in polling ✅
- Input validation and sanitization ✅
- Accessibility (WCAG 2.1 AA compliance) ✅

---

## High Priority

**Status:** All P1 tasks completed! ✅

Recent completions:
- Standardized error handling with toast system ✅ (2025-10-29)
- Request cancellation with AbortController ✅
- Console logging removed from production ✅
- Type safety improved with Zod ✅
- Loading states added to components ✅

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
  - Add `loading="lazy"` to all images
  - Implement thumbnail API endpoints (if not exist)
  - Use `<picture>` with multiple sources
  - Add srcset for responsive images
  - Preload modal images on hover
  - Add blur-up placeholder effect
- **Estimated Time:** 3-5 days (Medium)
- **Status:** Blocked (awaiting thumbnail API endpoint delivery)
- **Dependencies:** Backend thumbnail API endpoints (coordinate with backend roadmap)
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
  - Test on various screen sizes
- **Estimated Time:** 1-2 weeks (Large)
- **Status:** Not Started
- **Reference:** FRONTEND_CODE_AUDIT.md:635-653

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
- **Reference:** FRONTEND_CODE_AUDIT.md:656-672

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
  - Add auth state management improvements
- **Status:** Mostly complete, verify integration
- **Priority:** High
- **Estimated Time:** 1-2 days

---

### Queue Tab Secure Access
**Source:** FRONTEND_QUEUE_SECURE_ACCESS.md
- **Issue:** Queue tab should be admin-only
- **Files:** `web/src/components/QueueTab.tsx`
- **Solution:** Add admin check before rendering queue controls
- **Status:** Not Started
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
