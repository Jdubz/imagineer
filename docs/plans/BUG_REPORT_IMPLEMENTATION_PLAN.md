# Bug Report Tool - Implementation Plan

**Created:** 2025-10-29
**Status:** Backend delivered; frontend integration pending
**Priority:** Medium
**Estimated Time:** 8-12 hours

---

## Overview

Complete the bug report capture tool that allows admin users to submit detailed bug reports with automatic context capture including logs, network events, application state, and error information. Reports are stored on the server filesystem for manual review.

---

## Current Status

### ✅ Already Implemented (Frontend)
- `BugReportProvider` context with network interception
- Log collection (max 200 entries)
- Network event capture (max 50 requests)
- Application state collector pattern
- Bug report modal UI
- `BugReportButton` component
- Type definitions for bug reports
- `ErrorBoundary` component (without bug report integration)

### ❌ Missing Components
- Settings menu entry to surface the bug report modal
- Keyboard shortcut (Ctrl+Shift+B)
- ErrorBoundary integration hook
- Error toast with bug report button
- Frontend display of the server-provided trace ID

---

## Implementation Plan

### Phase 1: Backend Infrastructure (3-4 hours) ✅ Completed Oct 30, 2025

#### 1.1 Trace ID Middleware
**File:** `server/middleware/trace_id.py`

```python
import uuid
from flask import g, request
from functools import wraps

def generate_trace_id():
    """Generate unique trace ID for request"""
    return str(uuid.uuid4())

def trace_id_middleware(app):
    """Add trace ID to every request"""

    @app.before_request
    def before_request():
        # Check if trace ID provided by client
        g.trace_id = request.headers.get('X-Trace-Id') or generate_trace_id()

    @app.after_request
    def after_request(response):
        # Attach trace ID to response
        response.headers['X-Trace-Id'] = g.trace_id
        return response
```

**Implementation status:** Registered in `server/api.py`; trace IDs propagate through error handlers.

#### 1.2 Structured Error Responses
**File:** `server/utils/error_handler.py`

```python
from datetime import datetime
from flask import g, jsonify

class APIError(Exception):
    """Base API error with structured format"""
    def __init__(self, message, error_code=None, status_code=400, details=None):
        self.message = message
        self.error_code = error_code or 'GENERIC_ERROR'
        self.status_code = status_code
        self.details = details or {}

def format_error_response(error, trace_id=None):
    """Format error as structured JSON"""
    return {
        'error': str(error) if not isinstance(error, APIError) else error.message,
        'error_code': error.error_code if isinstance(error, APIError) else 'INTERNAL_ERROR',
        'trace_id': trace_id or getattr(g, 'trace_id', None),
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'details': error.details if isinstance(error, APIError) else {}
    }
```

**Implementation status:** Structured responses active across Flask error handlers and propagated to clients.

#### 1.3 Bug Report Storage
**File:** `server/routes/bug_reports.py`

```python
import os
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from server.auth import require_admin
from server.logging_config import logger

bug_reports_bp = Blueprint('bug_reports', __name__)

def get_bug_reports_dir():
    """Get bug reports directory from config"""
    from server.config import get_config
    config = get_config()
    return config.get('bug_reports', {}).get('storage_path',
                                              '/mnt/storage/imagineer/bug_reports')

@bug_reports_bp.route('/api/bug-reports', methods=['POST'])
@require_admin
def submit_bug_report():
    """
    Submit a bug report with full context
    Admin-only endpoint
    """
    try:
        payload = request.get_json()

        # Generate report ID and trace ID
        report_id = f"bug_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{g.trace_id[:8]}"

        # Create report directory
        reports_dir = get_bug_reports_dir()
        os.makedirs(reports_dir, exist_ok=True)

        report_path = os.path.join(reports_dir, f"{report_id}.json")

        # Add metadata to report
        report = {
            'report_id': report_id,
            'trace_id': g.trace_id,
            'submitted_at': datetime.utcnow().isoformat() + 'Z',
            'submitted_by': g.user.email if hasattr(g, 'user') else None,
            'user_role': g.user.role if hasattr(g, 'user') else None,
            'status': 'open',
            **payload
        }

        # Write to disk
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Bug report saved: {report_id}", extra={
            'report_id': report_id,
            'trace_id': g.trace_id,
            'user': g.user.email if hasattr(g, 'user') else None
        })

        return jsonify({
            'success': True,
            'report_id': report_id,
            'trace_id': g.trace_id,
            'stored_at': report_path
        }), 201

    except Exception as e:
        logger.error(f"Failed to save bug report: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to save bug report',
            'error_code': 'BUG_REPORT_SAVE_FAILED',
            'trace_id': g.trace_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 500
```

