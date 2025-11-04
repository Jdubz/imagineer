"""
Convenience helpers for working with stored bug reports.

This implementation uses the database-backed BugReport model for reliable
storage and querying. It provides a clean interface for the API routes
and agent manager.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from uuid import uuid4

from server.database import BugReport, db

logger = logging.getLogger(__name__)


@dataclass
class BugReportRecord:
    """In-memory view of a bug report entry (for backward compatibility)."""

    model: BugReport

    @classmethod
    def from_db_model(cls, bug_report: BugReport) -> "BugReportRecord":
        """Create a BugReportRecord from a database BugReport model."""
        return cls(model=bug_report)

    @property
    def report_id(self) -> str:
        return self.model.report_id

    @property
    def status(self) -> str:
        return str(self.model.status or "open").lower()

    def to_dict(self, *, include_context: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for API serialization."""
        return self.model.to_dict(include_context=include_context)


def _generate_report_id(trace_id: Optional[str]) -> str:
    """Generate a stable bug report identifier."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    prefix = (trace_id or uuid4().hex)[:8]
    suffix = uuid4().hex[:4]
    return f"bug_{timestamp}_{prefix}{suffix}"


def _json_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (list, dict)) and not value:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


def _normalise_optional(payload: Dict[str, Any], *keys: str) -> Optional[str]:
    """
    Extract first non-empty value from payload using provided key variants.

    Checks keys in order (snake_case first, then camelCase) and returns
    the first non-empty value found. This handles both naming conventions
    from different API clients.

    Note: If multiple variants exist with values, only the first is returned.
    This is intentional to handle legacy data migration scenarios.
    """
    for key in keys:
        if key in payload and payload[key]:
            return str(payload[key])
    return None


def generate_report_id(trace_id: Optional[str]) -> str:
    """Public helper to generate a bug report identifier."""
    return _generate_report_id(trace_id)


def create_bug_report(
    *,
    payload: Dict[str, Any],
    trace_id: Optional[str],
    submitted_by: Optional[str],
    screenshot_path: Optional[str],
    screenshot_error: Optional[str],
    report_id: Optional[str] = None,
) -> BugReportRecord:
    """
    Create a new bug report from a validated payload.

    Args:
        payload: Request payload (camelCase keys as per schema)
        trace_id: Request trace identifier
        submitted_by: Email of the submitting user
        screenshot_path: Path to stored screenshot (if any)
        screenshot_error: Screenshot failure note (if any)
    """

    report_id = report_id or _generate_report_id(trace_id)
    timestamp = datetime.now(timezone.utc)

    bug_report = BugReport(
        report_id=report_id,
        trace_id=trace_id,
        submitted_by=submitted_by,
        submitted_at=timestamp,
        description=str(payload["description"]),
        expected_behavior=_normalise_optional(payload, "expected_behavior", "expectedBehavior"),
        actual_behavior=_normalise_optional(payload, "actual_behavior", "actualBehavior"),
        steps_to_reproduce=_json_or_none(
            payload.get("steps_to_reproduce") or payload.get("stepsToReproduce") or []
        ),
        status="open",
        automation_attempts=0,
        screenshot_path=screenshot_path,
        screenshot_error=screenshot_error,
    )

    for request_key, model_field in (
        ("environment", "environment"),
        ("clientMeta", "client_meta"),
        ("appState", "app_state"),
        ("recentLogs", "recent_logs"),
        ("networkEvents", "network_events"),
    ):
        value = payload.get(request_key)
        if value is not None:
            setattr(bug_report, model_field, json.dumps(value))

    # Record initial submission event for audit history
    bug_report.events = json.dumps(
        [
            {
                "event_type": "submitted",
                "event_data": {"source": "frontend_submission"},
                "actor_id": submitted_by,
                "actor_type": "user" if submitted_by else "system",
                "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
            }
        ]
    )

    db.session.add(bug_report)
    db.session.commit()

    return BugReportRecord.from_db_model(bug_report)


def list_bug_reports(
    *,
    status: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
) -> Tuple[List[BugReportRecord], int]:
    """
    Return paginated bug report results.

    Args:
        status: Optional status filter
        page: 1-based page index
        per_page: Page size (max 100 enforced by caller)

    Returns:
        Tuple of (records, total_count)
    """

    query = BugReport.query
    if status:
        query = query.filter_by(status=status.lower())

    total = query.count()
    offset = max(0, page - 1) * per_page
    bug_reports = query.order_by(BugReport.submitted_at.desc()).offset(offset).limit(per_page).all()

    return [BugReportRecord.from_db_model(br) for br in bug_reports], total


def delete_bug_report(report_id: str) -> bool:
    """
    Delete a bug report and its associated screenshot (if any).

    Returns:
        True if deleted, False if not found.
    """

    bug_report = BugReport.query.filter_by(report_id=report_id).first()
    if not bug_report:
        return False

    screenshot_path = bug_report.screenshot_path
    db.session.delete(bug_report)
    db.session.commit()

    _cleanup_screenshot_files([screenshot_path] if screenshot_path else [])
    return True


def _cleanup_screenshot_files(paths: Iterable[Optional[str]]) -> None:
    for path_str in paths:
        if not path_str:
            continue
        try:
            path = Path(path_str)
        except (TypeError, ValueError):
            continue
        try:
            path.unlink(missing_ok=True)
            if path.parent.exists() and not any(path.parent.iterdir()):
                path.parent.rmdir()
        except OSError:
            logger.debug("Failed to remove screenshot file at %s", path_str, exc_info=True)


def get_bug_report(report_id: str) -> Optional[BugReportRecord]:
    """
    Retrieve a bug report by ID.

    Args:
        report_id: The bug report ID to retrieve

    Returns:
        BugReportRecord if found, None otherwise
    """
    bug_report = BugReport.query.filter_by(report_id=report_id).first()
    if not bug_report:
        return None
    return BugReportRecord.from_db_model(bug_report)


def update_bug_report_status(
    *,
    report_id: str,
    status: Optional[str] = None,
    actor_id: Optional[str] = None,
    resolution_notes: Optional[str] = None,
    resolution_commit_sha: Optional[str] = None,
) -> Optional[BugReportRecord]:
    """
    Update bug report status and resolution information.

    Args:
        report_id: The bug report ID to update
        status: New status ('open', 'in_progress', or 'resolved')
        actor_id: User/agent ID performing the update
        resolution_notes: Notes about the resolution
        resolution_commit_sha: Git commit SHA of the fix

    Returns:
        Updated BugReportRecord if found, None otherwise

    Raises:
        ValueError: If status is invalid
    """
    bug_report = BugReport.query.filter_by(report_id=report_id).first()
    if not bug_report:
        return None

    if status:
        normalized_status = status.lower()
        if normalized_status not in {"open", "in_progress", "resolved"}:
            raise ValueError("status must be 'open', 'in_progress', or 'resolved'")
        bug_report.status = normalized_status

    if actor_id:
        bug_report.resolution_actor_id = actor_id

    if resolution_notes is not None:
        bug_report.resolution_notes = resolution_notes

    if resolution_commit_sha is not None:
        bug_report.resolution_commit_sha = resolution_commit_sha

    # SQLAlchemy will automatically update updated_at due to onupdate=utcnow
    db.session.commit()

    return BugReportRecord.from_db_model(bug_report)


def increment_automation_attempts(report_id: str) -> Optional[BugReportRecord]:
    """
    Increment the automation attempt counter for a bug report.

    Args:
        report_id: The bug report ID to update

    Returns:
        Updated BugReportRecord if found, None otherwise
    """
    bug_report = BugReport.query.filter_by(report_id=report_id).first()
    if not bug_report:
        return None

    bug_report.automation_attempts = (bug_report.automation_attempts or 0) + 1
    db.session.commit()

    return BugReportRecord.from_db_model(bug_report)


def add_bug_report_event(
    *,
    report_id: str,
    event_type: str,
    event_data: Optional[Dict[str, Any]] = None,
    actor_id: Optional[str] = None,
    actor_type: Optional[str] = None,
) -> Optional[BugReportRecord]:
    """
    Add an event to the bug report's event log.

    Args:
        report_id: The bug report ID
        event_type: Type of event (e.g., 'automation_started', 'fix_attempted')
        event_data: Additional event data
        actor_id: User/agent ID that triggered the event
        actor_type: Type of actor ('user', 'agent', 'system')

    Returns:
        Updated BugReportRecord if found, None otherwise
    """
    bug_report = BugReport.query.filter_by(report_id=report_id).first()
    if not bug_report:
        return None

    # Parse existing events
    events = []
    if bug_report.events:
        try:
            events = json.loads(bug_report.events)
        except json.JSONDecodeError:
            logger.warning("Failed to parse events for %s, resetting", report_id)
            events = []

    # Add new event
    events.append(
        {
            "event_type": event_type,
            "event_data": event_data or {},
            "actor_id": actor_id,
            "actor_type": actor_type,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
    )

    # Save back to database
    bug_report.events = json.dumps(events)
    db.session.commit()

    return BugReportRecord.from_db_model(bug_report)


def get_pending_automation_reports(*, limit: int = 10) -> List[BugReportRecord]:
    """
    Get pending bug reports for automated remediation.

    Args:
        limit: Maximum number of reports to return

    Returns:
        List of BugReportRecords with status 'open'
    """
    bug_reports = (
        BugReport.query.filter_by(status="open")
        .order_by(BugReport.submitted_at.desc())
        .limit(limit)
        .all()
    )

    return [BugReportRecord.from_db_model(br) for br in bug_reports]


def purge_bug_reports(
    *,
    cutoff: datetime,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Purge bug reports older than the supplied cutoff timestamp.

    Args:
        cutoff: Oldest allowed submission timestamp (UTC)
        dry_run: When True, do not delete anything and only report counts
    """

    query = BugReport.query.filter(BugReport.submitted_at < cutoff)
    matched = query.count()

    if dry_run:
        return {
            "matched": matched,
            "deleted": 0,
            "skipped": 0,
        }

    bug_reports = query.all()
    screenshot_paths = [br.screenshot_path for br in bug_reports if br.screenshot_path]

    deleted = 0
    for bug_report in bug_reports:
        db.session.delete(bug_report)
        deleted += 1

    db.session.commit()
    _cleanup_screenshot_files(screenshot_paths)

    return {
        "matched": matched,
        "deleted": deleted,
        "skipped": 0,
    }
