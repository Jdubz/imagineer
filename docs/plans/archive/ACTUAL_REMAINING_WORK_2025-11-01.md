# Actual Remaining Frontend Work

**Date:** 2025-11-01  
**Source:** Verification of `develop` branch code

---

## ✅ What’s Already Done
- **Bug reporter UX** is wired end-to-end:
  - Settings menu exposes the “Report Bug” entry with keyboard shortcut support (`web/src/components/SettingsMenu.tsx`, `web/src/App.tsx`).
  - Error boundaries include the bug-report button and pre-fill stack traces (`web/src/components/ErrorBoundaryWithReporting.tsx`).
  - `BugReportContext` captures logs, network events, and submits via the `/api/bug-reports` endpoint.
- **Shared ImageCard component** exists (`web/src/components/common/ImageCard.tsx`) with unit coverage and supports NSFW badges, label badges, and click-through modals.
- **Auth-aware polling and admin gating** are live in QueueTab and fetch helpers; all API calls use `credentials: 'include'` with retry-after handling (`web/src/lib/api.ts`).

---

## ⚠️ Work That Still Needs Attention

### 1. NSFW Filter Modes & Persistence
- `AppContext` still exposes a boolean `nsfwEnabled` flag with no persistence (`web/src/contexts/AppContext.tsx`).
- `SettingsMenu` renders a simple checkbox toggle and cannot switch between blur vs hide (`web/src/components/SettingsMenu.tsx`).
- `ImageCard` only distinguishes between “show” and “hide”; blur is not implemented even though moderation asked for it.

**Action Items**
1. Replace the boolean with an enum (`'show' | 'blur' | 'hide'`) and persist the selection to `localStorage`.
2. Update settings UI to present the three options and reflect stored preference on load.
3. Teach `ImageCard` to blur thumbnails when requested and hide only in `hide` mode; add unit specs to cover all branches.

### 2. Gallery Surfaces Must Use ImageCard
- `ImageGrid.tsx` still renders bespoke `<img>` tags and ignores NSFW/label badges entirely.
- `BatchGallery.tsx` defines `BatchImageCard` with duplicated logic and no NSFW handling.
- `useGallery()` already exposes `nsfwEnabled`, but neither view reads it, so toggling the filter has no effect outside AlbumsTab.

**Action Items**
1. Replace bespoke gallery cards with `ImageCard` (or an adapter) so all surfaces honour the global NSFW setting and badges.
2. Ensure gallery views feed label counts when available so the badge is consistent with AlbumsTab.
3. Add RTL coverage proving NSFW hide/blur propagates through `GalleryTab` and `BatchGallery`.

### 3. Regression Coverage for Admin-Only Flows (Optional but Recommended)
- `QueueTab`’s admin banner and bug-report entry rely on `AuthContext`, yet no RTL tests exist to prevent regressions.

**Action Items**
1. Add tests that simulate viewer vs admin sessions, asserting the queue banner appears and polling stops on 401.
2. Cover the settings menu bug-report entry and keyboard shortcut to guard against accidental removals.

---

**Summary:** The blocker-level work now centres on finishing the NSFW preference experience and applying the shared `ImageCard` across the remaining gallery components. Once those are complete, focus shifts to tightening regression coverage for the new auth pathways.