**Implementation status:** Blueprint registered in `server/api.py`; endpoint requires admin auth.

#### 1.4 Configuration
**File:** `config.yaml`

```yaml
# Bug Report Configuration
bug_reports:
  storage_path: "/mnt/storage/imagineer/bug_reports"
  retention_days: 30  # For future automation
```

**Implementation status:** `config.yaml` entry merged with defaults on Oct 30, 2025.

**File:** `.env.example`
```bash
# Bug Reports (optional override)
BUG_REPORTS_PATH=/mnt/storage/imagineer/bug_reports
```

**Implementation status:** Environment override documented for operators.

---

### Phase 2: Frontend Settings Menu (2-3 hours)

#### 2.1 Settings Menu Component
**File:** `web/src/components/SettingsMenu.tsx` (new)

```tsx
import React, { useState, useRef, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useBugReporter } from '../contexts/BugReportContext'
import '../styles/SettingsMenu.css'

interface SettingsMenuProps {
  onNsfwToggle?: (enabled: boolean) => void
  nsfwEnabled?: boolean
}

const SettingsMenu: React.FC<SettingsMenuProps> = ({
  onNsfwToggle,
  nsfwEnabled = false
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const { user, logout } = useAuth()
  const { openBugReport } = useBugReporter()

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  const handleLogout = () => {
    setIsOpen(false)
    logout()
  }

  const handleBugReport = () => {
    setIsOpen(false)
    openBugReport()
  }

  const handleNsfwToggle = () => {
    if (onNsfwToggle) {
      onNsfwToggle(!nsfwEnabled)
    }
  }

  const isAdmin = user?.role === 'admin'

  return (
    <div className="settings-menu" ref={menuRef}>
      <button
        className="settings-trigger"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Open settings menu"
        aria-expanded={isOpen}
      >
        <svg
          className="settings-icon"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <circle cx="12" cy="12" r="3" />
          <path d="M12 1v6m0 6v6m0-18a2 2 0 0 1 2 2v.5a2 2 0 0 0 1 1.73l.5.29a2 2 0 0 0 2 0l.5-.29a2 2 0 0 1 2.73 1l.84 1.46a2 2 0 0 1-.73 2.73l-.5.29a2 2 0 0 0-1 1.73v.58a2 2 0 0 0 1 1.73l.5.29a2 2 0 0 1 .73 2.73l-.84 1.46a2 2 0 0 1-2.73 1l-.5-.29a2 2 0 0 0-2 0l-.5.29a2 2 0 0 1-2.73-1l-.84-1.46a2 2 0 0 1 .73-2.73l.5-.29a2 2 0 0 0 1-1.73v-.58a2 2 0 0 0-1-1.73l-.5-.29a2 2 0 0 1-.73-2.73l.84-1.46a2 2 0 0 1 2.73-1l.5.29a2 2 0 0 0 2 0l.5-.29a2 2 0 0 0 1-1.73V3a2 2 0 0 1 2-2z" />
        </svg>
      </button>

      {isOpen && (
        <div className="settings-dropdown">
          <div className="settings-header">
            <div className="settings-user-info">
              <div className="settings-user-email">{user?.email}</div>
              <div className="settings-user-role">
                {isAdmin ? '👑 Admin' : '👁️ Viewer'}
              </div>
            </div>
          </div>

          <div className="settings-divider" />

          <div className="settings-options">
            {/* NSFW Filter Toggle */}
            <label className="settings-option settings-toggle">
              <span className="settings-option-label">NSFW Filter</span>
              <input
                type="checkbox"
                checked={nsfwEnabled}
                onChange={handleNsfwToggle}
                className="settings-checkbox"
              />
            </label>

            {/* Bug Report (Admin Only) */}
            {isAdmin && (
              <>
                <div className="settings-divider" />
                <button
                  className="settings-option settings-button"
                  onClick={handleBugReport}
                >
                  <span className="settings-option-label">Report Bug</span>
                  <span className="settings-option-hint">Ctrl+Shift+B</span>
                </button>
              </>
            )}

            {/* Logout */}
            <div className="settings-divider" />
            <button
              className="settings-option settings-button"
              onClick={handleLogout}
            >
              <span className="settings-option-label">Logout</span>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default SettingsMenu
```

