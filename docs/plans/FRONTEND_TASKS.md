# Frontend Task Backlog (Updated 2025-11-01)

This backlog reflects the outstanding frontend work after verifying the codebase on 2025-11-01. Items marked completed in the archived 2025-10-31 plan are now in `docs/plans/archive/FRONTEND_TASKS_2025-10-31.md`.

### Status Overview

| Priority | Total | Complete | In Progress | Not Started |
|----------|-------|----------|-------------|-------------|
| P0 (Critical) | 5 | 5 ✅ | 0 | 0 |
| P1 (High) | 3 | 0 | 0 | 3 |
| P2 (Medium) | 10 | 0 | 0 | 10 |
| P3 (Low) | 10 | 0 | 0 | 10 |
| **Total** | **28** | **5** | **0** | **23** |

## Priority P0

### F-1: Expand NSFW Filter Controls and Persistence
- **Status:** ✅ Completed 2025-11-01 – multi-mode NSFW preference now ships with persistence and regression coverage.
- **Outcome:**
  - `AppContext` exposes a `NsfwPreference` enum persisted via `localStorage` (`imagineer.nsfwPreference`) and sanitises unexpected stored values.
  - `SettingsMenu` renders a three-state Select wired to `setNsfwPreference`, giving admins show/blur/hide controls.
  - `ImageCard`, `ImageGallery`, `ImageGrid`, and `BatchGallery` all respect blur/hide behaviour with the shared overlay styling.
  - New tests in `web/src/components/common/ImageCard.test.tsx` and `web/src/contexts/AppContext.test.tsx` verify mode handling and persistence.

## Priority P1

### F-2: Apply ImageCard Consistently Across Gallery Surfaces
- **Status:** ✅ Completed 2025-11-01 – gallery views now delegate to the shared `ImageCard`, so NSFW/label behaviour is consistent across the app.
- **Outcome:**
  - `ImageGrid` and `BatchGallery` render `ImageCard` wrappers instead of bespoke markup, eliminating duplicated blur/hide overlays and badge logic.
  - Added shared footer styling in `App.css` for prompts/metadata and removed legacy `.image-overlay`/`.preview-image` rules that drifted from the new component.
  - `GeneratedImage` now exposes optional `labels`, enabling badge counts wherever image responses include label data.
  - New RTL tests (`GalleryTab.test.tsx`, `BatchGallery.test.tsx`) assert hide/blur paths, catching regressions in context wiring and NSFW handling.

### F-4: Replace Header Login Flow with AuthButton
- **Status:** ✅ Completed 2025-11-01 – legacy header button removed, shared popup flow now active.
- **Outcome:** `web/src/App.tsx` renders `<AuthButton onAuthChange={setUser} />`, `web/src/styles/AuthButton.css` only retains layout helpers, and `web/src/App.test.tsx` gained coverage for signed-out vs. authenticated states.

### F-5: Complete Tab Navigation Migration to shadcn/ui
- **Status:** ✅ Completed 2025-11-01 – navigation now renders Radix tabs styled via shadcn tokens.
- **Outcome:** Added shared primitives in `web/src/components/ui/tabs.tsx`, rewired `web/src/components/Tabs.tsx` to use them with router-driven navigation, and removed the legacy stylesheet.
- **Historical context:** Pre-migration, the nav relied on bespoke CSS and manual class toggles, so this section is retained for audit history only.
- **Definition of done (met):**
  1. Replace the legacy markup with the shadcn `Tabs` (or a Radix-based variant) that surfaces focus-visible states and aria roles.
  2. Move tab labels/icons into the new component while retaining route navigation via `react-router`.
  3. Delete `Tabs.css` and adjust snapshot/RTL coverage to reflect the new structure.

