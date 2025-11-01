"""
Helpers for managing bug report files on disk.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

logger = logging.getLogger(__name__)

BUG_REPORT_PATTERN = "bug_*.json"


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except ValueError:
        logger.debug("Unable to parse bug report timestamp %s", value)
        return None


@dataclass
class BugReportSummary:
    report_id: str
    status: str
    submitted_at: Optional[datetime]
    submitted_by: Optional[str]
    trace_id: Optional[str]
    size_bytes: int
    path: Path

    @property
    def submitted_at_iso(self) -> Optional[str]:
        if not self.submitted_at:
            return None
        value = self.submitted_at.astimezone(timezone.utc)
        return value.isoformat().replace("+00:00", "Z")

    def to_dict(self, *, root: Path) -> dict:
        return {
            "report_id": self.report_id,
            "status": self.status,
            "submitted_at": self.submitted_at_iso,
            "submitted_by": self.submitted_by,
            "trace_id": self.trace_id,
            "size_bytes": self.size_bytes,
            "relative_path": str(self.path.relative_to(root)),
        }


class BugReportStorageError(RuntimeError):
    """Raised when a bug report cannot be read or written."""


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Bug report not found: {path}") from exc
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to read bug report %s: %s", path, exc)
        raise BugReportStorageError(f"Failed to read bug report {path}") from exc


def _write_json(path: Path, payload: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(payload, indent=2)
        if not serialized.endswith("\n"):
            serialized += "\n"
        path.write_text(serialized, encoding="utf-8")
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to write bug report %s: %s", path, exc)
        raise BugReportStorageError(f"Failed to write bug report {path}") from exc


def _iter_report_paths(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return root.rglob(BUG_REPORT_PATTERN)


def list_reports(root: Path, *, status: Optional[str] = None) -> List[BugReportSummary]:
    summaries: List[BugReportSummary] = []
    for path in _iter_report_paths(root):
        try:
            payload = _read_json(path)
        except (BugReportStorageError, FileNotFoundError):
            continue

        report_id = payload.get("report_id") or path.stem
        report_status = str(payload.get("status", "open")).lower()
        submitted_at = _parse_timestamp(payload.get("submitted_at"))
        submitted_by = payload.get("submitted_by")
        trace_id = payload.get("trace_id")
        size_bytes = path.stat().st_size

        summary = BugReportSummary(
            report_id=report_id,
            status=report_status,
            submitted_at=submitted_at,
            submitted_by=submitted_by,
            trace_id=trace_id,
            size_bytes=size_bytes,
            path=path,
        )

        if status and report_status != status.lower():
            continue

        summaries.append(summary)

    summaries.sort(
        key=lambda item: (item.submitted_at or datetime.min, item.report_id), reverse=True
    )
    return summaries


def find_report_path(report_id: str, root: Path) -> Path:
    report_id = report_id.strip()
    candidates = [
        root / f"{report_id}.json",
        root / report_id,
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    # Fallback to recursive search
    for path in _iter_report_paths(root):
        if path.name == f"{report_id}.json" or path.stem == report_id:
            return path

    raise FileNotFoundError(f"No bug report found with id {report_id}")


def load_report(report_id: str, root: Path) -> dict:
    path = find_report_path(report_id, root)
    payload = _read_json(path)
    payload.setdefault("report_id", path.stem)
    payload.setdefault("status", "open")
    payload.setdefault("stored_at", str(path))
    return payload


def update_report(
    report_id: str,
    root: Path,
    *,
    status: Optional[str] = None,
    resolution: Optional[dict] = None,
) -> dict:
    path = find_report_path(report_id, root)
    payload = _read_json(path)

    if status:
        normalized = status.lower()
        if normalized not in {"open", "resolved"}:
            raise ValueError("status must be 'open' or 'resolved'")
        payload["status"] = normalized
        payload["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    if resolution:
        payload.setdefault("resolution", {}).update(resolution)

    _write_json(path, payload)
    payload["stored_at"] = str(path)
    return payload


def delete_report(report_id: str, root: Path) -> None:
    path = find_report_path(report_id, root)
    try:
        path.unlink()
    except FileNotFoundError:
        raise
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to delete bug report %s: %s", path, exc)
        raise BugReportStorageError(f"Failed to delete bug report {path}") from exc


def purge_reports_older_than(root: Path, cutoff: datetime) -> dict:
    cutoff = cutoff.astimezone(timezone.utc)
    removed = 0
    skipped = 0
    for path in list(_iter_report_paths(root)):
        try:
            payload = _read_json(path)
        except (BugReportStorageError, FileNotFoundError):
            skipped += 1
            continue

        submitted_at = _parse_timestamp(payload.get("submitted_at"))
        if not submitted_at:
            skipped += 1
            continue

        if submitted_at.astimezone(timezone.utc) >= cutoff:
            continue

        try:
            path.unlink()
            removed += 1
        except FileNotFoundError:
            continue
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to delete stale bug report %s: %s", path, exc)
            skipped += 1

    return {
        "deleted": removed,
        "skipped": skipped,
        "cutoff": cutoff.isoformat().replace("+00:00", "Z"),
    }
