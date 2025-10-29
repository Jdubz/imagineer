# Frontend Task: Secure Job Queue UX

Updated: October 29, 2025  
Owner: Web Platform · Status: Open

## Background
Backend changes now require admin authentication for `/api/jobs` and `/api/jobs/{id}` and return sanitized payloads (`output_filename`, `output_directory`, shortened `lora_paths`). Anonymous calls receive `401 Unauthorized`.

## Required UI Changes
- **Authenticated fetches**: Ensure all queue polling (e.g., `QueueTab`, `App.tsx` job poller) sends `credentials: 'include'` and handles 401/403 by prompting the admin to re-authenticate.
- **Field mapping**: Update components to read `output_filename`/`output_directory` instead of raw path keys. Remove any client logic that expects absolute paths.
- **Error messaging**: Surface a friendly banner or toast when the queue view is inaccessible due to missing admin rights, with a call-to-action to sign in.

## QA Checklist
- Admin session loads queue successfully and displays sanitized filenames.
- Non-admin or expired session sees clear messaging and never renders stale data.
- Job detail views (`/api/jobs/{id}`) continue to update the UI without requiring path assumptions.