### F-6: Standardise Admin Surfaces on the Typed API Client
- **Status:** ✅ Completed 2025-11-01 – admin surfaces now route through the shared API client.
- **Outcome:** `ScrapingTab`, `TrainingTab`, and `BatchGallery` call `api.scraping`, `api.training`, and `api.batches`; shared utilities live in `web/src/lib/adminJobs.ts`; Zod schemas cover scraping/training responses and tests exercise the new client paths.
- **Why it matters:** Admin-only tabs bypass the shared `api` client, so they miss trace IDs, error normalisation, and auth handling that other views rely on. The duplicated helpers (e.g. `clampProgress`) drift between tabs.
- **Current state:**
  - `web/src/components/ScrapingTab.tsx:57-188`, `TrainingTab.tsx:235-360`, and `BatchGallery.tsx:140-194` all call `fetch` directly and hand-roll status handling.
  - Progress utilities (`clampProgress`, status colours) live in multiple files with conflicting signatures.
- **Definition of done:**
  1. Swap the raw `fetch` calls for `api.scraping`, `api.training`, and `api.gallery` helpers (extending `lib/api.ts` as needed) so errors funnel through `formatErrorMessage`.
  2. Extract shared admin-job utilities (progress clamps, status colours, GB formatting) into `web/src/lib` and reuse them.
  3. Backfill tests that mock the new client to confirm 401 handling and toast messaging.

## Priority P2

### F-3: Regression Tests for Admin-Gated Workflows
- **Why it matters:** Queue security and bug reporting now depend on `AuthContext` but lack automated coverage, making future changes risky.
- **Current state:** No dedicated RTL tests exist for `QueueTab` or the settings menu bug-report flow (`web/src/components/__tests__` only houses error-boundary coverage).
- **Definition of done:**
  1. Add RTL tests that mock admin vs viewer contexts to assert `QueueTab` renders the authentication banner and stops polling on 401 responses.
  2. Add tests covering the settings menu bug-report entry and keyboard shortcut to guard against regressions.

### F-7: Consolidate Polling Hooks into a Single API
- **Why it matters:** Both polling hooks pause on hidden tabs, debounce interval changes, and clean up timers, but they diverge in behaviour (e.g. adaptive timing vs. fixed). Keeping two implementations risks regressions when only one path is updated.
- **Current state:**
  - `web/src/hooks/usePolling.ts` and `web/src/hooks/useAdaptivePolling.ts` duplicate timer setup, visibility handlers, and cleanup logic.
  - `QueueTab` consumes the adaptive hook while `ScrapingTab` and `TrainingTab` use the static version, so fixes must be applied twice.
- **Definition of done:**
  1. Merge the hooks into a single `usePolling` with optional adaptive settings and shared tests.
  2. Update all call sites to the unified API and remove the deprecated hook file.
  3. Extend hook tests to cover adaptive intervals, pause-on-hidden, and immediate-run scenarios.

### F-8: Retire the Shadcn Test Route from the Production Bundle
- **Status:** ✅ Completed 2025-11-01
- **Outcome:** Removed the lazy import and route guard from `App.tsx`, deleted `ShadcnTest.tsx`, and reran type-check/tests to confirm the build stays green.


### F-9: Harmonise Layout Shell
- **Status:** ⏳ Not started
- **Why it matters:** Each tab currently manages its own padding/typography, leading to inconsistent spacing once the shadcn theme is applied.
- **Current state:** `App.css` mixes legacy `.container` styles with new components; some tabs apply custom background colours.
- **Definition of done:**
  1. Replace the top-level header/container with shared layout components (`AppShell`, `PageHeader`, `PageContent` or equivalent).
  2. Remove redundant CSS once the layout wrappers are in use.
  3. Verify dark-mode tokens are respected (no hard-coded light backgrounds).

### F-10: Standardise Feedback & Loading States
- **Status:** ⏳ Not started
- **Why it matters:** The toaster provider exists, but a few flows still rely on `alert()`/`console.log`, and loading states mix bespoke spinners with shadcn skeletons.
- **Current state:** Toasts are wired for Generate/Albums, while Scraping/Training still emit console output for some errors; loading UIs vary by tab.
- **Definition of done:**
  1. Replace legacy messaging with `toast.*` helpers (reuse existing context where possible).
  2. Swap ad-hoc spinners for `Skeleton`/`Spinner` components from `@/components/ui`.
  3. Add/adjust tests to cover error surface + loading indicator expectations.

---

**Next review:** Re-assess after completing F-1 and F-2 or by 2025-11-15, whichever comes first.
