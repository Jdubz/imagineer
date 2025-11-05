# Bug Report DB Migration - Detailed Implementation Plan

**Goal:** Migrate bug report system from flat-file JSON storage to SQLAlchemy database-backed storage while preserving ALL existing features.

**Critical Requirement:** Zero feature loss during migration. All existing functionality must be preserved.

---

## Feature Preservation Checklist

### Must-Preserve Features
- ✅ Screenshot upload and storage (`/api/bug-reports/{id}/screenshot`)
- ✅ Trace ID middleware (`server/middleware/trace_middleware.py`)
- ✅ Agent manager Docker integration (`src/bug_reports/agent_manager.py`)
- ✅ Bootstrap script (`scripts/bug_reports/agent_bootstrap.sh`)
- ✅ Admin-only access control
- ✅ Network request capture
- ✅ Component tree capture
- ✅ In-process queue.Queue worker pattern
- ✅ Claude CLI remediation workflow
- ✅ Git branch creation and push
- ✅ Test suite execution (npm + pytest)
- ✅ Session logging and artifacts

---

## Phase 1: Database Schema (M1) - Target: Nov 10

### Step 1.1: Create Database Models
**File:** `server/database.py`

```python
class BugReport(db.Model):
    __tablename__ = 'bug_reports'

    # Primary identification
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(64), unique=True, nullable=False, index=True)  # bug_20251104_000814_54edd4f7
    trace_id = db.Column(db.String(64), nullable=True, index=True)

    # Lifecycle
    status = db.Column(db.String(32), nullable=False, default='new', index=True)
    # Statuses: new, triaged, in_progress, awaiting_verification, resolved, closed
    priority = db.Column(db.String(16), nullable=True)  # critical, high, medium, low

    # Content (preserve existing fields)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    stack_trace = db.Column(db.Text, nullable=True)

    # Context (preserve existing fields)
    user_actions = db.Column(db.Text, nullable=True)  # JSON string
    component_hierarchy = db.Column(db.Text, nullable=True)  # JSON string
    network_logs = db.Column(db.Text, nullable=True)  # JSON string

    # Browser info (preserve existing fields)
    browser_info = db.Column(db.Text, nullable=True)  # JSON string
    viewport = db.Column(db.String(32), nullable=True)  # "1920x1080"
    url = db.Column(db.String(512), nullable=True)

    # Telemetry (new fields)
    request_id = db.Column(db.String(64), nullable=True, index=True)
    release_hash = db.Column(db.String(64), nullable=True, index=True)

    # Screenshot (CRITICAL: preserve existing feature)
    screenshot_path = db.Column(db.String(512), nullable=True)

    # Remediation tracking (new fields)
    fix_commit_sha = db.Column(db.String(64), nullable=True)
    fix_branch = db.Column(db.String(128), nullable=True)
    verification_status = db.Column(db.String(32), nullable=True)  # pending, passed, failed
    agent_session_log = db.Column(db.Text, nullable=True)

    # Deduplication (new fields)
    content_hash = db.Column(db.String(64), nullable=True, index=True)
    dedup_group_id = db.Column(db.Integer, db.ForeignKey('bug_report_dedup.id'), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    triaged_at = db.Column(db.DateTime, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    events = db.relationship('BugReportEvent', back_populates='bug_report', cascade='all, delete-orphan')
    dedup_group = db.relationship('BugReportDedup', back_populates='reports')

    def to_dict(self):
        """Convert to dict for API responses - preserve existing format"""
        return {
            'report_id': self.report_id,
            'trace_id': self.trace_id,
            'status': self.status,
            'priority': self.priority,
            'title': self.title,
            'description': self.description,
            'error_message': self.error_message,
            'stack_trace': self.stack_trace,
            'user_actions': json.loads(self.user_actions) if self.user_actions else None,
            'component_hierarchy': json.loads(self.component_hierarchy) if self.component_hierarchy else None,
            'network_logs': json.loads(self.network_logs) if self.network_logs else None,
            'browser_info': json.loads(self.browser_info) if self.browser_info else None,
            'viewport': self.viewport,
            'url': self.url,
            'screenshot_path': self.screenshot_path,
            'fix_commit_sha': self.fix_commit_sha,
            'fix_branch': self.fix_branch,
            'verification_status': self.verification_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
        }


class BugReportEvent(db.Model):
    __tablename__ = 'bug_report_events'

    id = db.Column(db.Integer, primary_key=True)
    bug_report_id = db.Column(db.Integer, db.ForeignKey('bug_reports.id'), nullable=False, index=True)
    event_type = db.Column(db.String(32), nullable=False)  # status_change, comment, remediation_attempt
    old_value = db.Column(db.String(128), nullable=True)
    new_value = db.Column(db.String(128), nullable=True)
    details = db.Column(db.Text, nullable=True)  # JSON string for additional context
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    bug_report = db.relationship('BugReport', back_populates='events')


class BugReportDedup(db.Model):
    __tablename__ = 'bug_report_dedup'

    id = db.Column(db.Integer, primary_key=True)
    content_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    first_seen_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    occurrence_count = db.Column(db.Integer, nullable=False, default=1)

    reports = db.relationship('BugReport', back_populates='dedup_group')
```

