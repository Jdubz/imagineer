#!/usr/bin/env python3
"""
Migrate bug reports from JSON files to database.

This script reads bug report JSON files from the storage directory and
inserts them into the bug_reports table with all enhanced quality fields.
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Attempt to import app modules; fall back to adding project root dynamically.
try:
    from flask import Flask

    from server.database import BugReport, BugReportEvent, db
except ImportError:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from flask import Flask

    from server.database import BugReport, BugReportEvent, db

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def create_app():
    """Create Flask app for migration"""
    app = Flask(__name__)
    # Use absolute path to database
    db_path = Path(__file__).parent.parent / "instance" / "imagineer.db"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    return app


def parse_timestamp(ts_str):
    """Parse ISO timestamp string to datetime object."""
    if not ts_str:
        return None
    try:
        # Handle various ISO formats
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        return datetime.fromisoformat(ts_str)
    except (ValueError, AttributeError):
        return None


def migrate_report(json_path: Path, dry_run: bool = False):
    """Migrate a single bug report from JSON to database."""
    logger.info(f"Processing: {json_path.name}")

    try:
        with open(json_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read {json_path}: {e}")
        return False

    report_id = data.get("report_id")
    if not report_id:
        logger.warning(f"Skipping {json_path.name}: no report_id")
        return False

    # Check if already migrated
    existing = BugReport.query.filter_by(report_id=report_id).first()
    if existing:
        logger.info(f"  Already migrated: {report_id}")
        return True

    # Extract fields with fallbacks
    description = data.get("description", "")
    if not description:
        logger.warning(f"Skipping {report_id}: no description")
        return False

    # Build metadata
    environment = data.get("environment", {})
    client_meta = data.get("clientMeta", {})
    app_state = data.get("appState", {})

    # Parse build metadata from environment
    app_version = environment.get("appVersion")
    git_sha = environment.get("gitSha")
    build_time_str = environment.get("buildTime")
    build_time = parse_timestamp(build_time_str) if build_time_str else None

    # Extract route for categorization
    route = client_meta.get("locationHref", "")

    # Determine category heuristically
    category = "unknown"
    if "image" in route.lower():
        category = "ui_images"
    elif "album" in route.lower():
        category = "ui_albums"
    elif "/api/" in route:
        category = "api"

    # Create bug report
    bug_report = BugReport(
        report_id=report_id,
        title=description[:500] if description else None,  # Use first 500 chars as title
        description=description,
        # Quality fields (empty for now, will be populated by frontend in future)
        expected_behavior=None,
        actual_behavior=None,
        steps_to_reproduce=None,
        # Classification
        severity=None,  # Could be inferred from error logs
        category=category,
        status="open",  # Default to open
        # Source tracking
        source="user",
        reporter_id=data.get("submitted_by"),
        assignee_id=None,
        # Telemetry
        trace_id=data.get("trace_id"),
        request_id=None,
        release_sha=None,
        # Build metadata
        app_version=app_version,
        git_sha=git_sha,
        build_time=build_time,
        # Context metadata (will be populated by frontend improvements)
        suspected_components=None,
        related_files=None,
        navigation_history=None,
        # Full context (preserve existing data)
        environment=json.dumps(environment) if environment else None,
        client_meta=json.dumps(client_meta) if client_meta else None,
        app_state=json.dumps(app_state) if app_state else None,
        recent_logs=json.dumps(data.get("recentLogs", [])),
        network_events=json.dumps(data.get("networkEvents", [])),
        # Screenshot
        screenshot_path=data.get("screenshot_path"),
        screenshot_error=data.get("screenshot_error"),
        # Resolution (check if closed)
        resolution_notes=None,
        resolution_commit_sha=None,
        # Deduplication
        duplicate_of_id=None,
        dedup_hash=None,  # Will be computed by dedup engine later
        # Automation
        automation_enabled=True,  # Enable by default
        automation_attempts=0,
        last_automation_at=None,
        # Timestamps
        created_at=parse_timestamp(data.get("submitted_at")) or datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        resolved_at=None,
        sla_due_at=None,
    )

    if dry_run:
        logger.info(f"  [DRY RUN] Would create: {report_id}")
        return True

    try:
        db.session.add(bug_report)
        db.session.flush()  # Get the ID

        # Create initial event
        event = BugReportEvent(
            bug_report_id=bug_report.id,
            event_type="created",
            event_data=json.dumps({"source": "migration", "original_file": str(json_path)}),
            actor_id="system",
            actor_type="system",
        )
        db.session.add(event)

        db.session.commit()
        logger.info(f"  ✓ Migrated: {report_id} (id={bug_report.id})")
        return True

    except Exception as e:
        db.session.rollback()
        logger.error(f"  Failed to migrate {report_id}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Migrate bug reports from JSON to database")
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("/mnt/storage/imagineer/bug_reports"),
        help="Directory containing bug report JSON files",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be migrated without writing"
    )
    args = parser.parse_args()

    # Create Flask app context
    app = create_app()

    with app.app_context():
        # Ensure tables exist
        db.create_all()
        logger.info("Database tables created/verified")

        # Find all JSON files
        json_files = sorted(args.reports_dir.glob("bug_*.json"))
        logger.info(f"Found {len(json_files)} bug report files in {args.reports_dir}")

        if not json_files:
            logger.warning("No bug report files found!")
            return 1

        # Migrate each report
        success_count = 0
        for json_path in json_files:
            if migrate_report(json_path, dry_run=args.dry_run):
                success_count += 1

        logger.info(f"\nMigration complete: {success_count}/{len(json_files)} reports migrated")

        if args.dry_run:
            logger.info("DRY RUN - no changes were made to the database")

    return 0


if __name__ == "__main__":
    sys.exit(main())