**File:** `web/src/styles/SettingsMenu.css` (new)

```css
.settings-menu {
  position: relative;
}

.settings-trigger {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: background-color 0.2s;
}

.settings-trigger:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.settings-icon {
  color: #666;
}

.settings-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  min-width: 260px;
  z-index: 1000;
}

.settings-header {
  padding: 16px;
}

.settings-user-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.settings-user-email {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.settings-user-role {
  font-size: 12px;
  color: #666;
}

.settings-divider {
  height: 1px;
  background-color: #e0e0e0;
  margin: 0;
}

.settings-options {
  padding: 8px 0;
}

.settings-option {
  width: 100%;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
  transition: background-color 0.2s;
}

.settings-option:hover {
  background-color: rgba(0, 0, 0, 0.04);
}

.settings-option-label {
  font-size: 14px;
  color: #333;
}

.settings-option-hint {
  font-size: 12px;
  color: #999;
  font-family: monospace;
}

.settings-checkbox {
  cursor: pointer;
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .settings-dropdown {
    background: #2a2a2a;
    border-color: #444;
  }

  .settings-trigger:hover {
    background-color: rgba(255, 255, 255, 0.1);
  }

  .settings-icon {
    color: #ccc;
  }

  .settings-user-email {
    color: #e0e0e0;
  }

  .settings-user-role {
    color: #999;
  }

  .settings-divider {
    background-color: #444;
  }

  .settings-option-label {
    color: #e0e0e0;
  }

  .settings-option:hover {
    background-color: rgba(255, 255, 255, 0.08);
  }
}
```

#### 2.2 Update App.tsx
**File:** `web/src/App.tsx`

```tsx
// Import SettingsMenu
import SettingsMenu from './components/SettingsMenu'

// Add to header (replace or complement existing BugReportButton)
<header className="app-header">
  {/* ... existing content ... */}
  <SettingsMenu
    onNsfwToggle={(enabled) => {
      // TODO: Connect to NSFW filter or document as not implemented
      console.log('NSFW filter toggled:', enabled)
    }}
    nsfwEnabled={false}
  />
</header>
```

---

### Phase 3: Keyboard Shortcut & Admin Restrictions (1-2 hours)

#### 3.1 Global Keyboard Shortcut Hook
**File:** `web/src/hooks/useKeyboardShortcut.ts` (new)

```typescript
import { useEffect } from 'react'

interface KeyboardShortcutOptions {
  key: string
  ctrlKey?: boolean
  shiftKey?: boolean
  metaKey?: boolean
  enabled?: boolean
  callback: () => void
}

export const useKeyboardShortcut = ({
  key,
  ctrlKey = false,
  shiftKey = false,
  metaKey = false,
  enabled = true,
  callback
}: KeyboardShortcutOptions) => {
  useEffect(() => {
    if (!enabled) return

    const handleKeyDown = (event: KeyboardEvent) => {
      // Ignore if typing in input/textarea
      const target = event.target as HTMLElement
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return
      }

      // Check if all modifiers and key match
      if (
        event.key.toLowerCase() === key.toLowerCase() &&
        event.ctrlKey === ctrlKey &&
        event.shiftKey === shiftKey &&
        event.metaKey === metaKey
      ) {
        event.preventDefault()
        callback()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [key, ctrlKey, shiftKey, metaKey, enabled, callback])
}
```

#### 3.2 Add Shortcut to App
**File:** `web/src/App.tsx`

```tsx
import { useKeyboardShortcut } from './hooks/useKeyboardShortcut'
import { useAuth } from './contexts/AuthContext'

// Inside App component
const { user } = useAuth()
const { openBugReport } = useBugReporter()
const isAdmin = user?.role === 'admin'

// Register Ctrl+Shift+B shortcut (admin only)
useKeyboardShortcut({
  key: 'b',
  ctrlKey: true,
  shiftKey: true,
  enabled: isAdmin,
  callback: () => openBugReport()
})
```