**Testing:**
- [ ] Create migration: `flask db migrate -m "Add bug report tables"`
- [ ] Apply migration: `flask db upgrade`
- [ ] Verify tables created: `sqlite3 imagineer.db ".tables"`
- [ ] Test model creation: Create test bug report in Python shell

### Step 1.2: Create Data Migration Script
**File:** `scripts/migrate_bug_reports_to_db.py`

```python
#!/usr/bin/env python3
"""
Migrate existing flat-file JSON bug reports to database.

Usage:
    python scripts/migrate_bug_reports_to_db.py [--dry-run]
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from server.database import db, BugReport
from server.api import create_app


def parse_report_id(filename):
    """Extract report_id from filename: bug_20251104_000814_54edd4f7.json"""
    return filename.replace('.json', '')


def migrate_bug_report(json_path, dry_run=False):
    """Migrate a single bug report from JSON to database"""
    with open(json_path, 'r') as f:
        data = json.load(f)

    report_id = parse_report_id(os.path.basename(json_path))

    # Map old format to new database fields
    bug_report = BugReport(
        report_id=report_id,
        trace_id=data.get('trace_id'),
        status='resolved' if data.get('status') == 'resolved' else 'new',  # Migrate old statuses
        title=data.get('title', 'Untitled'),
        description=data.get('description'),
        error_message=data.get('error', {}).get('message') if isinstance(data.get('error'), dict) else data.get('error'),
        stack_trace=data.get('error', {}).get('stack') if isinstance(data.get('error'), dict) else None,
        user_actions=json.dumps(data.get('userActions', [])),
        component_hierarchy=json.dumps(data.get('componentHierarchy', [])),
        network_logs=json.dumps(data.get('networkLogs', [])),
        browser_info=json.dumps(data.get('browserInfo', {})),
        viewport=data.get('viewport'),
        url=data.get('url'),
        screenshot_path=data.get('screenshot_path'),  # Preserve screenshot path
        created_at=datetime.fromisoformat(data['timestamp']) if 'timestamp' in data else datetime.utcnow(),
    )

    if dry_run:
        print(f"[DRY RUN] Would migrate: {report_id}")
        return None
    else:
        db.session.add(bug_report)
        print(f"Migrated: {report_id}")
        return bug_report


def main():
    parser = argparse.ArgumentParser(description='Migrate bug reports from JSON to database')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated without making changes')
    parser.add_argument('--bug-reports-dir', default='/mnt/storage/imagineer/bug_reports', help='Path to bug reports directory')
    args = parser.parse_args()

    app = create_app()

    with app.app_context():
        bug_reports_dir = Path(args.bug_reports_dir)
        json_files = list(bug_reports_dir.glob('bug_*.json'))

        print(f"Found {len(json_files)} bug reports to migrate")

        migrated_count = 0
        for json_path in sorted(json_files):
            try:
                migrate_bug_report(json_path, dry_run=args.dry_run)
                migrated_count += 1
            except Exception as e:
                print(f"ERROR migrating {json_path}: {e}")

        if not args.dry_run:
            db.session.commit()
            print(f"\n✅ Successfully migrated {migrated_count} bug reports")
        else:
            print(f"\n[DRY RUN] Would migrate {migrated_count} bug reports")


if __name__ == '__main__':
    main()
```

