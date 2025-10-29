# Frontend Adaptations for Backend Auth Changes

Updated: October 29, 2025  
Owner: Web Platform · Status: Draft

## Context
Backend hardening (October 29, 2025) now enforces admin authentication on several endpoints used by the web app:

- `GET /api/config`, `PUT /api/config`, `PUT /api/config/generation`
- `PUT /api/sets/<set_name>/loras`
- `DELETE /api/jobs/<id>`

These routes previously accepted anonymous calls. The frontend must account for the new 401/403 failure modes, surface clear messaging, and ensure admin-only actions stay behind authenticated UI flows.

## Required Frontend Updates
- **Config bootstrap (`App.tsx:74-81`)**  
  - Handle 401/403 by prompting for admin login (e.g., surface the OAuth modal via `AuthButton`) instead of blindly calling `response.json()`.  
  - Confirm `fetch('/api/config')` is invoked with cookie credentials (same-origin defaults are fine, but add `credentials: 'include'` explicitly for clarity).

- **Config mutation UI (wherever `/api/config` PUTs are issued)**
  - Ensure requests include admin cookies (`credentials: 'include'`).
  - Surface an “admin session expired” toast/dialog when the backend returns 401/403.
  - Gate config editing controls behind an `isAdmin` check so anonymous viewers never see write buttons.

- **Job queue views (`QueueTab`, polling in `App.tsx`)**
  - `/api/jobs` and `/api/jobs/{id}` now require an authenticated admin session and return sanitized payloads (`output_filename`, `output_directory`, shortened `lora_paths`).
  - Update fetches to send cookies, handle 401s by prompting for re-auth, and adjust UI to read the sanitized field names.

- **LoRA management (`GenerateForm.tsx:119-177`)**
  - The `updateSetLoras` call to `PUT /api/sets/<set_name>/loras` must add `credentials: 'include'`.
  - Handle 401/403 responses by informing the user their admin session is required and revert local optimistic updates.
  - Consider disabling the LoRA edit UI for non-admin accounts (currently it is always enabled).

- **Job cancellation actions**  
  - Any UI invoking `DELETE /api/jobs/<id>` (future queue management) must include credentials and treat 401/403 as “admin permission required”.  
  - Until admin gating is implemented client-side, avoid exposing cancel controls to non-admin users.

## Testing & Tooling
- Update frontend mocks (`web/src/App.test.tsx`) to expect 401 responses when the test harness simulates unauthenticated access to the secured routes.  
- Add Cypress/Playwright (or RTL) coverage to verify that non-admin sessions see appropriate messaging and that admin sessions can still load/update configuration and LoRA sets.

## Additional Notes
- October 29, 2025 — Backend now tolerates Google OAuth callbacks that arrive on double-encoded paths (e.g., `/api/auth/google/%2Fhttps://...`). No frontend change is required, but please avoid adding ad-hoc rewrites in the SPA; keep relying on `AuthButton`’s sanitized state handling so we can surface regressions if they reappear.

## Open Questions
- Do we want a dedicated “Admin Console” route instead of auto-fetching `/api/config` on app load?  
- Should the app proactively refresh admin sessions (e.g., on visibility change) to avoid silent 401s mid-workflow?
