# Frontend Code Audit - Task Tracking

**Created:** 2025-10-28
**Last Updated:** 2025-10-29
**Source:** [FRONTEND_CODE_AUDIT.md](FRONTEND_CODE_AUDIT.md)
**Overall Progress:** 2/30 tasks complete (7%)

---

## 📊 Task Summary

| Priority | Total | Complete | In Progress | Not Started |
|----------|-------|----------|-------------|-------------|
| P0 (Critical) | 5 | 1 | 0 | 4 |
| P1 (High) | 5 | 1 | 0 | 4 |
| P2 (Medium) | 10 | 0 | 0 | 10 |
| P3 (Low) | 10 | 0 | 0 | 10 |
| **Total** | **30** | **2** | **0** | **28** |

### Effort Distribution

| Effort | Count | Tasks |
|--------|-------|-------|
| S (Small) | 4 | #8, #21, #28, #30 |
| M (Medium) | 9 | #3, #4, #10, #13, #14, #15, #20, #25, #29 |
| L (Large) | 8 | #2, #6, #7, #9, #16, #18, #26, #27 |
| XL (Extra Large) | 3 | #5, #23, #24 |

---

## 🔴 P0: Critical Issues (5 tasks)

### Task #1: Add Error Boundaries
**Priority:** P0
**Effort:** M
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- New: `web/src/components/ErrorBoundary.tsx`
- Modified: `web/src/App.tsx`
- New: `web/src/components/ErrorBoundary.test.tsx`

**Description:**
No React Error Boundaries implemented anywhere in the application. Any uncaught error in a component tree will crash the entire app with a white screen.

**Tasks:**
- [ ] Create `ErrorBoundary` component with fallback UI
- [ ] Add error logging/reporting integration point
- [ ] Wrap each major tab component with ErrorBoundary
- [ ] Add recovery options (reload page, go home)
- [ ] Include error details in development mode
- [ ] Write tests for error boundary behavior

**Acceptance Criteria:**
- [ ] Errors in one tab don't crash entire app
- [ ] User sees friendly error message with recovery options
- [ ] Errors are logged for debugging
- [ ] Tests verify error boundary catches and displays errors

**Reference:** FRONTEND_CODE_AUDIT.md:27-40

---

### Task #2: Fix Uncontrolled State Mutations in AlbumsTab
**Priority:** P0
**Effort:** L
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- `web/src/components/AlbumsTab.tsx:356-362, 397-425`
- New: `web/src/hooks/useAlbumState.ts` (recommended)

**Description:**
Direct state mutations and race conditions in label management. Multiple async operations updating the same state without proper synchronization can lead to race conditions and stale data.

**Tasks:**
- [ ] Audit all state updates in AlbumsTab
- [ ] Refactor to use `useReducer` for complex state
- [ ] Add loading states for all async operations
- [ ] Implement optimistic updates for better UX
- [ ] Add proper request cancellation with AbortController
- [ ] Fix useEffect dependencies to prevent stale closures
- [ ] Add comprehensive tests for state transitions

**Acceptance Criteria:**
- [ ] No direct state mutations
- [ ] All async operations have loading states
- [ ] Race conditions eliminated
- [ ] useEffect dependencies are correct
- [ ] Tests verify state management logic

**Reference:** FRONTEND_CODE_AUDIT.md:43-66

---

### Task #3: Fix Memory Leaks in Polling Mechanisms ✅
**Priority:** P0
**Effort:** M
**Status:** ✅ Complete
**Completed:** 2025-10-29
**Commit:** c2bc2e5

**Files:**
- ✅ `web/src/components/ScrapingTab.tsx` - Refactored to use usePolling
- ✅ `web/src/components/QueueTab.tsx` - Refactored to use usePolling
- ✅ `web/src/components/TrainingTab.tsx` - Refactored to use usePolling
- ✅ `web/src/hooks/usePolling.ts` - Created custom hook
- ✅ `web/src/hooks/usePolling.test.ts` - Added comprehensive tests (12/12 passing)

**Description:**
Intervals not properly cleaned up when components unmount or dependencies change. Dependencies change on every render, creating new intervals without clearing old ones, leading to memory leaks.

**Tasks:**
- [x] Move data fetching functions outside component or wrap with `useCallback`
- [x] Store interval ID in ref
- [x] Add cleanup in useEffect return
- [x] Create reusable `usePolling` hook
- [x] Add Page Visibility API to pause when tab hidden
- [x] Add tests to verify cleanup on unmount