**Testing:**
- [ ] Run dry-run: `python scripts/migrate_bug_reports_to_db.py --dry-run`
- [ ] Run actual migration: `python scripts/migrate_bug_reports_to_db.py`
- [ ] Verify count: `sqlite3 imagineer.db "SELECT COUNT(*) FROM bug_reports;"`
- [ ] Spot-check: Compare database record to original JSON file

---

## Phase 2: Service Layer (M2) - Target: Nov 14

### Step 2.1: Create Bug Report Service
**File:** `src/bug_reports/bug_report_service.py`

```python
"""
Bug report service layer - handles all bug report business logic.
Replaces flat-file JSON storage with database operations.
"""

from datetime import datetime
import hashlib
import json

from server.database import db, BugReport, BugReportEvent, BugReportDedup


class BugReportService:
    """Service for managing bug reports"""

    @staticmethod
    def generate_report_id():
        """Generate unique report ID: bug_YYYYMMDD_HHMMSS_<hash>"""
        timestamp = datetime.utcnow()
        date_str = timestamp.strftime('%Y%m%d_%H%M%S')
        random_hash = hashlib.sha256(timestamp.isoformat().encode()).hexdigest()[:8]
        return f"bug_{date_str}_{random_hash}"

    @staticmethod
    def compute_content_hash(error_message, stack_trace, url):
        """Compute hash for deduplication"""
        content = f"{error_message}|{stack_trace}|{url}"
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def create_bug_report(data):
        """
        Create a new bug report from frontend submission.
        Preserves existing API contract.

        Args:
            data: Dict with keys: title, description, error, userActions,
                  componentHierarchy, networkLogs, browserInfo, viewport, url, trace_id

        Returns:
            BugReport: Created bug report instance
        """
        report_id = BugReportService.generate_report_id()

        # Extract error message and stack trace
        error = data.get('error', {})
        error_message = error.get('message') if isinstance(error, dict) else str(error)
        stack_trace = error.get('stack') if isinstance(error, dict) else None

        # Compute content hash for deduplication
        content_hash = BugReportService.compute_content_hash(
            error_message or '',
            stack_trace or '',
            data.get('url', '')
        )

        # Check for existing dedup group
        dedup_group = BugReportDedup.query.filter_by(content_hash=content_hash).first()
        if not dedup_group:
            dedup_group = BugReportDedup(content_hash=content_hash)
            db.session.add(dedup_group)
            db.session.flush()  # Get dedup_group.id
        else:
            dedup_group.occurrence_count += 1
            dedup_group.last_seen_at = datetime.utcnow()

        # Create bug report
        bug_report = BugReport(
            report_id=report_id,
            trace_id=data.get('trace_id'),
            status='new',
            title=data.get('title', 'Untitled Bug Report'),
            description=data.get('description'),
            error_message=error_message,
            stack_trace=stack_trace,
            user_actions=json.dumps(data.get('userActions', [])),
            component_hierarchy=json.dumps(data.get('componentHierarchy', [])),
            network_logs=json.dumps(data.get('networkLogs', [])),
            browser_info=json.dumps(data.get('browserInfo', {})),
            viewport=data.get('viewport'),
            url=data.get('url'),
            content_hash=content_hash,
            dedup_group_id=dedup_group.id,
        )

        db.session.add(bug_report)

        # Create initial event
        event = BugReportEvent(
            bug_report=bug_report,
            event_type='status_change',
            new_value='new',
            details=json.dumps({'source': 'frontend_submission'})
        )
        db.session.add(event)

        db.session.commit()
        return bug_report

    @staticmethod
    def update_screenshot_path(report_id, screenshot_path):
        """Update screenshot path after upload. CRITICAL: preserve existing feature."""
        bug_report = BugReport.query.filter_by(report_id=report_id).first()
        if not bug_report:
            raise ValueError(f"Bug report {report_id} not found")

        bug_report.screenshot_path = screenshot_path
        db.session.commit()
        return bug_report

    @staticmethod
    def update_status(report_id, new_status, details=None):
        """Update bug report status and create audit event"""
        bug_report = BugReport.query.filter_by(report_id=report_id).first()
        if not bug_report:
            raise ValueError(f"Bug report {report_id} not found")

        old_status = bug_report.status
        bug_report.status = new_status

        # Update timestamp fields based on status
        if new_status == 'triaged':
            bug_report.triaged_at = datetime.utcnow()
        elif new_status == 'in_progress':
            bug_report.started_at = datetime.utcnow()
        elif new_status == 'resolved':
            bug_report.resolved_at = datetime.utcnow()
        elif new_status == 'closed':
            bug_report.closed_at = datetime.utcnow()

        # Create audit event
        event = BugReportEvent(
            bug_report=bug_report,
            event_type='status_change',
            old_value=old_status,
            new_value=new_status,
            details=json.dumps(details) if details else None
        )
        db.session.add(event)

        db.session.commit()
        return bug_report

    @staticmethod
    def update_remediation_result(report_id, fix_commit_sha, fix_branch, verification_status, agent_log=None):
        """Update bug report with remediation results from agent"""
        bug_report = BugReport.query.filter_by(report_id=report_id).first()
        if not bug_report:
            raise ValueError(f"Bug report {report_id} not found")

        bug_report.fix_commit_sha = fix_commit_sha
        bug_report.fix_branch = fix_branch
        bug_report.verification_status = verification_status
        if agent_log:
            bug_report.agent_session_log = agent_log

        # Create remediation event
        event = BugReportEvent(
            bug_report=bug_report,
            event_type='remediation_attempt',
            new_value=verification_status,
            details=json.dumps({
                'commit': fix_commit_sha,
                'branch': fix_branch
            })
        )
        db.session.add(event)

        db.session.commit()
        return bug_report

    @staticmethod
    def get_bug_report(report_id):
        """Get bug report by ID"""
        return BugReport.query.filter_by(report_id=report_id).first()

    @staticmethod
    def list_bug_reports(status=None, limit=50):
        """List bug reports, optionally filtered by status"""
        query = BugReport.query.order_by(BugReport.created_at.desc())
        if status:
            query = query.filter_by(status=status)
        return query.limit(limit).all()
```

