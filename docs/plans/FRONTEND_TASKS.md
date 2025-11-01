# Frontend Task Backlog (Updated 2025-11-01)

This backlog reflects the outstanding frontend work after verifying the codebase on 2025-11-01. Items marked completed in the archived 2025-10-31 plan are now in `docs/plans/archive/FRONTEND_TASKS_2025-10-31.md`.

## Priority P0

### F-1: Expand NSFW Filter Controls and Persistence
- **Why it matters:** Compliance reviewers require blur/hide options instead of a single hide toggle so admins can audit content safely without exposing NSFW imagery to viewers.
- **Current state:**
  - `web/src/contexts/AppContext.tsx` still exposes a boolean `nsfwEnabled` flag with no persistence or blur mode.
  - `web/src/components/SettingsMenu.tsx` renders a simple checkbox and does not store preferences.
  - Views such as `ImageCard` support badges but rely on the boolean hide behaviour.
- **Definition of done:**
  1. Replace the boolean with an enum (`'show' | 'blur' | 'hide'`) persisted to `localStorage`.
  2. Update `SettingsMenu` to expose the three-state picker and reflect the stored selection.
  3. Update `ImageCard` (and any callers) to blur when requested and hide only when in `hide` mode.
  4. Adjust unit tests in `web/src/components/common/ImageCard.test.tsx` (and add new ones) to cover all modes.

## Priority P1

### F-2: Apply ImageCard Consistently Across Gallery Surfaces
- **Why it matters:** The shared NSFW and label badge behaviour only runs inside the new `ImageCard`. `ImageGrid.tsx` and `BatchGallery.tsx` still render bespoke cards that ignore NSFW settings and omit badges, creating inconsistent moderation.
- **Current state:**
  - `web/src/components/ImageGrid.tsx` renders inline `<img>` tags with no NSFW or label handling.
  - `web/src/components/BatchGallery.tsx` defines a local `BatchImageCard` component with duplicated logic and no badge support.
- **Definition of done:**
  1. Replace the bespoke cards with the shared `ImageCard` component (or extract a thin adapter) so all grids honour the global NSFW preference and badges.
  2. Ensure `useGallery()`’s `nsfwEnabled` value feeds the cards in both views.
  3. Add regression tests (RTL) covering NSFW hide/blur behaviour inside `GalleryTab` and `BatchGallery`.

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
- **Why it matters:** The `/shadcn-test` route exposes a developer-only showcase in production builds, increases bundle size, and duplicates component demos better suited for Storybook.
- **Current state:**
  - `web/src/App.tsx:214-223` still defines a route pointing at `ShadcnTest`.
  - `web/src/components/ShadcnTest.tsx` pulls in multiple UI primitives solely for the demo page.
- **Definition of done:**
  1. Remove the route (or guard it behind `import.meta.env.DEV`) so it never ships to end users.
  2. Move any useful examples into Storybook/docs and delete the component when redundant.
  3. Update routing tests to reflect the reduced surface area.

---

**Next review:** Re-assess after completing F-1 and F-2 or by 2025-11-15, whichever comes first.
