"""
Convenience helpers for working with stored bug reports.

The current implementation uses the on-disk JSON storage that powers the
admin API and CLI utilities.  It provides a thin abstraction that matches
the interface expected by the API routes and agent manager while keeping
the door open for a future database-backed implementation.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from server.bug_reports import storage as file_storage
from server.bug_reports.paths import resolve_storage_root

logger = logging.getLogger(__name__)
_CONTEXT_FIELDS: Iterable[str] = (
    "description",
    "environment",
    "clientMeta",
    "appState",
    "recentLogs",
    "networkEvents",
)


def _load_payload(report_id: str) -> Optional[Dict[str, Any]]:
    root = resolve_storage_root()
    try:
        payload = file_storage.load_report(report_id, root)
    except FileNotFoundError:
        return None
    except Exception:
        logger.error("Failed to load bug report %s", report_id, exc_info=True)
        return None
    payload.setdefault("report_id", report_id)
    payload.setdefault("status", "open")
    payload.setdefault("automation_attempts", 0)
    payload.setdefault("events", [])
    return payload


def _write_payload(report_id: str, payload: Dict[str, Any]) -> None:
    root = resolve_storage_root()
    path = file_storage.find_report_path(report_id, root)
    try:
        serialized = json.dumps(payload, indent=2)
        if not serialized.endswith("\n"):
            serialized += "\n"
        path.write_text(serialized, encoding="utf-8")
    except Exception as exc:
        logger.error("Failed to write bug report %s: %s", path, exc)
        raise


@dataclass
class BugReportRecord:
    """In-memory view of a bug report entry."""

    report_id: str
    payload: Dict[str, Any]

    @property
    def status(self) -> str:
        return str(self.payload.get("status", "open")).lower()

    def to_dict(self, *, include_context: bool = False) -> Dict[str, Any]:
        base: Dict[str, Any] = {
            "report_id": self.report_id,
            "status": self.status,
            "submitted_at": self.payload.get("submitted_at"),
            "submitted_by": self.payload.get("submitted_by"),
            "trace_id": self.payload.get("trace_id"),
            "screenshot_path": self.payload.get("screenshot_path"),
            "screenshot_error": self.payload.get("screenshot_error"),
            "automation_attempts": self.payload.get("automation_attempts", 0),
            "stored_at": self.payload.get("stored_at"),
            "updated_at": self.payload.get("updated_at"),
        }

        resolution = self.payload.get("resolution")
        if isinstance(resolution, dict):
            base.setdefault("resolution_notes", resolution.get("notes"))
            base.setdefault("resolution_commit_sha", resolution.get("commit_sha"))
            base.setdefault("resolution_actor_id", resolution.get("actor_id"))

        base.setdefault("resolution_notes", self.payload.get("resolution_notes"))
        base.setdefault("resolution_commit_sha", self.payload.get("resolution_commit_sha"))
        base.setdefault("resolution_actor_id", self.payload.get("resolution_actor_id"))

        if include_context:
            context = {key: self.payload.get(key) for key in _CONTEXT_FIELDS if key in self.payload}
            base["context"] = context
        else:
            for key in _CONTEXT_FIELDS:
                if key in self.payload:
                    base[key] = self.payload[key]

        return base


def get_bug_report(report_id: str) -> Optional[BugReportRecord]:
    payload = _load_payload(report_id)
    if not payload:
        return None
    return BugReportRecord(report_id=report_id, payload=payload)


def update_bug_report_status(
    *,
    report_id: str,
    status: Optional[str] = None,
    actor_id: Optional[str] = None,
    resolution_notes: Optional[str] = None,
    resolution_commit_sha: Optional[str] = None,
) -> Optional[BugReportRecord]:
    payload = _load_payload(report_id)
    if not payload:
        return None

    if status:
        normalized_status = status.lower()
        if normalized_status not in {"open", "resolved"}:
            raise ValueError("status must be 'open' or 'resolved'")
        payload["status"] = normalized_status

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload["updated_at"] = now_iso
    if actor_id:
        payload["resolution_actor_id"] = actor_id

    if resolution_notes is not None:
        payload["resolution_notes"] = resolution_notes
        payload.setdefault("resolution", {})["notes"] = resolution_notes
    if resolution_commit_sha is not None:
        payload["resolution_commit_sha"] = resolution_commit_sha
        payload.setdefault("resolution", {})["commit_sha"] = resolution_commit_sha

    if actor_id:
        payload.setdefault("resolution", {})["actor_id"] = actor_id

    _write_payload(report_id, payload)
    return BugReportRecord(report_id=report_id, payload=payload)


def increment_automation_attempts(report_id: str) -> Optional[BugReportRecord]:
    payload = _load_payload(report_id)
    if not payload:
        return None
    attempts = int(payload.get("automation_attempts", 0) or 0)
    payload["automation_attempts"] = attempts + 1
    payload["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    _write_payload(report_id, payload)
    return BugReportRecord(report_id=report_id, payload=payload)


def add_bug_report_event(
    *,
    report_id: str,
    event_type: str,
    event_data: Optional[Dict[str, Any]] = None,
    actor_id: Optional[str] = None,
    actor_type: Optional[str] = None,
) -> Optional[BugReportRecord]:
    payload = _load_payload(report_id)
    if not payload:
        return None

    events = payload.setdefault("events", [])
    events.append(
        {
            "event_type": event_type,
            "event_data": event_data or {},
            "actor_id": actor_id,
            "actor_type": actor_type,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
    )
    payload["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    _write_payload(report_id, payload)
    return BugReportRecord(report_id=report_id, payload=payload)


def get_pending_automation_reports(*, limit: int = 10) -> List[BugReportRecord]:
    root = resolve_storage_root()
    summaries = file_storage.list_reports(root, status="open")
    records: List[BugReportRecord] = []
    for summary in summaries:
        report = get_bug_report(summary.report_id)
        if not report:
            continue
        records.append(report)
        if len(records) >= limit:
            break
    return records