**Testing:**
- [ ] Unit tests for each method in `tests/test_bug_report_service.py`
- [ ] Test deduplication logic with duplicate reports
- [ ] Test status transitions and timestamp updates
- [ ] Test screenshot path updates

### Step 2.2: Update Bug Report Agent Manager
**File:** `src/bug_reports/agent_manager.py`

**Changes:**
1. Replace flat-file JSON reads with `BugReportService.get_bug_report()`
2. Update status to `in_progress` when starting remediation
3. Call `BugReportService.update_remediation_result()` after agent completes
4. Preserve all existing Docker integration and bootstrap script logic

**Example update:**
```python
def start_remediation(self, report_id):
    """Start remediation for a bug report"""
    # Update status to in_progress
    BugReportService.update_status(report_id, 'in_progress')

    # Get bug report details from database (instead of JSON file)
    bug_report = BugReportService.get_bug_report(report_id)
    if not bug_report:
        raise ValueError(f"Bug report {report_id} not found")

    # ... rest of existing Docker logic ...

    # After agent completes, update remediation results
    BugReportService.update_remediation_result(
        report_id=report_id,
        fix_commit_sha=session_summary.get('commit'),
        fix_branch=f"bugfix/{report_id}",
        verification_status='passed' if session_summary['status'] == 'success' else 'failed',
        agent_log=session_log_content
    )
```

**Testing:**
- [ ] Run agent manager against existing bug report
- [ ] Verify status updates in database
- [ ] Verify remediation results saved correctly

---

## Phase 3: API Updates (M4) - Target: Nov 21

### Step 3.1: Update Bug Report Submission Endpoint
**File:** `server/api.py`

**Changes:**
1. Replace flat-file JSON writes with `BugReportService.create_bug_report()`
2. Preserve existing API contract (request/response format)
3. Add new fields to response: status, priority, dedup info

**Before:**
```python
@app.route('/api/bug-reports', methods=['POST'])
@admin_required
def submit_bug_report():
    data = request.get_json()
    report_id = generate_report_id()

    # Save to JSON file
    report_path = os.path.join(BUG_REPORTS_DIR, f"{report_id}.json")
    with open(report_path, 'w') as f:
        json.dump(data, f, indent=2)

    return jsonify({
        'success': True,
        'report_id': report_id,
        'trace_id': data.get('trace_id'),
        'stored_at': report_path
    })
```

