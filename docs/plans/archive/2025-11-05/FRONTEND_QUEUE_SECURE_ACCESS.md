# Frontend Task: Secure Job Queue UX

Updated: November 1, 2025  
Owner: Web Platform · Status: ✅ Completed (landed in QueueTab refactor 2025-10-30)

**Verification Notes (2025-11-01):**
- `web/src/components/QueueTab.tsx` now short-circuits with an admin-auth banner when `/api/jobs` returns 401 and stops polling via `useAdaptivePolling`.
- All queue fetches go through the typed API client with `credentials: 'include'` and `Retry-After` handling (`web/src/lib/api.ts`).
- Queue UI reads sanitized fields (`output_filename`, `output_directory`) and never renders queue data for viewers.

## Background
Backend changes now require admin authentication for `/api/jobs` and `/api/jobs/{id}` and return sanitized payloads (`output_filename`, `output_directory`, shortened `lora_paths`). Anonymous calls receive `401 Unauthorized`.

## Required UI Changes
- **Authenticated fetches**: Ensure all queue polling (e.g., `QueueTab`, `App.tsx` job poller) sends `credentials: 'include'` and handles 401/403 by prompting the admin to re-authenticate.
- **Field mapping**: Update components to read `output_filename`/`output_directory` instead of raw path keys. Remove any client logic that expects absolute paths.
- **Admin gating**: Hide queue controls and metrics entirely for non-admin users. Use the upcoming `AuthContext` (#14) so access checks stay centralized and reusable.
- **Error messaging**: Surface a friendly banner or toast when the queue view is inaccessible due to missing admin rights, with a call-to-action to sign in. Ensure we never continue polling after a permission failure.

## QA Checklist
- Admin session loads queue successfully and displays sanitized filenames.
- Non-admin or expired session never renders queue data, sees clear messaging, and polling stops until re-authenticated.
- Job detail views (`/api/jobs/{id}`) continue to update the UI without requiring path assumptions.
