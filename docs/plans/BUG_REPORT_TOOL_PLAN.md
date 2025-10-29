## Bug Report Capture Tool – Progress Log (October 29, 2025)

### Current Progress

- Implemented initial frontend plumbing for bug report capture:
  - Added `BugReportProvider`, modal trigger button, and logging/network interceptors in the React app.
  - Extended the shared logger to stream log events to registered listeners.
  - Introduced preliminary bug report API hook and schemas (`BugReportResponseSchema`).
- Added TODO scaffolding for local storage of reports (currently assumes `/api/bug-reports` endpoint exists).
- Instrumented `AppContent` to expose summary state snapshots through the bug reporter collector interface.
- Created styling and UI components for the bug report modal and trigger button.

### Gaps / Work Remaining

1. **Server-Side Storage & API**
   - Build `/api/bug-reports` endpoint to persist reports locally on the server (filesystem or database).
   - Define storage schema (JSONL, SQLite table, etc.) including captured logs, network traces, client metadata, and optional trace IDs.
   - Return canonical `trace_id` and `report_id` values (and surface them back to the UI).

2. **Frontend Error Telemetry → Server**
   - Forward client-side errors and unhandled promise rejections to a server logging endpoint immediately.
   - Ensure every logged error includes/receives a server-generated trace ID for correlation.

3. **Trace ID Propagation**
   - Have the backend attach `X-Trace-Id` to every response (all Flask routes + error handlers).
   - Update the API client to forward trace IDs on subsequent requests and include them in bug report payloads.

4. **Network Capture Enhancements**
   - Send recorded network event payloads alongside bug report submissions.
   - Decide on safe body redaction rules (PII, secrets) for persisted reports.

5. **System Health & Review Interface**
   - Add CLI tooling or admin-only UI to browse/clear stored bug reports.
   - Consider retention policy, disk usage caps, and optional export functionality.

6. **Automated Tests & Docs**
   - Unit/integration tests for the provider, logger instrumentation, and new REST endpoint.
   - Update developer documentation covering bug report workflow, trace IDs, and troubleshooting steps.

### Next Recommended Steps

1. Design backend data model for bug reports (e.g., `server/bug_reports.py` module).
2. Implement Flask endpoint with authentication guard (viewer/admin decision required).
3. Wire frontend submission to the real endpoint, handling failure states gracefully.
4. Create utility to stream client error logs to the new endpoint (e.g., `POST /api/logs/client-error`).
5. Add CI tests ensuring report submission stores payload and that trace IDs round-trip.

> Note: **No commits/pushes performed**. Pending backend work is required before merging. Ensure coordination with DevOps for storage location and retention policies.