**After:**
```python
@app.route('/api/bug-reports', methods=['POST'])
@admin_required
def submit_bug_report():
    data = request.get_json()

    # Create bug report in database
    bug_report = BugReportService.create_bug_report(data)

    # Preserve existing response format
    return jsonify({
        'success': True,
        'report_id': bug_report.report_id,
        'trace_id': bug_report.trace_id,
        'stored_at': None  # Deprecated but preserve for compatibility
    })
```

**Testing:**
- [ ] Submit bug report via frontend
- [ ] Verify database record created
- [ ] Verify response format unchanged
- [ ] Verify admin-only access still enforced

### Step 3.2: Update Screenshot Upload Endpoint
**File:** `server/api.py`

**Changes:**
1. Replace flat-file lookup with `BugReportService.get_bug_report()`
2. Call `BugReportService.update_screenshot_path()` after upload
3. Preserve existing file storage logic

**Before:**
```python
@app.route('/api/bug-reports/<report_id>/screenshot', methods=['POST'])
@admin_required
def upload_screenshot(report_id):
    file = request.files.get('screenshot')
    if not file:
        return jsonify({'error': 'No screenshot provided'}), 400

    screenshot_path = os.path.join(BUG_REPORTS_DIR, 'screenshots', f"{report_id}.png")
    file.save(screenshot_path)

    # Update JSON file with screenshot path
    report_path = os.path.join(BUG_REPORTS_DIR, f"{report_id}.json")
    with open(report_path, 'r+') as f:
        data = json.load(f)
        data['screenshot_path'] = screenshot_path
        f.seek(0)
        json.dump(data, f, indent=2)

    return jsonify({'success': True})
```

**After:**
```python
@app.route('/api/bug-reports/<report_id>/screenshot', methods=['POST'])
@admin_required
def upload_screenshot(report_id):
    file = request.files.get('screenshot')
    if not file:
        return jsonify({'error': 'No screenshot provided'}), 400

    # Check bug report exists
    bug_report = BugReportService.get_bug_report(report_id)
    if not bug_report:
        return jsonify({'error': 'Bug report not found'}), 404

    # Save screenshot (preserve existing file storage)
    screenshot_path = os.path.join(BUG_REPORTS_DIR, 'screenshots', f"{report_id}.png")
    file.save(screenshot_path)

    # Update database with screenshot path
    BugReportService.update_screenshot_path(report_id, screenshot_path)

    return jsonify({'success': True})
```

**Testing:**
- [ ] Upload screenshot via frontend
- [ ] Verify file saved to disk
- [ ] Verify screenshot_path updated in database
- [ ] Verify error handling for invalid report_id

### Step 3.3: Add New Bug Report Management Endpoints
**File:** `server/api.py`

```python
@app.route('/api/bug-reports', methods=['GET'])
@admin_required
def list_bug_reports():
    """List all bug reports with optional status filter"""
    status = request.args.get('status')
    limit = int(request.args.get('limit', 50))

    bug_reports = BugReportService.list_bug_reports(status=status, limit=limit)

    return jsonify({
        'bug_reports': [br.to_dict() for br in bug_reports],
        'total': len(bug_reports)
    })


@app.route('/api/bug-reports/<report_id>', methods=['GET'])
@admin_required
def get_bug_report(report_id):
    """Get a single bug report with full details"""
    bug_report = BugReportService.get_bug_report(report_id)
    if not bug_report:
        return jsonify({'error': 'Bug report not found'}), 404

    # Include events in response
    events = [
        {
            'event_type': e.event_type,
            'old_value': e.old_value,
            'new_value': e.new_value,
            'details': json.loads(e.details) if e.details else None,
            'created_at': e.created_at.isoformat()
        }
        for e in bug_report.events
    ]

    response = bug_report.to_dict()
    response['events'] = events

    return jsonify(response)


@app.route('/api/bug-reports/<report_id>/status', methods=['PUT'])
@admin_required
def update_bug_report_status(report_id):
    """Update bug report status (manual triage)"""
    data = request.get_json()
    new_status = data.get('status')

    if new_status not in ['new', 'triaged', 'in_progress', 'awaiting_verification', 'resolved', 'closed']:
        return jsonify({'error': 'Invalid status'}), 400

    bug_report = BugReportService.update_status(
        report_id,
        new_status,
        details={'updated_by': 'manual'}
    )

    return jsonify(bug_report.to_dict())
```

