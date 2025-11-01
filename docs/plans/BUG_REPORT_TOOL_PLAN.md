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

7. **Screenshot Capture (Planned)**
   - Capture screenshot automatically on submission using `html2canvas`.
   - Provide preview + include checkbox (default on), no retake option.
   - Allow simple red annotations before sending.
   - On failure, alert user, continue submission, record failure in bug report JSON.
   - Store `{report_id}/screenshot.png` alongside other report artifacts.

1. **Server-Side Storage & API** ✅ *(Completed 2025-11-01)*
   - `/api/bug-reports` implemented with list/detail/update/delete/purge.
   - JSON file storage defined alongside CLI tooling for operators.
   - Responses include canonical `trace_id` and `report_id`.

2. **Frontend Error Telemetry → Server**
   - Forward client-side errors and unhandled promise rejections to a server logging endpoint immediately.
   - Ensure every logged error includes/receives a server-generated trace ID for correlation.

3. **Trace ID Propagation** ✅ *(Completed)*
   - Middleware shipped Oct 2025; currently active end-to-end.

4. **Network Capture Enhancements** ✅ *(Completed)*
   - Network capture ships with redaction caps (50 events, size limits).

5. **System Health & Review Interface** ✅ *(Completed 2025-11-01)*
   - Admin API + `scripts/bug_reports.py` cover listing, resolution, retention purge.

6. **Automated Tests & Docs** ✅ *(Completed 2025-11-01)*
   - Backend tests cover submission + admin routes; docs refreshed in workflow guide.

### Next Recommended Steps

1. Design backend data model for bug reports (e.g., `server/bug_reports.py` module).
2. Implement Flask endpoint with authentication guard (viewer/admin decision required).
3. Wire frontend submission to the real endpoint, handling failure states gracefully.
4. Create utility to stream client error logs to the new endpoint (e.g., `POST /api/logs/client-error`).
5. Add CI tests ensuring report submission stores payload and that trace IDs round-trip.

> Note: **No commits/pushes performed**. Pending backend work is required before merging. Ensure coordination with DevOps for storage location and retention policies.
