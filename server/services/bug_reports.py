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
from typing import Any, Dict, List, Optional

from server.database import BugReport, db

logger = logging.getLogger(__name__)


@dataclass
class BugReportRecord:
    """In-memory view of a bug report entry (for backward compatibility)."""

    report_id: str
    payload: Dict[str, Any]

    @classmethod
    def from_db_model(cls, bug_report: BugReport) -> "BugReportRecord":
        """Create a BugReportRecord from a database BugReport model."""
        return cls(report_id=bug_report.report_id, payload=bug_report.to_dict(include_context=True))

    @property
    def status(self) -> str:
        return str(self.payload.get("status", "open")).lower()

    def to_dict(self, *, include_context: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for API serialization."""
        # The payload already contains the full data
        if include_context:
            return self.payload
        else:
            # Return without nested context
            result = dict(self.payload)
            # Remove nested context if present
            result.pop("context", None)
            return result


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
            logger.warning(f"Failed to parse events for {report_id}, resetting")
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