#### 3.3 Hide BugReportButton for Non-Admins
**File:** `web/src/components/BugReportButton.tsx`

```tsx
import React from 'react'
import { useBugReporter } from '../contexts/BugReportContext'
import { useAuth } from '../contexts/AuthContext'

const BugReportButton: React.FC = () => {
  const { openBugReport } = useBugReporter()
  const { user } = useAuth()

  // Only show for admin users
  if (user?.role !== 'admin') {
    return null
  }

  return (
    <button
      type="button"
      className="bug-report-trigger"
      onClick={() => openBugReport()}
      aria-label="Report a bug (Ctrl+Shift+B)"
      title="Report a bug (Ctrl+Shift+B)"
    >
      🐞 Report Bug
    </button>
  )
}

export default BugReportButton
```

---

### Phase 4: ErrorBoundary Integration (1-2 hours)

#### 4.1 Update ErrorBoundary
**File:** `web/src/components/ErrorBoundary.tsx`

```tsx
// Add imports
import { useAuth } from '../contexts/AuthContext'
import { useBugReporter } from '../contexts/BugReportContext'
import { useToast } from '../hooks/useToast'

// Inside ErrorBoundary component - update componentDidCatch
componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
  const { boundaryName, onError } = this.props

  // Log error with context
  logger.error('React Error Boundary caught an error', error, {
    boundaryName: boundaryName || 'Unknown',
    componentStack: errorInfo.componentStack,
  })

  // Update state with error info for display
  this.setState({
    errorInfo,
  })

  // Call optional error callback
  if (onError) {
    onError(error, errorInfo)
  }

  // Show toast with bug report option for admin users
  // This will be handled via the onError callback from App
}

// Add handleReportBug method
handleReportBug = (): void => {
  const { error, errorInfo } = this.state
  const { boundaryName } = this.props

  // This will be called via onError callback with bug reporter context
  // Prefill description with error details
  const description = `Error in ${boundaryName || 'application'}:

${error?.message || 'Unknown error'}

Component Stack:
${errorInfo?.componentStack || 'Not available'}`

  // openBugReport will be passed via callback
}

// Update render to include Report Bug button (admin only)
render(): ReactNode {
  // ... existing code ...

  return (
    <div className="error-boundary">
      <div className="error-boundary-content">
        {/* ... existing error UI ... */}

        <div className="error-actions">
          <button
            className="error-button primary"
            onClick={this.handleReset}
            type="button"
          >
            Try Again
          </button>

          {/* Add Report Bug button - will be shown via wrapper */}

          {/* ... other buttons ... */}
        </div>
      </div>
    </div>
  )
}
```

#### 4.2 ErrorBoundary Wrapper with Bug Report
**File:** `web/src/components/ErrorBoundaryWithReporting.tsx` (new)

```tsx
import React, { useCallback } from 'react'
import ErrorBoundary from './ErrorBoundary'
import { useBugReporter } from '../contexts/BugReportContext'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../hooks/useToast'
import type { ErrorInfo } from 'react'

interface Props {
  children: React.ReactNode
  boundaryName?: string
}

const ErrorBoundaryWithReporting: React.FC<Props> = ({ children, boundaryName }) => {
  const { openBugReport } = useBugReporter()
  const { user } = useAuth()
  const toast = useToast()

  const handleError = useCallback((error: Error, errorInfo: ErrorInfo) => {
    // Only show bug report option to admins
    if (user?.role === 'admin') {
      const description = `Error in ${boundaryName || 'application'}:

${error.message}

Component Stack:
${errorInfo.componentStack}`

      toast.error(
        <>
          <strong>An error occurred</strong>
          <p>{error.message}</p>
          <button
            onClick={() => openBugReport({ description })}
            style={{
              marginTop: '8px',
              padding: '6px 12px',
              background: '#fff',
              color: '#333',
              border: '1px solid #ccc',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Report Bug
          </button>
        </>,
        { duration: 10000 }
      )
    }
  }, [user, boundaryName, openBugReport, toast])

  return (
    <ErrorBoundary boundaryName={boundaryName} onError={handleError}>
      {children}
    </ErrorBoundary>
  )
}

export default ErrorBoundaryWithReporting
```