**Acceptance Criteria:**
- [x] No memory leaks in polling components
- [x] Intervals properly cleaned up on unmount
- [x] Polling pauses when tab is hidden
- [x] Tests verify cleanup behavior

**Implementation Details:**
- Created `usePolling` hook with proper cleanup, stable callback references, and Page Visibility API support
- QueueTab: Replaced manual autoRefresh interval with usePolling
- ScrapingTab: Replaced manual job/stats polling with usePolling
- TrainingTab: Replaced manual log polling with conditional usePolling (enabled when log viewer open)
- All 12 tests passing, build successful

**Reference:** FRONTEND_CODE_AUDIT.md:69-92

---

### Task #4: Add Input Validation and Sanitization
**Priority:** P0
**Effort:** M
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- `web/src/components/GenerateForm.tsx:179-196`
- `web/src/components/ScrapingTab.tsx:396-404`
- `web/src/components/TrainingTab.tsx:645-764`
- New: `web/src/lib/validation.ts`

**Description:**
User inputs sent directly to API without client-side validation. No validation for prompt length limits, special characters, numeric range validation, or URL validation.

**Tasks:**
- [ ] Install validation library (Zod or Yup)
- [ ] Create validation schemas for all forms
- [ ] Add prompt length limits
- [ ] Add numeric range validation (steps, seed, etc.)
- [ ] Add URL validation for scraping form
- [ ] Sanitize inputs before submission
- [ ] Add field-level validation feedback
- [ ] Write validation tests

**Acceptance Criteria:**
- [ ] All forms have validation schemas
- [ ] Invalid inputs prevented from submission
- [ ] Clear validation error messages
- [ ] Numeric inputs respect min/max
- [ ] URLs validated before scraping
- [ ] Tests verify validation logic

**Reference:** FRONTEND_CODE_AUDIT.md:95-128

---

### Task #5: Fix Accessibility Violations (WCAG 2.1 AA)
**Priority:** P0
**Effort:** XL
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- `web/src/components/BatchGallery.tsx:110-172`
- `web/src/components/ImageGrid.tsx:63-127`
- `web/src/components/AlbumsTab.tsx:775-817`
- `web/src/components/LorasTab.tsx:78-80`
- `web/src/components/QueueTab.tsx:86-88`
- All CSS files (color contrast audit)
- New: `web/src/components/SkipNav.tsx`

**Description:**
Application fails WCAG 2.1 AA standards. No focus management, minimal keyboard navigation, missing ARIA labels, poor color contrast.

**Tasks:**
- [ ] Add `aria-label` to all icon buttons
- [ ] Implement keyboard handlers (`onKeyDown` for Enter/Space)
- [ ] Add `tabIndex={0}` to clickable divs or convert to buttons
- [ ] Install and use `react-focus-lock` for modals
- [ ] Add skip navigation links
- [ ] Audit and fix color contrast in all CSS (use WCAG contrast checker)
- [ ] Add `aria-live` regions for dynamic content
- [ ] Add `role` attributes where needed
- [ ] Test with screen reader (NVDA, VoiceOver)
- [ ] Add keyboard navigation documentation

**Acceptance Criteria:**
- [ ] All interactive elements keyboard accessible
- [ ] All icon buttons have aria-labels
- [ ] Modal focus properly trapped
- [ ] Skip navigation links present
- [ ] Color contrast meets WCAG 2.1 AA (4.5:1 for normal text)
- [ ] Screen reader can navigate entire app
- [ ] Passes automated accessibility audit (axe, Lighthouse)

**Reference:** FRONTEND_CODE_AUDIT.md:131-158

---

## 🟡 P1: High Priority (5 tasks)

### Task #6: Standardize Error Handling
**Priority:** P1
**Effort:** L
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- New: `web/src/hooks/useApiError.ts`
- New: `web/src/components/Toast.tsx`
- New: `web/src/contexts/ToastContext.tsx`
- All components with async operations

**Description:**
Mix of error handling strategies across components. Some use try/catch with console.error, some use .catch(), some use alert(), some set error state. Need centralized approach.

**Tasks:**
- [ ] Create `useApiError` custom hook
- [ ] Implement toast/notification system
- [ ] Replace all `alert()` calls with toast
- [ ] Standardize error message format
- [ ] Add error recovery suggestions
- [ ] Add error reporting/logging integration
- [ ] Update all components to use new system
- [ ] Write tests for error handling

