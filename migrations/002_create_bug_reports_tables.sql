BEGIN;

CREATE TABLE IF NOT EXISTS bug_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT NOT NULL UNIQUE,
    trace_id TEXT,
    submitted_by TEXT,
    submitted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT NOT NULL,
    expected_behavior TEXT,
    actual_behavior TEXT,
    steps_to_reproduce TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    automation_attempts INTEGER NOT NULL DEFAULT 0,
    environment TEXT,
    client_meta TEXT,
    app_state TEXT,
    recent_logs TEXT,
    network_events TEXT,
    screenshot_path TEXT,
    screenshot_error TEXT,
    resolution_notes TEXT,
    resolution_commit_sha TEXT,
    resolution_actor_id TEXT,
    events TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_bug_reports_report_id ON bug_reports(report_id);
CREATE INDEX IF NOT EXISTS ix_bug_reports_trace_id ON bug_reports(trace_id);
CREATE INDEX IF NOT EXISTS ix_bug_reports_status ON bug_reports(status);
CREATE INDEX IF NOT EXISTS ix_bug_reports_submitted_at ON bug_reports(submitted_at);

-- Ensure migration history table exists for idempotent script tracking.
CREATE TABLE IF NOT EXISTS migration_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_run_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    details TEXT
);

COMMIT;
