"""
Bug report service layer.

Handles CRUD operations and business logic for bug reports.
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

from server.database import BugReport, BugReportEvent, db

logger = logging.getLogger(__name__)


def create_bug_report(
    report_id: str,
    description: str,
    trace_id: Optional[str] = None,
    reporter_id: Optional[str] = None,
    screenshot_path: Optional[str] = None,
    screenshot_error: Optional[str] = None,
    environment: Optional[dict] = None,
    client_meta: Optional[dict] = None,
    app_state: Optional[dict] = None,
    recent_logs: Optional[list] = None,
    network_events: Optional[list] = None,
    expected_behavior: Optional[str] = None,
    actual_behavior: Optional[str] = None,
    steps_to_reproduce: Optional[list] = None,
    suspected_components: Optional[list] = None,
    related_files: Optional[list] = None,
    navigation_history: Optional[list] = None,
) -> BugReport:
    """
    Create a new bug report in the database.

    Args:
        report_id: Unique report identifier
        description: Bug description
        trace_id: Request trace ID
        reporter_id: User who reported the bug
        screenshot_path: Path to screenshot file
        screenshot_error: Screenshot capture error message
        environment: Environment metadata (dict)
        client_meta: Client metadata (dict)
        app_state: Application state (dict)
        recent_logs: Recent log entries (list)
        network_events: Network event log (list)
        expected_behavior: Expected behavior description
        actual_behavior: Actual behavior description
        steps_to_reproduce: Steps to reproduce (list)
        suspected_components: Suspected components (list)
        related_files: Related file paths (list)
        navigation_history: Navigation history (list)

    Returns:
        Created BugReport instance
    """
    # Extract build metadata from environment
    env = environment or {}
    app_version = env.get("appVersion")
    git_sha = env.get("gitSha")
    build_time_str = env.get("buildTime")
    build_time = None
    if build_time_str:
        try:
            if build_time_str.endswith("Z"):
                build_time_str = build_time_str[:-1] + "+00:00"
            build_time = datetime.fromisoformat(build_time_str)
        except (ValueError, AttributeError):
            pass

    # Determine category heuristically from route
    route = (client_meta or {}).get("locationHref", "")
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
        title=description[:500] if description else None,
        description=description,
        expected_behavior=expected_behavior,
        actual_behavior=actual_behavior,
        steps_to_reproduce=json.dumps(steps_to_reproduce) if steps_to_reproduce else None,
        severity=None,
        category=category,
        status="new",
        source="user",
        reporter_id=reporter_id,
        assignee_id=None,
        trace_id=trace_id,
        request_id=None,
        release_sha=None,
        app_version=app_version,
        git_sha=git_sha,
        build_time=build_time,
        suspected_components=json.dumps(suspected_components) if suspected_components else None,
        related_files=json.dumps(related_files) if related_files else None,
        navigation_history=json.dumps(navigation_history) if navigation_history else None,
        environment=json.dumps(environment) if environment else None,
        client_meta=json.dumps(client_meta) if client_meta else None,
        app_state=json.dumps(app_state) if app_state else None,
        recent_logs=json.dumps(recent_logs) if recent_logs else None,
        network_events=json.dumps(network_events) if network_events else None,
        screenshot_path=screenshot_path,
        screenshot_error=screenshot_error,
        resolution_notes=None,
        resolution_commit_sha=None,
        duplicate_of_id=None,
        dedup_hash=None,
        automation_enabled=True,
        automation_attempts=0,
        last_automation_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        resolved_at=None,
        sla_due_at=None,
    )

    db.session.add(bug_report)
    db.session.flush()

    # Create initial event
    event = BugReportEvent(
        bug_report_id=bug_report.id,
        event_type="created",
        event_data=json.dumps(
            {
                "reporter_id": reporter_id,
                "trace_id": trace_id,
                "category": category,
            }
        ),
        actor_id=reporter_id or "anonymous",
        actor_type="user",
    )
    db.session.add(event)
    db.session.commit()

    logger.info(f"Created bug report: {report_id} (id={bug_report.id})")
    return bug_report


def get_bug_report(report_id: str) -> Optional[BugReport]:
    """Get bug report by report_id."""
    return BugReport.query.filter_by(report_id=report_id).first()


def get_bug_report_by_id(id: int) -> Optional[BugReport]:
    """Get bug report by database ID."""
    return BugReport.query.get(id)


def list_bug_reports(
    status: Optional[str] = None,
    assignee_id: Optional[str] = None,
    automation_enabled: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[BugReport]:
    """
    List bug reports with optional filtering.

    Args:
        status: Filter by status (new, triaged, in_progress, etc.)
        assignee_id: Filter by assignee
        automation_enabled: Filter by automation flag
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of BugReport instances
    """
    query = BugReport.query

    if status:
        query = query.filter_by(status=status)
    if assignee_id:
        query = query.filter_by(assignee_id=assignee_id)
    if automation_enabled is not None:
        query = query.filter_by(automation_enabled=automation_enabled)

    query = query.order_by(BugReport.created_at.desc())
    return query.limit(limit).offset(offset).all()


def update_bug_report_status(
    report_id: str,
    status: str,
    actor_id: Optional[str] = None,
    resolution_notes: Optional[str] = None,
    resolution_commit_sha: Optional[str] = None,
) -> Optional[BugReport]:
    """
    Update bug report status.

    Args:
        report_id: Bug report ID
        status: New status
        actor_id: Who performed the update
        resolution_notes: Resolution notes (if resolving)
        resolution_commit_sha: Commit SHA of the fix (if resolving)

    Returns:
        Updated BugReport or None if not found
    """
    bug_report = get_bug_report(report_id)
    if not bug_report:
        return None

    old_status = bug_report.status
    bug_report.status = status
    bug_report.updated_at = datetime.now(timezone.utc)

    if status in ("resolved", "closed") and not bug_report.resolved_at:
        bug_report.resolved_at = datetime.now(timezone.utc)

    if resolution_notes:
        bug_report.resolution_notes = resolution_notes
    if resolution_commit_sha:
        bug_report.resolution_commit_sha = resolution_commit_sha

    # Create event
    event = BugReportEvent(
        bug_report_id=bug_report.id,
        event_type="status_change",
        event_data=json.dumps(
            {
                "old_status": old_status,
                "new_status": status,
                "resolution_notes": resolution_notes,
                "resolution_commit_sha": resolution_commit_sha,
            }
        ),
        actor_id=actor_id or "system",
        actor_type="user" if actor_id else "system",
    )
    db.session.add(event)
    db.session.commit()

    logger.info(f"Updated bug report {report_id}: {old_status} -> {status}")
    return bug_report


def add_bug_report_event(
    report_id: str,
    event_type: str,
    event_data: Optional[dict] = None,
    actor_id: Optional[str] = None,
    actor_type: str = "system",
) -> Optional[BugReportEvent]:
    """
    Add an event to a bug report.

    Args:
        report_id: Bug report ID
        event_type: Type of event (note, agent_run, assignment, etc.)
        event_data: Event data dictionary
        actor_id: Actor who triggered the event
        actor_type: Type of actor (user, agent, system)

    Returns:
        Created BugReportEvent or None if report not found
    """
    bug_report = get_bug_report(report_id)
    if not bug_report:
        return None

    event = BugReportEvent(
        bug_report_id=bug_report.id,
        event_type=event_type,
        event_data=json.dumps(event_data) if event_data else None,
        actor_id=actor_id or "system",
        actor_type=actor_type,
    )
    db.session.add(event)
    db.session.commit()

    logger.info(f"Added event to bug report {report_id}: {event_type}")
    return event


def increment_automation_attempts(report_id: str) -> Optional[BugReport]:
    """
    Increment automation attempt counter for a bug report.

    Args:
        report_id: Bug report ID

    Returns:
        Updated BugReport or None if not found
    """
    bug_report = get_bug_report(report_id)
    if not bug_report:
        return None

    bug_report.automation_attempts += 1
    bug_report.last_automation_at = datetime.now(timezone.utc)
    db.session.commit()

    return bug_report


def get_pending_automation_reports(limit: int = 10) -> List[BugReport]:
    """
    Get bug reports that are pending automated remediation.

    Returns reports that:
    - Have automation enabled
    - Are in 'new' or 'triaged' status
    - Are not duplicates

    Args:
        limit: Maximum number of reports to return

    Returns:
        List of BugReport instances
    """
    return (
        BugReport.query.filter_by(automation_enabled=True, duplicate_of_id=None)
        .filter(BugReport.status.in_(["new", "triaged"]))
        .order_by(BugReport.created_at.asc())
        .limit(limit)
        .all()
    )