**Testing:**
- [ ] List bug reports: `GET /api/bug-reports`
- [ ] Filter by status: `GET /api/bug-reports?status=new`
- [ ] Get single report: `GET /api/bug-reports/{id}`
- [ ] Update status: `PUT /api/bug-reports/{id}/status`

---

## Phase 4: Queue Integration (M2) - Target: Nov 14

### Step 4.1: Update Bug Report Queue Worker
**File:** `src/bug_reports/queue_worker.py` (new file)

```python
"""
Bug report queue worker - processes remediation jobs in background.
Reuses in-process queue.Queue pattern from image generation.
"""

import queue
import threading
import logging

from src.bug_reports.agent_manager import BugReportAgentManager
from src.bug_reports.bug_report_service import BugReportService

logger = logging.getLogger(__name__)


class BugReportQueueWorker:
    """Background worker for processing bug report remediation"""

    def __init__(self):
        self.queue = queue.Queue()
        self.agent_manager = BugReportAgentManager()
        self.worker_thread = None
        self.running = False

    def start(self):
        """Start the background worker thread"""
        if self.worker_thread and self.worker_thread.is_alive():
            logger.warning("Queue worker already running")
            return

        self.running = True
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
        logger.info("Bug report queue worker started")

    def stop(self):
        """Stop the background worker thread"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("Bug report queue worker stopped")

    def enqueue_remediation(self, report_id):
        """Add a bug report to the remediation queue"""
        self.queue.put(report_id)
        logger.info(f"Enqueued bug report {report_id} for remediation")

    def _process_queue(self):
        """Main worker loop - processes remediation jobs"""
        while self.running:
            try:
                # Wait for next job (1 second timeout to check running flag)
                report_id = self.queue.get(timeout=1)

                logger.info(f"Processing remediation for {report_id}")

                try:
                    # Run remediation agent
                    self.agent_manager.start_remediation(report_id)
                    logger.info(f"Remediation completed for {report_id}")
                except Exception as e:
                    logger.error(f"Remediation failed for {report_id}: {e}")
                    BugReportService.update_status(
                        report_id,
                        'new',  # Reset to new on failure
                        details={'error': str(e), 'source': 'queue_worker'}
                    )
                finally:
                    self.queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Queue worker error: {e}")


# Global queue worker instance
bug_report_queue_worker = BugReportQueueWorker()
```

**Integration in `server/api.py`:**
```python
from src.bug_reports.queue_worker import bug_report_queue_worker

# Start worker on app startup
@app.before_first_request
def start_bug_report_worker():
    bug_report_queue_worker.start()

# Enqueue remediation after bug report submission
@app.route('/api/bug-reports', methods=['POST'])
@admin_required
def submit_bug_report():
    data = request.get_json()
    bug_report = BugReportService.create_bug_report(data)

    # Auto-enqueue for remediation (optional: make this configurable)
    if data.get('auto_remediate', False):
        bug_report_queue_worker.enqueue_remediation(bug_report.report_id)

    return jsonify({
        'success': True,
        'report_id': bug_report.report_id,
        'trace_id': bug_report.trace_id,
    })
```

**Testing:**
- [ ] Submit bug report with auto_remediate=true
- [ ] Verify worker picks up job from queue
- [ ] Verify agent runs and updates database
- [ ] Test worker graceful shutdown

---

## Phase 5: Frontend Updates (M4) - Target: Nov 21

### Step 5.1: Preserve Existing Frontend Features
**Files:** No changes required to:
- `web/src/contexts/BugReportProvider.tsx` - Submission logic unchanged
- `web/src/hooks/useBugReport.ts` - API contract preserved
- Ctrl+Shift+B keyboard shortcut - Unchanged
- Screenshot capture - Unchanged
- Network interception - Unchanged

### Step 5.2: Add Bug Report Management UI (Optional Enhancement)
**File:** `web/src/pages/BugReportsPage.tsx` (new page)