**Acceptance Criteria:**
- [ ] No `alert()` calls remain
- [ ] All errors shown via toast system
- [ ] Consistent error message format
- [ ] Error logging centralized
- [ ] Tests verify error handling

**Reference:** FRONTEND_CODE_AUDIT.md:163-179

---

### Task #7: Add Request Cancellation
**Priority:** P1
**Effort:** L
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- All components with API calls
- New: `web/src/hooks/useAbortableEffect.ts` (recommended)

**Description:**
API requests not cancelled on unmount/navigation. If user navigates away before request completes, setState on unmounted component triggers React warnings and potential bugs.

**Tasks:**
- [ ] Add AbortController to all fetch requests
- [ ] Add cleanup in all useEffect hooks
- [ ] Create `useAbortableEffect` custom hook
- [ ] Handle AbortError properly (don't show as error)
- [ ] Consider React Query or SWR for automatic cancellation
- [ ] Update all components to use new pattern
- [ ] Write tests for cancellation behavior

**Acceptance Criteria:**
- [ ] No setState warnings on unmounted components
- [ ] All requests properly cancelled on unmount
- [ ] AbortError handled gracefully
- [ ] Tests verify cancellation

**Reference:** FRONTEND_CODE_AUDIT.md:182-215

---

### Task #8: Remove Console Logging from Production ✅
**Priority:** P1
**Effort:** S
**Status:** ✅ **COMPLETED** (2025-10-29)
**Assignee:** Claude Code
**Commit:** `b863b42`

**Files:**
- ✅ `web/src/App.tsx` (10 instances)
- ✅ `web/src/components/AlbumsTab.tsx` (9 instances)
- ✅ `web/src/components/ScrapingTab.tsx` (9 instances)
- ✅ `web/src/components/TrainingTab.tsx` (8 instances)
- ✅ `web/src/components/QueueTab.tsx` (1 instance)
- ✅ And 5 more files
- ✅ New: `web/src/lib/logger.ts`
- ✅ New: `web/src/lib/logger.test.ts`

**Description:**
51 console statements across 10 files replaced with centralized logger. Production builds no longer leak sensitive information.

**Tasks:**
- [x] Create logger utility with environment-based levels
- [x] Replace all `console.log` with logger.debug()
- [x] Replace `console.error` with logger.error() (sanitize messages)
- [x] Configure logger to be silent in production
- [x] Add error tracking integration point (Sentry/LogRocket)
- [x] Remove or gate all debug logging
- [x] Update ESLint rules to prevent console usage

**Acceptance Criteria:**
- [x] No console.log in production
- [x] console.error sanitized and gated
- [x] Logger respects environment
- [x] ESLint enforces no-console
- [x] Tests verify logger behavior (11/11 passing)

**Reference:** FRONTEND_CODE_AUDIT.md:218-238

**Completion Notes:**
- Created robust logger with PII sanitization
- All 51 console statements replaced
- ESLint configured to prevent regression
- Build passes (216KB bundle)
- All tests passing (51/51)

---

### Task #9: Improve Type Safety
**Priority:** P1
**Effort:** L
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- All components with API calls
- `shared/schema/` (backend types)
- New: `web/src/lib/api.ts` (typed API client)

**Description:**
Overuse of type assertions and unknown. Type guards returning Record<string, unknown> lose type information. API responses not validated against schemas.

**Tasks:**
- [ ] Install Zod for runtime validation
- [ ] Create Zod schemas for all API responses
- [ ] Generate TypeScript types from Zod schemas
- [ ] Remove double type assertions
- [ ] Validate API responses at boundary
- [ ] Create typed API client
- [ ] Update all API calls to use typed client
- [ ] Add tests for type validation

**Acceptance Criteria:**
- [ ] No double type assertions
- [ ] API responses validated at runtime
- [ ] TypeScript types match runtime validation
- [ ] Typed API client used throughout
- [ ] Tests verify runtime validation

**Reference:** FRONTEND_CODE_AUDIT.md:241-263

---

### Task #10: Add Loading States to Components
**Priority:** P1
**Effort:** M
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- `web/src/components/ImageGrid.tsx`
- `web/src/components/BatchList.tsx`
- `web/src/components/Tabs.tsx`
- `web/src/components/BatchGallery.tsx`
- New: `web/src/components/Spinner.tsx`
- New: `web/src/components/Skeleton.tsx`

**Description:**
Components render immediately without loading indicators. Users can't distinguish between "no data" and "still loading."

**Tasks:**
- [ ] Create `Spinner` component
- [ ] Create `Skeleton` component for content placeholders
- [ ] Add loading prop to all data-dependent components
- [ ] Show skeleton screens during loading
- [ ] Disable interactions during loading
- [ ] Add loading states to all async operations
- [ ] Write tests for loading states

**Acceptance Criteria:**
- [ ] All data fetches show loading indicator
- [ ] Skeleton screens for major content areas
- [ ] Interactions disabled during loading
- [ ] Clear distinction between loading and empty states
- [ ] Tests verify loading states render

**Reference:** FRONTEND_CODE_AUDIT.md:266-285

---

## 🟢 P2: Medium Priority (10 tasks)

### Task #11: Implement Code Splitting
**Priority:** P2
**Effort:** S
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- `web/src/App.tsx:242-277`

**Description:**
All tab components imported statically. Initial bundle includes code for all tabs even if user only uses one.

**Tasks:**
- [ ] Replace static imports with `React.lazy()`
- [ ] Wrap tab components in `Suspense`
- [ ] Create loading fallback component
- [ ] Test bundle size reduction
- [ ] Verify lazy loading works correctly

**Acceptance Criteria:**
- [ ] Tabs lazy loaded
- [ ] Bundle size reduced
- [ ] Loading fallback shown during load
- [ ] No errors in production build

**Reference:** FRONTEND_CODE_AUDIT.md:290-314

---

### Task #12: Optimize Component Re-renders
**Priority:** P2
**Effort:** L
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- `web/src/components/GenerateForm.tsx` (562 lines)
- `web/src/components/AlbumsTab.tsx` (821 lines)
- `web/src/components/TrainingTab.tsx` (814 lines)

**Description:**
Large components re-render entirely on any state change. GenerateForm re-renders on every keystroke, AlbumsTab re-renders when any image label changes.

**Tasks:**
- [ ] Split large components into smaller sub-components
- [ ] Use `React.memo()` for expensive sub-components
- [ ] Add `useCallback` for event handlers passed as props
- [ ] Add `useMemo` for expensive computations
- [ ] Measure render performance with React DevTools Profiler
- [ ] Write performance tests

**Acceptance Criteria:**
- [ ] Components split into logical sub-components
- [ ] Unnecessary re-renders eliminated
- [ ] Performance improved (measurable)
- [ ] Tests verify memoization works

**Reference:** FRONTEND_CODE_AUDIT.md:317-334

---

### Task #13: Implement Image Optimization
**Priority:** P2
**Effort:** M
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- `web/src/components/BatchGallery.tsx`
- `web/src/components/ImageGrid.tsx`
- `web/src/components/AlbumsTab.tsx`
- Backend: thumbnail API endpoints

**Description:**
No responsive images, thumbnails loaded as full images, no lazy loading attributes, no image preloading for modals.

**Tasks:**
- [ ] Add `loading="lazy"` to all images
- [ ] Implement thumbnail API endpoints (if not exist)
- [ ] Use `<picture>` with multiple sources
- [ ] Add srcset for responsive images
- [ ] Preload modal images on hover
- [ ] Add blur-up placeholder effect
- [ ] Measure performance improvements

**Acceptance Criteria:**
- [ ] All images lazy loaded
- [ ] Thumbnails used in grids
- [ ] Full images only loaded when needed
- [ ] Responsive images on different screen sizes
- [ ] Performance improved (measurable)

**Reference:** FRONTEND_CODE_AUDIT.md:337-362

---

### Task #14: Eliminate Prop Drilling with Context
**Priority:** P2
**Effort:** M
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- `web/src/App.tsx`
- New: `web/src/contexts/AuthContext.tsx`
- New: `web/src/contexts/ConfigContext.tsx`
- All child components receiving drilled props

**Description:**
Props passed through multiple levels. Auth state computed 3 times and passed separately to different components.

**Tasks:**
- [ ] Create `AuthContext` for user/auth state
- [ ] Create `ConfigContext` for global config
- [ ] Update App.tsx to provide contexts
- [ ] Update child components to consume contexts
- [ ] Remove prop drilling
- [ ] Consider state management library (Zustand, Jotai) if needed
- [ ] Write tests for context providers

**Acceptance Criteria:**
- [ ] No unnecessary prop drilling
- [ ] Auth context used throughout app
- [ ] Config context available to all components
- [ ] Tests verify context works

**Reference:** FRONTEND_CODE_AUDIT.md:365-383

---

### Task #15: Create Centralized API Client
**Priority:** P2
**Effort:** M
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- New: `web/src/lib/api.ts`
- New: `web/src/lib/apiClient.ts`
- All components with fetch calls

**Description:**
API endpoints hardcoded throughout components. Can't easily change base URL, no environment-based configuration, difficult to mock in tests.

**Tasks:**
- [ ] Create API client with base URL configuration
- [ ] Use environment variables for base URL
- [ ] Centralize all API endpoints
- [ ] Add request/response interceptors
- [ ] Add automatic error handling
- [ ] Update all components to use API client
- [ ] Write tests for API client

**Acceptance Criteria:**
- [ ] All API calls use centralized client
- [ ] Base URL configurable via env vars
- [ ] Easy to mock in tests
- [ ] Consistent error handling
- [ ] Tests verify API client behavior

**Reference:** FRONTEND_CODE_AUDIT.md:386-407

---

### Task #16: Add Form Validation with React Hook Form
**Priority:** P2
**Effort:** L
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- `web/src/components/GenerateForm.tsx`
- `web/src/components/ScrapingTab.tsx:389-499`
- `web/src/components/TrainingTab.tsx:645-764`

**Description:**
Forms provide minimal validation feedback. No inline error messages, only required attribute validation, no field-level validation, error states not visually indicated.

**Tasks:**
- [ ] Install React Hook Form and Zod
- [ ] Create validation schemas for all forms
- [ ] Refactor forms to use React Hook Form
- [ ] Add inline error messages per field
- [ ] Add visual error states (red borders)
- [ ] Show validation on blur and submit
- [ ] Add field-level async validation if needed
- [ ] Write comprehensive form tests

**Acceptance Criteria:**
- [ ] All forms use React Hook Form
- [ ] Inline validation errors shown
- [ ] Visual feedback for invalid fields
- [ ] Good UX (validate on blur, not on every keystroke)
- [ ] Tests verify form validation

**Reference:** FRONTEND_CODE_AUDIT.md:410-427

---

### Task #17: Extract Reusable Components and Utilities
**Priority:** P2
**Effort:** M
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- New: `web/src/components/Modal.tsx`
- New: `web/src/components/ImageCard.tsx`
- New: `web/src/lib/dateUtils.ts`
- `web/src/components/BatchGallery.tsx:110-172`
- `web/src/components/ImageGrid.tsx:63-127`
- `web/src/components/AlbumsTab.tsx:775-817`

**Description:**
Duplicate code patterns across components. Modal pattern repeated 3 times, image card pattern repeated 3 times, date formatting duplicated 3 times.

**Tasks:**
- [ ] Create reusable `<Modal>` component
- [ ] Create reusable `<ImageCard>` component
- [ ] Create date formatting utility
- [ ] Extract common patterns into custom hooks
- [ ] Update all components to use shared code
- [ ] Write tests for reusable components
- [ ] Document component APIs

**Acceptance Criteria:**
- [ ] Modal component used everywhere
- [ ] ImageCard component used everywhere
- [ ] Date formatting centralized
- [ ] Code duplication eliminated
- [ ] Tests verify reusable components

**Reference:** FRONTEND_CODE_AUDIT.md:429-456

---

### Task #18: Update Dependencies and Fix Security Issues
**Priority:** P2
**Effort:** L
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- `web/package.json`
- `web/package-lock.json`

**Description:**
Outdated packages and 2 moderate security vulnerabilities. React 19 available, testing libraries outdated, Vite and Vitest need updates.

**Tasks:**
- [ ] Run `npm audit fix` for security patches
- [ ] Review React 19 migration guide
- [ ] Test React 19 upgrade in branch
- [ ] Update testing libraries (@testing-library/react, vitest)
- [ ] Update Vite to latest
- [ ] Run full test suite after updates
- [ ] Test application thoroughly
- [ ] Pin dependency versions

**Acceptance Criteria:**
- [ ] No security vulnerabilities
- [ ] Dependencies updated (or decision made to wait)
- [ ] All tests pass
- [ ] Application works correctly
- [ ] Versions pinned to prevent breaks

**Reference:** FRONTEND_CODE_AUDIT.md:458-480

---

### Task #19: Optimize Polling Performance
**Priority:** P2
**Effort:** M
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- `web/src/components/ScrapingTab.tsx`
- `web/src/components/QueueTab.tsx`
- `web/src/components/TrainingTab.tsx`
- `web/src/components/LabelingPanel.tsx`
- New: `web/src/hooks/useVisibilityPolling.ts`

**Description:**
Aggressive polling every 2-5 seconds continues when tab not visible, no exponential backoff, multiple polls running simultaneously, battery drain on mobile.

**Tasks:**
- [ ] Use Page Visibility API to pause when tab hidden
- [ ] Implement exponential backoff for errors
- [ ] Coordinate polling across components
- [ ] Consider WebSocket for real-time updates
- [ ] Add "pull to refresh" as alternative
- [ ] Create `useVisibilityPolling` hook
- [ ] Measure performance improvements

**Acceptance Criteria:**
- [ ] Polling pauses when tab hidden
- [ ] Exponential backoff on errors
- [ ] Reduced network traffic
- [ ] Better battery life on mobile
- [ ] Tests verify polling behavior

**Reference:** FRONTEND_CODE_AUDIT.md:499-524

---

### Task #20: Add Build Optimization Configuration
**Priority:** P2
**Effort:** S
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- `web/vite.config.js`

**Description:**
Reading VERSION file synchronously at build time, no build size analysis, no compression configuration, no bundle splitting strategy.

**Tasks:**
- [ ] Fix VERSION file reading (use async or build-time env var)
- [ ] Add rollup-plugin-visualizer for bundle analysis
- [ ] Configure chunk splitting for vendor libs
- [ ] Add compression configuration (gzip/brotli)
- [ ] Set up source maps for production debugging
- [ ] Document build optimization strategy
- [ ] Measure build performance improvements

**Acceptance Criteria:**
- [ ] Build configuration optimized
- [ ] Bundle size visible and tracked
- [ ] Vendor chunks properly split
- [ ] Compression enabled
- [ ] Source maps available for debugging

**Reference:** FRONTEND_CODE_AUDIT.md:699-715

---

## 🔵 P3: Low Priority (10 tasks)

### Task #21: Enable Stricter TypeScript Options
**Priority:** P3
**Effort:** S
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- `web/tsconfig.json`

**Description:**
TypeScript strict mode enabled but could be stricter with noUncheckedIndexedAccess and exactOptionalPropertyTypes.

**Tasks:**
- [ ] Enable `noUncheckedIndexedAccess`
- [ ] Enable `exactOptionalPropertyTypes`
- [ ] Fix resulting type errors
- [ ] Update code to handle undefined array access
- [ ] Write tests for edge cases

**Acceptance Criteria:**
- [ ] Stricter TypeScript options enabled
- [ ] No type errors
- [ ] Code handles edge cases better
- [ ] Tests verify type safety

**Reference:** FRONTEND_CODE_AUDIT.md:528-546

---

### Task #22: Improve CSS Organization
**Priority:** P3
**Effort:** XL
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- All CSS files (11 files, 3,656 lines)
- New: `web/src/styles/tokens.css` (design tokens)

**Description:**
No CSS modules or CSS-in-JS, global namespace pollution risk, no design tokens, duplicate color values, no responsive breakpoint variables.

**Tasks:**
- [ ] Decide on CSS strategy (CSS Modules, CSS-in-JS, or Tailwind)
- [ ] Extract design tokens to CSS variables
- [ ] Create responsive breakpoint variables
- [ ] Migrate to chosen CSS solution
- [ ] Remove duplicate styles
- [ ] Document CSS architecture
- [ ] Update component imports

**Acceptance Criteria:**
- [ ] CSS organized and maintainable
- [ ] Design tokens defined
- [ ] No global namespace pollution
- [ ] Responsive breakpoints standardized
- [ ] Documentation updated

**Reference:** FRONTEND_CODE_AUDIT.md:550-567

---

### Task #23: Increase Test Coverage to 80%
**Priority:** P3
**Effort:** XL
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- `web/src/components/BatchGallery.tsx` (0 tests)
- `web/src/components/BatchList.tsx` (0 tests)
- `web/src/components/ConfigDisplay.tsx` (0 tests)
- `web/src/components/ImageGrid.tsx` (1 test, minimal)
- `web/src/components/LorasTab.tsx` (0 tests)
- `web/src/components/QueueTab.tsx` (0 tests)
- `web/src/components/Tabs.tsx` (0 tests)
- `web/src/components/LabelingPanel.tsx` (1 test)
- `web/src/components/GalleryTab.tsx` (0 tests)

**Description:**
Current coverage at 58% (2,595/4,468 statements). Many components have no tests at all.

**Tasks:**
- [ ] Write tests for untested components
- [ ] Add integration tests for user flows
- [ ] Test error states and edge cases
- [ ] Add visual regression tests (consider Chromatic)
- [ ] Add accessibility tests
- [ ] Set up coverage thresholds in CI
- [ ] Document testing strategy

**Acceptance Criteria:**
- [ ] 80%+ statement coverage
- [ ] All critical paths tested
- [ ] Error states tested
- [ ] Integration tests for major flows
- [ ] Tests maintainable and readable

**Reference:** FRONTEND_CODE_AUDIT.md:570-598

---

### Task #24: Add Internationalization (i18n)
**Priority:** P3
**Effort:** XL
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- All components
- New: `web/src/i18n/` directory
- New: `web/src/i18n/translations/en.json`

**Description:**
All text hardcoded in English. If multi-language support needed, requires complete refactor.

**Tasks:**
- [ ] Install react-i18next
- [ ] Extract all hardcoded strings
- [ ] Create translation files
- [ ] Set up i18n context
- [ ] Update all components to use translations
- [ ] Add language switcher
- [ ] Test with multiple languages
- [ ] Document translation workflow

**Acceptance Criteria:**
- [ ] No hardcoded strings in components
- [ ] Multiple languages supported
- [ ] Language switcher works
- [ ] Easy to add new translations
- [ ] Documentation for translators

**Reference:** FRONTEND_CODE_AUDIT.md:602-614

---

### Task #25: Add Error Tracking and Analytics
**Priority:** P3
**Effort:** M
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- New: `web/src/lib/monitoring.ts`
- `web/src/components/ErrorBoundary.tsx` (integrate Sentry)
- `web/src/main.tsx` (add Web Vitals)

**Description:**
No error tracking, performance monitoring, or user analytics.

**Tasks:**
- [ ] Set up Sentry for error tracking
- [ ] Integrate Sentry with ErrorBoundary
- [ ] Add Web Vitals reporting
- [ ] Add basic pageview tracking
- [ ] Add feature usage tracking
- [ ] Set up monitoring dashboard
- [ ] Document monitoring strategy

**Acceptance Criteria:**
- [ ] Errors reported to Sentry
- [ ] Performance metrics tracked
- [ ] User analytics available
- [ ] Dashboard accessible to team
- [ ] Privacy considerations addressed

**Reference:** FRONTEND_CODE_AUDIT.md:617-633

---

### Task #26: Improve Responsive Design
**Priority:** P3
**Effort:** L
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- All CSS files
- All components

**Description:**
Minimal responsive breakpoints, no mobile-first design, no touch target sizing, no mobile navigation.

**Tasks:**
- [ ] Audit on mobile devices
- [ ] Implement mobile-first CSS
- [ ] Add touch-friendly interactions (44px+ touch targets)
- [ ] Implement hamburger menu for tabs on mobile
- [ ] Add responsive images
- [ ] Test on various screen sizes
- [ ] Add mobile-specific features
- [ ] Document responsive strategy

**Acceptance Criteria:**
- [ ] Works well on mobile devices
- [ ] Touch targets properly sized
- [ ] Navigation usable on small screens
- [ ] Responsive images adapt to screen size
- [ ] Tested on multiple devices

**Reference:** FRONTEND_CODE_AUDIT.md:635-653

---

### Task #27: Add Dark Mode Support
**Priority:** P3
**Effort:** M
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- All CSS files
- New: `web/src/hooks/useTheme.ts`
- New: `web/src/contexts/ThemeContext.tsx`

**Description:**
No dark mode implementation despite modern browser support.

**Tasks:**
- [ ] Define dark mode color palette
- [ ] Add CSS custom properties for theme
- [ ] Add prefers-color-scheme media query support
- [ ] Create theme context and hook
- [ ] Add theme toggle button
- [ ] Update all components to use theme colors
- [ ] Test dark mode thoroughly
- [ ] Persist user preference

**Acceptance Criteria:**
- [ ] Dark mode available
- [ ] Respects system preference
- [ ] Manual toggle works
- [ ] Colors optimized for dark mode
- [ ] Theme preference persisted

**Reference:** FRONTEND_CODE_AUDIT.md:656-672

---

### Task #28: Add Essential Meta Tags
**Priority:** P3
**Effort:** S
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- `web/index.html`

**Description:**
Missing or incomplete meta tags for SEO and social sharing.

**Tasks:**
- [ ] Verify viewport meta tag
- [ ] Add description meta tag
- [ ] Add Open Graph tags
- [ ] Add Twitter Card tags
- [ ] Add favicon (multiple sizes)
- [ ] Add web app manifest
- [ ] Test social sharing

**Acceptance Criteria:**
- [ ] All essential meta tags present
- [ ] Favicon displays correctly
- [ ] Social sharing previews work
- [ ] Web app manifest valid

**Reference:** FRONTEND_CODE_AUDIT.md:675-685

---

### Task #29: Add Offline Support with Service Worker
**Priority:** P3
**Effort:** M
**Status:** Not Started
**Assignee:** Unassigned

**Files:**
- New: `web/public/service-worker.js`
- New: `web/src/lib/registerServiceWorker.ts`

**Description:**
No service worker, no offline functionality.

**Tasks:**
- [ ] Create service worker
- [ ] Cache static assets
- [ ] Create offline fallback page
- [ ] Add cache strategies for API calls
- [ ] Register service worker
- [ ] Test offline functionality
- [ ] Add update notification

**Acceptance Criteria:**
- [ ] Basic offline page available
- [ ] Static assets cached
- [ ] User notified when offline
- [ ] Updates handled gracefully

**Reference:** FRONTEND_CODE_AUDIT.md:688-696

---

### Task #30: Migrate to Progressive Web App (PWA)
**Priority:** P3
**Effort:** Not Estimated
**Status:** Not Started
**Assignee:** Unassigned

**Description:**
Application requires JavaScript to render anything. No SSR, no static fallback.

**Note:** This is an architectural decision. Consider Next.js or Remix for SSR if SEO becomes important. If not, at least add a `<noscript>` message.

**Tasks:**
- [ ] Evaluate need for SSR/SSG
- [ ] If needed, plan migration to Next.js or Remix
- [ ] If not needed, add `<noscript>` message
- [ ] Document decision and rationale

**Acceptance Criteria:**
- [ ] Decision documented
- [ ] If SSR: Migration plan created
- [ ] If no SSR: noscript message added

**Reference:** FRONTEND_CODE_AUDIT.md:483-496

---

## 📈 Progress Tracking

### Sprint 1: Critical Issues (Weeks 1-2)
- [ ] Task #3: Fix Memory Leaks in Polling
- [ ] Task #1: Add Error Boundaries
- [ ] Task #8: Remove Console Logging

**Goal:** Fix stability issues that affect all users

### Sprint 2: High Priority (Weeks 3-4)
- [ ] Task #5: Fix Accessibility Violations (Part 1: ARIA labels, keyboard nav)
- [ ] Task #6: Standardize Error Handling
- [ ] Task #7: Add Request Cancellation

**Goal:** Improve reliability and start accessibility work

### Sprint 3: P0 Completion (Weeks 5-6)
- [ ] Task #5: Fix Accessibility Violations (Part 2: Focus management, color contrast)
- [ ] Task #4: Add Input Validation
- [ ] Task #10: Add Loading States

**Goal:** Complete all P0 items

### Sprint 4: High Priority (Weeks 7-8)
- [ ] Task #2: Fix State Mutations in AlbumsTab
- [ ] Task #9: Improve Type Safety

**Goal:** Complete P1 items

### Sprint 5+: Medium and Low Priority
- Work through P2 and P3 items based on business priorities

---

## 🎯 Quick Actions

### This Week
Focus on immediate stability wins:
1. Fix memory leaks (#3) - Prevents performance degradation
2. Add error boundary (#1) - Prevents white screen crashes
3. Remove console logs (#8) - Reduces production noise

### This Month
Complete all P0 and P1 items:
- All critical stability and reliability issues
- Accessibility compliance
- Better error handling and user feedback

### This Quarter
Work through P2 items based on impact:
- Performance optimizations
- Code organization improvements
- Dependency updates

---

## 📝 Notes

### Effort Estimates
- **S (Small):** 1-2 days
- **M (Medium):** 3-5 days
- **L (Large):** 1-2 weeks
- **XL (Extra Large):** 2-4 weeks

### Dependencies
Some tasks have dependencies:
- Task #6 (Error Handling) should be done before Task #9 (Type Safety)
- Task #14 (Context) should be done before Task #15 (API Client)
- Task #1 (Error Boundary) should integrate with Task #25 (Monitoring)

### Resources
- **WCAG 2.1 Guidelines:** https://www.w3.org/WAI/WCAG21/quickref/
- **React Hook Form:** https://react-hook-form.com/
- **Zod:** https://zod.dev/
- **React Query:** https://tanstack.com/query/latest
- **Sentry:** https://sentry.io/

---

**Last Updated:** 2025-10-28
**Document Owner:** Development Team
**Review Frequency:** Weekly during sprints, monthly for roadmap