---

### Phase 5: Documentation (1 hour)

#### 5.1 Bug Report Workflow Documentation
**File:** `docs/guides/BUG_REPORT_WORKFLOW.md` (new)

```markdown
# Bug Report Workflow

## Overview

Admin users can submit detailed bug reports with automatic context capture including application logs, network requests, error stack traces, and environment information.

## How to Submit a Bug Report

### Method 1: Settings Menu
1. Click the gear icon ⚙️ in the top-right corner
2. Select "Report Bug" from the dropdown

### Method 2: Keyboard Shortcut
- Press `Ctrl+Shift+B` (Windows/Linux) or `Cmd+Shift+B` (Mac)
- **Note:** Only available for admin users

### Method 3: From Error Toast
- When an error occurs, admin users will see a toast notification with a "Report Bug" button
- Click the button to open a pre-filled bug report

## What Information is Captured

Bug reports automatically include:

- **User Information:** Email and role (admin/viewer)
- **Error Details:** Error message, stack trace, component stack
- **Recent Logs:** Last 200 application log entries
- **Network Events:** Last 50 API requests with request/response data
- **Application State:** Current tab, selected items, form values
- **Environment:** App version, git SHA, build time
- **Client Metadata:** Browser, OS, screen size, timezone
- **Trace ID:** Unique identifier for correlating frontend/backend errors

## Report Storage

Reports are stored on the server at:
```
/mnt/storage/imagineer/bug_reports/{report_id}.json
```

Each report includes:
- `report_id`: Unique identifier (e.g., `bug_20251029_143022_a1b2c3d4`)
- `trace_id`: Request correlation ID
- `submitted_at`: ISO 8601 timestamp
- `submitted_by`: User email
- `status`: `"open"` or `"resolved"`
- All captured context data

## Reviewing Bug Reports

### Viewing Reports
```bash
cd /mnt/storage/imagineer/bug_reports
ls -lah  # List all reports
cat bug_20251029_143022_a1b2c3d4.json | jq .  # View formatted report
```

### Using AI Agents
```bash
# Copy report to clipboard for AI review
cat bug_20251029_143022_a1b2c3d4.json | xclip -selection clipboard

# Or provide to Claude Code directly
cat bug_20251029_143022_a1b2c3d4.json
```

### Resolving Reports
Once a bug is fixed:

**Option 1: Update Status Field**
```bash
# Edit the JSON file and change "status": "open" to "status": "resolved"
vim bug_20251029_143022_a1b2c3d4.json
```

**Option 2: Move to Resolved Directory**
```bash
mkdir -p /mnt/storage/imagineer/bug_reports/resolved
mv bug_20251029_143022_a1b2c3d4.json resolved/
```

## Retention Policy

- **Current:** Manual cleanup
- **Recommended:** Delete reports older than 30 days
- **Future:** Automated cleanup via cron job

### Manual Cleanup
```bash
# Find reports older than 30 days
find /mnt/storage/imagineer/bug_reports -name "bug_*.json" -mtime +30

# Delete old reports
find /mnt/storage/imagineer/bug_reports -name "bug_*.json" -mtime +30 -delete
```

## Testing Notes

### Development Environment
In development, bug reports are stored at:
```
/home/jdubz/Development/imagineer/bug_reports/
```

### CI/CD Environment
**Important:** The bug reports directory will not exist in CI environments. The backend gracefully handles missing directories and creates them on first use.

Tests should mock the bug report endpoint or use temporary directories.

## NSFW Filter Status

**Status:** Partially implemented, not yet connected to UI toggle.

The NSFW filter toggle in the Settings menu is currently a placeholder. The backend has an `is_nsfw` flag on images, but the frontend filtering is not yet implemented.

**TODO:** Connect the NSFW toggle to filter images in galleries, or document as future enhancement.

See: `web/src/components/SettingsMenu.tsx` line X for toggle implementation.

## Troubleshooting

### Bug Report Submission Fails
1. Check server logs for trace ID
2. Verify `/mnt/storage/imagineer/bug_reports/` is writable
3. Ensure user has admin role

### Keyboard Shortcut Not Working
- Only works for admin users
- Check that you're not focused on an input field
- Verify shortcut is `Ctrl+Shift+B` (Windows/Linux) or `Cmd+Shift+B` (Mac)

### Reports Not Appearing
```bash
# Check directory exists
ls -la /mnt/storage/imagineer/bug_reports/