```typescript
// Admin-only page for viewing and managing bug reports
export function BugReportsPage() {
  const [bugReports, setBugReports] = useState([])
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    fetch(`/api/bug-reports?status=${filter}`)
      .then(res => res.json())
      .then(data => setBugReports(data.bug_reports))
  }, [filter])

  return (
    <div>
      <h1>Bug Reports</h1>
      <select value={filter} onChange={(e) => setFilter(e.target.value)}>
        <option value="all">All</option>
        <option value="new">New</option>
        <option value="in_progress">In Progress</option>
        <option value="resolved">Resolved</option>
      </select>

      <table>
        <thead>
          <tr>
            <th>Report ID</th>
            <th>Status</th>
            <th>Title</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {bugReports.map(report => (
            <tr key={report.report_id}>
              <td>{report.report_id}</td>
              <td>{report.status}</td>
              <td>{report.title}</td>
              <td>{new Date(report.created_at).toLocaleString()}</td>
              <td>
                <button onClick={() => viewDetails(report.report_id)}>View</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

**Testing:**
- [ ] View bug reports list
- [ ] Filter by status
- [ ] Click to view details
- [ ] Verify admin-only access

---

## Phase 6: Testing & Rollout (M6) - Target: Nov 26

### Step 6.1: Comprehensive Testing

**Backend Tests:**
- [ ] All BugReportService methods
- [ ] Database migrations
- [ ] API endpoints (preserve existing contract)
- [ ] Queue worker
- [ ] Agent manager integration

**Frontend Tests:**
- [ ] Bug report submission (existing flow)
- [ ] Screenshot upload (existing flow)
- [ ] Keyboard shortcut (existing feature)
- [ ] Admin-only access (existing security)

**Integration Tests:**
- [ ] End-to-end: Submit → Queue → Agent → Remediation → Database
- [ ] Screenshot upload → Database update
- [ ] Deduplication with identical reports
- [ ] Status transitions

**Backwards Compatibility Tests:**
- [ ] Old JSON files still readable via migration script
- [ ] API responses match old format
- [ ] Frontend still works without changes

### Step 6.2: Rollout Plan

**Pre-rollout:**
1. [ ] Run migration script on production data (dry-run first)
2. [ ] Backup `/mnt/storage/imagineer/bug_reports/` directory
3. [ ] Verify all tests pass
4. [ ] Review database schema

**Rollout:**
1. [ ] Deploy database migration
2. [ ] Run migration script: `python scripts/migrate_bug_reports_to_db.py`
3. [ ] Deploy updated API code
4. [ ] Restart API: `sudo systemctl restart imagineer-api`
5. [ ] Verify existing bug reports visible in database
6. [ ] Submit test bug report via frontend
7. [ ] Verify remediation agent works with database

**Post-rollout:**
1. [ ] Monitor logs for errors
2. [ ] Verify new bug reports created in database
3. [ ] Keep JSON files as backup for 30 days
4. [ ] Update documentation

**Rollback Plan:**
- If issues occur, revert API code and continue using JSON files
- Database migration is additive (doesn't delete JSON files)
- Can re-run migration script if needed

---

## Critical Preservation Checklist

**Before ANY code changes, verify these features still work:**

- [ ] Admin can submit bug report via Ctrl+Shift+B
- [ ] Screenshot automatically captured and uploaded
- [ ] Network logs captured
- [ ] Component hierarchy captured
- [ ] Trace ID middleware still running
- [ ] Agent manager can run Docker containers
- [ ] Bootstrap script executes successfully
- [ ] Git integration (branch, commit, push) works
- [ ] Test suite execution (npm + pytest) works
- [ ] Session logs and artifacts saved

**After EACH phase, verify:**
- [ ] All existing tests still pass
- [ ] No regressions in existing features
- [ ] New tests for new functionality passing
- [ ] Documentation updated

---

## Summary

**Total Phases:** 6
**Target Completion:** Nov 26
**Critical Success Factor:** Zero feature loss

**Key Principles:**
1. Preserve ALL existing features
2. Maintain backwards compatibility
3. Additive changes only (don't delete JSON files until proven stable)
4. Test each phase independently
5. Document all changes

**High-Risk Areas:**
- Screenshot upload/storage (ensure path preserved)
- Agent manager Docker integration (don't break existing flow)
- Admin-only access control (preserve security)
- Queue worker pattern (reuse existing image generation pattern)

**Low-Risk Areas:**
- Database schema (new tables, no modifications to existing)
- Service layer (new code, doesn't affect existing)
- API additions (new endpoints, existing endpoints minimally modified)
