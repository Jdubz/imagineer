# Imagineer Frontend Styling Plan (shadcn/ui)

**Updated:** 2025-11-01  
**Scope:** Single shared SPA for two internal users (admin + viewer). Focus on a minimal, cohesive interface; no marketing gallery or advanced dashboards.

---

## Goals
1. **Consistency:** Every screen uses shadcn primitives (buttons, dialogs, tabs, selects, toasts) with our existing theme tokens.
2. **Simplicity:** Keep the current routes (`/generate`, `/gallery`, `/albums`, `/scraping`, `/training`, `/queue`, `/loras`) and polish their layout; no hero carousels, no masonry experiments.
3. **Maintainability:** Remove demo/test routes, delete legacy CSS, and standardise spacing/typography so future tweaks are easy.

---

## Current Status
- Phase 1 (foundation + theme) ✅ – shadcn is installed, tokens configured.
- Phase 2 (component migration) ✅ – core primitives and toasts migrated.
- `/shadcn-test` demo route still exists and should be removed.
- Some legacy containers (`App.css`, ad-hoc padding) still need cleanup.

---

## Remaining Work (Priority P1)

### 1. Remove Demo Route
- Delete `components/ShadcnTest.tsx`.
- Remove the lazy import and `<Route path="/shadcn-test" …>` from `App.tsx`.
- Ensure navigation/tests no longer reference the demo.

### 2. Harmonise Layout
- Introduce shared wrappers (`AppShell`, `PageHeader`, `PageContent`) using shadcn cards/dividers for consistent spacing.
- Replace bespoke `.container`/`.main-content` CSS with layout components.
- Audit dark-mode tokens so we avoid hard-coded light backgrounds.

### 3. Feedback & Loading
- Confirm `Toaster` is the only toast provider.
- Replace any remaining ad-hoc spinners with `Skeleton`/`Spinner` components from `@/components/ui`.
- Remove leftover `alert()` / `console.log` user messaging.

Deliverable: existing tabs feel cohesive and minimalist without introducing new features.

---

## Optional Enhancements (P3 / Future)
- Sidebar layout for widescreens.
- Animated transitions or skeleton choreography.
- Read-only “public gallery” toggle (only if requirements appear).

---

## Open Questions
1. Do we need a read-only gallery mode for unauthenticated visitors, or is the current gating sufficient?
2. Should we add Storybook/visual regression tooling, or keep manual QA for now?
3. Are there upcoming features that would benefit from pre-building additional shadcn primitives?

---

## Success Criteria
- All routes use shadcn components for interactive elements.
- No references to the old `/shadcn-test` page.
- App header/footer/layout share consistent spacing, typography, and background tokens.
- Dark/light modes remain legible without ad-hoc overrides.