# Check permissions
ls -ld /mnt/storage/imagineer/bug_reports/

# View server logs
tail -f logs/server.log | grep -i "bug report"
```
```

#### 5.2 Update BUG_REPORT_TOOL_PLAN.md
**File:** `docs/plans/BUG_REPORT_TOOL_PLAN.md`

Update the "Gaps / Work Remaining" section to reflect new implementation plan and mark completed items.

---

## Implementation Checklist

### Backend
- [ ] Create `server/middleware/trace_id.py`
- [ ] Create `server/utils/error_handler.py`
- [ ] Create `server/routes/bug_reports.py`
- [ ] Register trace ID middleware in `server/api.py`
- [ ] Update all error handlers to use structured format
- [ ] Register bug_reports blueprint in `server/api.py`
- [ ] Add bug_reports config to `config.yaml`
- [ ] Add BUG_REPORTS_PATH to `.env.example`
- [ ] Test /api/bug-reports endpoint
- [ ] Verify trace IDs in response headers

### Frontend - Settings Menu
- [ ] Create `web/src/components/SettingsMenu.tsx`
- [ ] Create `web/src/styles/SettingsMenu.css`
- [ ] Update `web/src/App.tsx` to include SettingsMenu
- [ ] Test settings menu dropdown
- [ ] Verify user role display
- [ ] Document NSFW filter status

### Frontend - Keyboard & Admin
- [ ] Create `web/src/hooks/useKeyboardShortcut.ts`
- [ ] Add keyboard shortcut to `App.tsx`
- [ ] Update `BugReportButton.tsx` to hide for non-admins
- [ ] Test Ctrl+Shift+B shortcut (admin only)
- [ ] Test button hidden for viewer role

### Frontend - Error Integration
- [ ] Create `web/src/components/ErrorBoundaryWithReporting.tsx`
- [ ] Update ErrorBoundary with report button support
- [ ] Add error toast with bug report button
- [ ] Test error boundary captures errors
- [ ] Test toast shows for admin users
- [ ] Verify pre-filled description includes error details

### Documentation
- [ ] Create `docs/guides/BUG_REPORT_WORKFLOW.md`
- [ ] Update `docs/plans/BUG_REPORT_TOOL_PLAN.md`
- [ ] Add CI testing notes about directory
- [ ] Document NSFW filter status
- [ ] Update ARCHITECTURE.md with bug reporting flow

### Testing
- [ ] Test bug report submission end-to-end
- [ ] Test admin-only restrictions
- [ ] Test keyboard shortcut
- [ ] Test error boundary integration
- [ ] Test trace ID propagation
- [ ] Verify reports saved to disk
- [ ] Test manual resolution workflow
- [ ] Verify graceful handling of missing directory

---

## Future Enhancements (V2)

### Screenshot Capture
- Add screenshot capture with `html2canvas`
- Exclude bug report modal from screenshot
- Store as separate PNG file: `{report_id}/screenshot.png`
- Add screenshot path to JSON report

### Feature Requests with Annotations
- Separate modal for feature requests
- Screenshot annotation with arrows/text/highlights
- Use `react-sketch-canvas` or `fabric.js`
- Save annotations as separate layer

### Advanced Features
- Browser console log capture (intercept console.*)
- Performance metrics (memory, load times)
- Network timing waterfall
- Redux DevTools state snapshots
- Automated cleanup cron job
- Admin UI for browsing reports
- Report search and filtering

---

## Questions & Decisions

### Resolved
- ✅ Storage location: `/mnt/storage/imagineer/bug_reports/`
- ✅ Admin-only submission
- ✅ Keyboard shortcut: `Ctrl+Shift+B`
- ✅ Retention: 30 days manual cleanup
- ✅ Resolved tracking: Status field + optional resolved/ directory
- ✅ Screenshot: Deferred to V2
- ✅ Base64 vs separate file: Separate PNG for V2

### Open
- NSFW filter implementation status (needs investigation)
- Automated cleanup implementation timeline

---

**Document Version:** 1.0
**Last Updated:** 2025-10-29
**Next Review:** After Phase 1 completion
