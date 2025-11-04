#!/usr/bin/env python3
"""
Migration script to import JSON-based bug reports into the database.

This script reads all existing bug report JSON files from the file system
and imports them into the BugReport database table.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask

from server.bug_reports.storage import list_reports, load_report
from server.config_loader import load_config
from server.database import BugReport, MigrationHistory, db, init_database

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_bug_reports_dir() -> Path:
    """Get bug reports directory from config."""
    config = load_config()
    storage_path = config.get("bug_reports", {}).get("storage_path")
    if storage_path:
        return Path(storage_path).expanduser()
    return Path("/mnt/storage/imagineer/bug_reports").expanduser()


def parse_timestamp(ts_str: str | None) -> datetime | None:
    """Parse ISO timestamp string to datetime object."""
    if not ts_str:
        return None
    try:
        # Handle both with and without 'Z' suffix
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        return datetime.fromisoformat(ts_str)
    except (ValueError, AttributeError):
        return None


def migrate_bug_report(report_id: str, payload: dict) -> BugReport | None:
    """
    Create a BugReport database record from JSON payload.

    Args:
        report_id: The bug report ID
        payload: The JSON payload from the file

    Returns:
        The created BugReport object, or None if it already exists
    """
    # Check if already migrated
    existing = BugReport.query.filter_by(report_id=report_id).first()
    if existing:
        logger.debug(f"Bug report {report_id} already exists in database, skipping")
        return None

    # Parse timestamps
    submitted_at = parse_timestamp(payload.get("submitted_at")) or datetime.now(timezone.utc)

    # Create BugReport record
    bug_report = BugReport(
        report_id=report_id,
        trace_id=payload.get("trace_id"),
        submitted_by=payload.get("submitted_by"),
        submitted_at=submitted_at,
        description=payload.get("description", ""),
        expected_behavior=payload.get("expected_behavior") or payload.get("expectedBehavior"),
        actual_behavior=payload.get("actual_behavior") or payload.get("actualBehavior"),
        status=payload.get("status", "open"),
        automation_attempts=payload.get("automation_attempts", 0),
        screenshot_path=payload.get("screenshot_path"),
        screenshot_error=payload.get("screenshot_error"),
        resolution_notes=payload.get("resolution_notes"),
        resolution_commit_sha=payload.get("resolution_commit_sha"),
        resolution_actor_id=payload.get("resolution_actor_id"),
    )

    steps = payload.get("steps_to_reproduce") or payload.get("stepsToReproduce")
    if steps:
        if isinstance(steps, (list, dict)):
            bug_report.steps_to_reproduce = json.dumps(steps)
        else:
            bug_report.steps_to_reproduce = json.dumps([steps])

    # Set JSON fields
    for field in ["environment", "clientMeta", "appState", "recentLogs", "networkEvents"]:
        value = payload.get(field)
        if value:
            # Convert camelCase to snake_case for database field names
            db_field = field
            if field == "clientMeta":
                db_field = "client_meta"
            elif field == "appState":
                db_field = "app_state"
            elif field == "recentLogs":
                db_field = "recent_logs"
            elif field == "networkEvents":
                db_field = "network_events"

            # Store as JSON string
            if isinstance(value, (dict, list)):
                setattr(bug_report, db_field, json.dumps(value))
            else:
                setattr(bug_report, db_field, value)

    # Set events if present
    events = payload.get("events", [])
    if events:
        bug_report.events = json.dumps(events)

    # Set timestamps
    created_at = parse_timestamp(payload.get("stored_at")) or submitted_at
    updated_at = parse_timestamp(payload.get("updated_at")) or created_at

    bug_report.created_at = created_at
    bug_report.updated_at = updated_at

    return bug_report


def migrate_all_reports(app: Flask, reports_dir: Path) -> dict:
    """
    Migrate all JSON bug reports to the database.

    Args:
        app: Flask application context
        reports_dir: Directory containing bug report JSON files

    Returns:
        Dictionary with migration statistics
    """
    stats = {"total": 0, "migrated": 0, "skipped": 0, "errors": 0}

    with app.app_context():
        # Get all reports from file system
        logger.info(f"Scanning for bug reports in {reports_dir}")
        summaries = list_reports(reports_dir)
        stats["total"] = len(summaries)

        logger.info(f"Found {stats['total']} bug reports to migrate")

        for summary in summaries:
            try:
                # Load full report payload
                payload = load_report(summary.report_id, reports_dir)

                # Migrate to database
                bug_report = migrate_bug_report(summary.report_id, payload)

                if bug_report:
                    db.session.add(bug_report)
                    stats["migrated"] += 1
                    logger.info(f"Migrated {summary.report_id} (status: {bug_report.status})")
                else:
                    stats["skipped"] += 1

                # Commit in batches of 10
                if (stats["migrated"] + stats["skipped"]) % 10 == 0:
                    db.session.commit()

            except Exception as e:
                stats["errors"] += 1
                logger.error(f"Failed to migrate {summary.report_id}: {e}", exc_info=True)
                db.session.rollback()

        # Final commit
        db.session.commit()

        # Record migration in history
        migration_details = json.dumps(stats)
        MigrationHistory.ensure_record(
            "bug_reports_json_to_db_migration",
            details=migration_details,
            refresh_timestamp=True,
        )
        db.session.commit()

        logger.info(f"Migration complete: {stats}")

    return stats


def main():
    """Main migration entry point."""
    # Create Flask app
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "sqlite:///instance/imagineer.db"  # Update with your actual DB URI
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize database
    init_database(app)

    # Get reports directory
    reports_dir = get_bug_reports_dir()

    if not reports_dir.exists():
        logger.warning(f"Bug reports directory not found: {reports_dir}")
        logger.info("No migration needed - directory doesn't exist")
        return 0

    # Check if already migrated
    with app.app_context():
        if MigrationHistory.has_run("bug_reports_json_to_db_migration"):
            logger.info("Migration has already been run")
            response = input("Run migration again? (y/N): ")
            if response.lower() != "y":
                logger.info("Migration cancelled")
                return 0

    # Run migration
    logger.info("Starting bug report migration...")
    stats = migrate_all_reports(app, reports_dir)

    # Print summary
    print("\n" + "=" * 60)
    print("Bug Report Migration Summary")
    print("=" * 60)
    print(f"Total reports found:  {stats['total']}")
    print(f"Successfully migrated: {stats['migrated']}")
    print(f"Skipped (duplicates): {stats['skipped']}")
    print(f"Errors:               {stats['errors']}")
    print("=" * 60)

    if stats["errors"] > 0:
        print("\n⚠️  Some errors occurred during migration. Check logs for details.")
        return 1

    print("\n✅ Migration completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
