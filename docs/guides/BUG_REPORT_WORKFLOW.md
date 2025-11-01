# Bug Report Workflow Guide

Complete guide for using the in-app bug reporting system in Imagineer.

## Table of Contents

- [Overview](#overview)
- [For Admins: Submitting Bug Reports](#for-admins-submitting-bug-reports)
- [For Developers: Reviewing Bug Reports](#for-developers-reviewing-bug-reports)
- [Technical Details](#technical-details)
- [Troubleshooting](#troubleshooting)

---

## Overview

Imagineer includes an admin-only bug reporting system that captures comprehensive context about errors and issues. Bug reports include:

- User-provided description
- Recent console logs (last 200 entries)
- Network request/response history (last 50 events)
- Application state snapshot
- Browser/system environment info
- Trace ID for backend correlation
- Component stack traces (when triggered from ErrorBoundary)

**Key Features:**
- ✅ Admin-only access
- ✅ Keyboard shortcut: `Ctrl+Shift+B`
- ✅ Pre-filled error details from ErrorBoundary
- ✅ Automatic context capture
- ✅ Trace IDs for request correlation
- ✅ 30-day retention policy

---

## For Admins: Submitting Bug Reports

### Method 1: Settings Menu

1. **Click the gear icon (⚙️)** in the top-right corner
2. **Click "Report Bug"** from the dropdown menu
3. **Enter a description** of the issue in the modal
4. **Click "Submit Report"**

The system will automatically capture:
- Recent console logs
- Network activity
- Current application state
- Your browser and system info

### Method 2: Keyboard Shortcut

Press **Ctrl+Shift+B** (Windows/Linux) or **Cmd+Shift+B** (Mac) from anywhere in the application.

> **Note:** This shortcut only works for admin users. Viewer users will not see the bug report button or have access to the keyboard shortcut.

### Method 3: From Error Boundaries

When an error occurs in the application:

1. An error screen will appear with a **"🐞 Report Bug"** button
2. Click the button to open a pre-filled bug report
3. The error message, stack trace, and component stack are automatically included
4. Add any additional context in the description
5. Submit the report

---

## For Developers: Reviewing Bug Reports

### Report Location

Bug reports are stored as JSON files in:
```
/mnt/storage/imagineer/bug_reports/
```

Each report is named: `bug_<timestamp>_<trace_id_prefix>.json`

Example: `bug_20251029_162130_80da821b.json`

### Report Structure

```json
{
  "report_id": "bug_20251029_162130_80da821b",
  "trace_id": "80da821b-104f-42d9-b15e-43e53cd6a1d6",
  "submitted_at": "2025-10-29T16:21:30.123Z",
  "submitted_by": "admin@example.com",
  "user_role": "admin",
  "status": "open",

  "description": "User-provided description of the issue",

  "environment": {
    "userAgent": "Mozilla/5.0...",
    "language": "en-US",
    "platform": "Linux x86_64",
    "screenResolution": "1920x1080",
    "viewport": {"width": 1920, "height": 937},
    "timezone": "America/Los_Angeles"
  },

  "clientMeta": {
    "url": "http://localhost:3000/generate",
    "timestamp": "2025-10-29T16:21:30.123Z",
    "appVersion": "1.0.0"
  },

  "appState": {
    "route": {
      "pathname": "/generate",
      "search": "",
      "hash": ""
    },
    "activeTab": "generate",
    "loading": {
      "generate": false,
      "images": false,
      "batches": false
    },
    "queuePosition": null,
    "counts": {
      "batches": 42,
      "images": 156
    },
    "currentJob": null,
    "config": {...},
    "user": {
      "authenticated": true,
      "email": "admin@example.com",
      "role": "admin"
    },
    "imagePreview": [...],
    "batchPreview": [...]
  },

  "recentLogs": [
    {
      "timestamp": "2025-10-29T16:21:25.456Z",
      "level": "info",
      "message": "Config loaded successfully",
      "context": {...}
    }
  ],

  "networkEvents": [
    {
      "timestamp": "2025-10-29T16:21:28.789Z",
      "type": "request",
      "url": "http://localhost:10051/api/config",
      "method": "GET",
      "headers": {...},
      "status": 200,
      "duration": 45,
      "response": {...}
    }
  ]
}
```

### Reviewing Reports

### Using the Maintenance CLI

The repository ships with `scripts/bug_reports.py`, which mirrors the admin API:

```bash
# List reports (sorted newest first)
./scripts/bug_reports.py list

# Show a single report
./scripts/bug_reports.py show bug_20251029_162130_80da821b

# Mark a report resolved with optional resolution metadata
./scripts/bug_reports.py update bug_20251029_162130_80da821b \
  --status resolved \
  --resolution '{"commit": "abc123", "note": "Patched in hotfix"}'

# Delete reports older than the retention window (dry run first)
./scripts/bug_reports.py purge --dry-run
./scripts/bug_reports.py purge
```

Pass `--root /custom/path` if the storage directory differs from the config.

### Working with Files Directly

All CLI operations manipulate the underlying JSON files, so you can still
use standard tooling when needed:

- **List newest reports**
  ```bash
  ls -lth /mnt/storage/imagineer/bug_reports/ | head -20
  ```

- **Pretty-print a report**
  ```bash
  cat /mnt/storage/imagineer/bug_reports/bug_20251029_162130_80da821b.json | jq .
  ```

- **Search by trace ID**
  ```bash
  grep -r "80da821b" /mnt/storage/imagineer/bug_reports/
  ```

- **Update status manually**
  ```bash
  jq '.status = "resolved"' \
    /mnt/storage/imagineer/bug_reports/bug_20251029_162130_80da821b.json \
    > /tmp/temp.json && \
    mv /tmp/temp.json /mnt/storage/imagineer/bug_reports/bug_20251029_162130_80da821b.json
  ```

### Correlating with Backend Logs

Every request includes a `X-Trace-Id` header. Use this to find related backend activity:

```bash
# Find backend logs for a specific trace ID
grep "80da821b-104f-42d9-b15e-43e53cd6a1d6" /path/to/flask/logs/*.log
```

---

## Technical Details

### API Endpoint

**POST** `/api/bug-reports`

**Authentication:** Admin role required

**Request Body:**
```json
{
  "description": "User description (required)",
  "environment": {...},
  "clientMeta": {...},
  "appState": {...},
  "recentLogs": [...],
  "networkEvents": [...]
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "report_id": "bug_20251029_162130_80da821b",
  "trace_id": "80da821b-104f-42d9-b15e-43e53cd6a1d6",
  "stored_at": "/mnt/storage/imagineer/bug_reports/bug_20251029_162130_80da821b.json"
}
```

**Response (401 Unauthorized):**
```json
{
  "error": "Authentication required",
  "error_code": "UNAUTHORIZED",
  "trace_id": "80da821b-104f-42d9-b15e-43e53cd6a1d6",
  "timestamp": "2025-10-29T16:21:30.123Z"
}
```

### Trace ID System

**How It Works:**
1. Client can send `X-Trace-Id` header in requests (optional)
2. If not provided, server generates a new UUID
3. Server includes `X-Trace-Id` in all responses
4. Bug reports include the trace ID for correlation

**Client-Side Example:**
```typescript
fetch('/api/bug-reports', {
  method: 'POST',
  headers: {
    'X-Trace-Id': 'my-custom-trace-id',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({...})
})
```

### Context Collectors

The `BugReportProvider` uses a collector pattern to gather context:

```typescript
// Register a collector
const unregister = registerCollector('my_context', () => {
  return {
    customData: 'value',
    timestamp: Date.now()
  }
})

// Unregister when component unmounts
useEffect(() => {
  return unregister
}, [])
```

Built-in collectors:
- `application_state` - Current app state (App.tsx)
- `environment` - Browser/system info (BugReportProvider)
- `recent_logs` - Last 200 console entries (BugReportProvider)
- `network_events` - Last 50 HTTP requests (BugReportProvider)

### Configuration

In `config.yaml`:

```yaml
bug_reports:
  storage_path: /mnt/storage/imagineer/bug_reports
  retention_days: 30  # Purge job + /api/bug-reports/purge honour this value
```

### Admin Maintenance API

In addition to the submission endpoint, admins can automate triage through the REST API:

- `GET /api/bug-reports` — Paginated list of reports (`status`, `page`, `per_page` filters).
- `GET /api/bug-reports/<report_id>` — Retrieve a full report JSON payload.
- `PATCH /api/bug-reports/<report_id>` — Update `status` (`open`/`resolved`) and append `resolution` metadata.
- `DELETE /api/bug-reports/<report_id>` — Remove a stored report.
- `POST /api/bug-reports/purge` — Delete reports older than the retention window (`older_than_days`, `dry_run` supported).

All routes require an authenticated admin session and return JSON suitable for scripting.

---

## Troubleshooting

### Bug Report Button Not Visible

**Symptom:** Gear icon or "Report Bug" button not showing

**Solutions:**
1. Verify you're logged in as an admin user
2. Check browser console for JavaScript errors
3. Refresh the page to ensure latest code is loaded
4. Verify `user?.role === 'admin'` in React DevTools

### Keyboard Shortcut Not Working

**Symptom:** Ctrl+Shift+B does nothing

**Solutions:**
1. Ensure you're an admin user (viewers don't have access)
2. Check if you're typing in an input field (shortcuts are disabled there)
3. Try clicking outside any input fields and press again
4. Check browser console for errors
5. Verify `useKeyboardShortcut` hook is registered in App.tsx:95-105

### Bug Report Submission Fails

**Symptom:** Error message when submitting report

**Solutions:**

**401 Unauthorized:**
- Log out and log back in
- Check if your session expired
- Verify admin role in `/api/auth/me`

**403 Forbidden:**
- Your user account is not an admin
- Contact system administrator

**500 Internal Server Error:**
- Check Flask server logs: `/tmp/flask_bug_reporter_test.log`
- Verify storage directory exists and is writable:
  ```bash
  sudo mkdir -p /mnt/storage/imagineer/bug_reports
  sudo chown $USER:$USER /mnt/storage/imagineer/bug_reports
  ```
- Check disk space: `df -h /mnt/storage`

### Cannot Find Bug Reports

**Symptom:** Reports not appearing in expected directory

**Solutions:**
1. Check configured path in `config.yaml`
2. Verify directory permissions:
   ```bash
   ls -la /mnt/storage/imagineer/
   ```
3. Check Flask startup logs for warnings
4. Test with curl:
   ```bash
   curl -X POST http://localhost:10051/api/bug-reports \
     -H "Content-Type: application/json" \
     -H "Cookie: session=<your-session>" \
     -d '{"description":"Test report"}'
   ```

### Trace IDs Not Matching

**Symptom:** Cannot correlate frontend bug reports with backend logs

**Solutions:**
1. Verify middleware is registered in `server/api.py`
2. Check that frontend sends trace ID in requests
3. Grep backend logs for partial trace ID:
   ```bash
   grep "80da821b" /var/log/flask/*.log
   ```

---

## Best Practices

### For Admins

1. **Be Descriptive:** Include steps to reproduce, expected vs actual behavior
2. **Check Existing Reports:** Avoid duplicates by reviewing recent reports
3. **Include Context:** Mention what you were doing when the error occurred
4. **Test in Incognito:** Try reproducing in a clean browser session

### For Developers

1. **Review Regularly:** Check bug reports at least daily
2. **Correlate with Logs:** Use trace IDs to find related backend activity
3. **Mark as Resolved:** Move or update status when fixed
4. **Clean Up Old Reports:** Manually delete reports older than 30 days
5. **Monitor Disk Usage:** Bug reports can accumulate over time

### For DevOps

1. **Set Up Log Rotation:** Ensure Flask logs don't fill disk
2. **Monitor Storage:** Alert on `/mnt/storage` disk usage
3. **Backup Reports:** Include bug reports in backup strategy
4. **Security:** Bug reports may contain sensitive data - protect accordingly

---

## Related Documentation

- [BUG_REPORT_IMPLEMENTATION_PLAN.md](../plans/BUG_REPORT_IMPLEMENTATION_PLAN.md) - Implementation details
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture
- [API_DOCUMENTATION.md](../API_DOCUMENTATION.md) - Full API reference

---

## Support

If you encounter issues with the bug reporting system:

1. Check this troubleshooting guide
2. Review Flask server logs
3. Check browser console for errors
4. Contact the development team with:
   - Trace ID from response headers
   - Screenshots of error messages
   - Browser and OS version
