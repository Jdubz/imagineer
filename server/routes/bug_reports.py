"""
Bug report submission endpoint.

Allows admin users to submit detailed bug reports with automatic context capture.
"""

import base64
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

from flask import Blueprint, current_app, g, jsonify, request
from jsonschema import Draft202012Validator, ValidationError
from werkzeug.exceptions import BadRequest

from server.auth import require_admin
from server.bug_reports.storage import (
    BugReportStorageError,
    delete_report,
    list_reports,
    load_report,
    purge_reports_older_than,
    update_report,
)
from server.config_loader import PROJECT_ROOT, load_config
from server.services import bug_reports as bug_report_service
from server.shared_types import (
    BugReportSubmissionRequestTypedDict,
    BugReportSubmissionResponseTypedDict,
)
from server.utils.error_handler import APIError, format_error_response

logger = logging.getLogger(__name__)

bug_reports_bp = Blueprint("bug_reports", __name__)

_SCHEMA_DIR = PROJECT_ROOT / "shared" / "schema"
with (_SCHEMA_DIR / "bug_report_submission_request.json").open("r", encoding="utf-8") as f:
    _BUG_REPORT_REQUEST_VALIDATOR = Draft202012Validator(json.load(f))
with (_SCHEMA_DIR / "bug_report_submission_response.json").open("r", encoding="utf-8") as f:
    _BUG_REPORT_RESPONSE_VALIDATOR = Draft202012Validator(json.load(f))


def _in_testing_mode() -> bool:
    """Return True when running inside pytest or a testing Flask app."""
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True
    try:
        return bool(current_app.testing)  # type: ignore[attr-defined]
    except Exception:
        return False


def _log_storage_failure(message: str, exc: Exception) -> None:
    """Log storage-related failures without spamming error severity during tests."""
    if _in_testing_mode():
        logger.warning("%s (testing mode): %s", message, exc)
        logger.debug("Suppressed stack trace for testing-only failure", exc_info=True)
    else:
        logger.error(message, exc_info=True)


def get_bug_reports_dir() -> str:
    """
    Get bug reports directory from config.

    Returns:
        Path to bug reports directory
    """
    env_override = os.getenv("BUG_REPORTS_PATH")
    if env_override:
        return env_override

    try:
        config = load_config()
        storage_path = config.get("bug_reports", {}).get("storage_path")
        if storage_path:
            return storage_path
    except Exception:
        logger.warning(
            "Falling back to default bug report directory due to config load failure",
            exc_info=True,
        )

    return "/mnt/storage/imagineer/bug_reports"


def _get_reports_root() -> Path:
    return Path(get_bug_reports_dir()).expanduser()


@bug_reports_bp.route("/api/bug-reports", methods=["POST"])
@require_admin
def submit_bug_report():
    """
    Submit a bug report with full context.

    Admin-only endpoint that accepts bug report payload with logs,
    network events, application state, and environment information.

    Request Body:
        {
            "description": str (required),
            "environment": {...},
            "clientMeta": {...},
            "appState": {...},
            "recentLogs": [...],
            "networkEvents": [...]
        }

    Returns:
        201: Bug report saved successfully
        400: Invalid request payload
        401: Unauthorized (non-admin user)
        500: Failed to save bug report
    """
    try:
        # Get request payload
        try:
            payload_raw = request.get_json()
        except BadRequest as exc:
            raise APIError(
                "Request body must be valid JSON", "INVALID_JSON", 400, {"error": str(exc)}
            )

        if payload_raw is None:
            raise APIError("Request body is required", "MISSING_PAYLOAD", 400)

        if not isinstance(payload_raw, dict):
            raise APIError("Request body must be a JSON object", "INVALID_PAYLOAD", 400)

        try:
            _BUG_REPORT_REQUEST_VALIDATOR.validate(payload_raw)
        except ValidationError as exc:
            if exc.validator == "required" and "description" in exc.message:
                raise APIError("Description is required", "MISSING_DESCRIPTION", 400)
            raise APIError(
                "Invalid bug report payload",
                "INVALID_BUG_REPORT_PAYLOAD",
                400,
                {"schema_error": exc.message},
            )

        payload = cast(BugReportSubmissionRequestTypedDict, payload_raw)

        if payload["description"].strip() == "":
            raise APIError("Description is required", "MISSING_DESCRIPTION", 400)

        # Generate report ID with timestamp and trace ID prefix
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        trace_id_prefix = g.trace_id[:8] if hasattr(g, "trace_id") else "unknown"
        report_id = f"bug_{timestamp}_{trace_id_prefix}"

        # Create report directory
        reports_dir = get_bug_reports_dir()
        try:
            os.makedirs(reports_dir, exist_ok=True)
        except Exception as e:
            _log_storage_failure(f"Failed to create bug reports directory: {reports_dir}", e)
            raise APIError(
                "Failed to create bug reports directory",
                "STORAGE_ERROR",
                500,
                {"directory": reports_dir, "error": str(e)},
            )

        report_path = os.path.join(reports_dir, f"{report_id}.json")

        # Extract and save screenshot if provided
        screenshot_data = payload_raw.get("screenshot")
        screenshot_path = None
        server_screenshot_error = None
        client_screenshot_error = payload_raw.get("screenshotError")

        if screenshot_data and isinstance(screenshot_data, str):
            try:
                # Create report subdirectory for screenshot
                report_subdir = os.path.join(reports_dir, report_id)
                os.makedirs(report_subdir, exist_ok=True)
                screenshot_path = os.path.join(report_subdir, "screenshot.png")

                # Extract base64 data (handle data:image/png;base64, prefix)
                if screenshot_data.startswith("data:"):
                    screenshot_data = screenshot_data.split(",", 1)[1]

                # Decode and save screenshot
                screenshot_bytes = base64.b64decode(screenshot_data)
                with open(screenshot_path, "wb") as f:
                    f.write(screenshot_bytes)

                logger.info(f"Screenshot saved for report {report_id}")
            except Exception as e:
                server_screenshot_error = str(e)
                logger.warning(f"Failed to save screenshot for report {report_id}: {e}")
                screenshot_path = None

        # Combine client and server screenshot errors
        screenshot_error = client_screenshot_error or server_screenshot_error

        # Save to database
        try:
            bug_report_service.create_bug_report(
                report_id=report_id,
                description=payload["description"],
                trace_id=g.trace_id if hasattr(g, "trace_id") else None,
                reporter_id=g.user.email if hasattr(g, "user") else None,
                screenshot_path=screenshot_path,
                screenshot_error=screenshot_error,
                environment=payload.get("environment"),
                client_meta=payload.get("clientMeta"),
                app_state=payload.get("appState"),
                recent_logs=payload.get("recentLogs"),
                network_events=payload.get("networkEvents"),
            )
        except Exception as e:
            logger.error(f"Failed to save bug report to database: {e}", exc_info=True)
            raise APIError(
                "Failed to save bug report",
                "DATABASE_ERROR",
                500,
                {"error": str(e)},
            )

        # Also write to disk for backward compatibility (temporary during migration)
        try:
            report = {
                "report_id": report_id,
                "trace_id": g.trace_id if hasattr(g, "trace_id") else None,
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "submitted_by": g.user.email if hasattr(g, "user") else None,
                "user_role": g.user.role if hasattr(g, "user") else None,
                "status": "open",
                "screenshot_path": screenshot_path,
                "screenshot_error": screenshot_error,
                **{k: v for k, v in payload.items() if k not in ("screenshot", "screenshotError")},
            }
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2)
        except Exception as e:
            # Log but don't fail - database is primary storage now
            logger.warning(f"Failed to write bug report JSON backup: {e}")

        logger.info(
            f"Bug report saved: {report_id}",
            extra={
                "report_id": report_id,
                "user": g.user.email if hasattr(g, "user") else None,
            },
        )

        # Enqueue for automated remediation
        try:
            from server.bug_reports.agent_manager import get_bug_report_agent_manager

            get_bug_report_agent_manager().enqueue(report_id)
            logger.info(f"Bug report {report_id} enqueued for automated remediation")
        except Exception as e:
            logger.warning(f"Failed to enqueue bug report {report_id} for remediation: {e}")

        response_payload: BugReportSubmissionResponseTypedDict = {
            "success": True,
            "report_id": report_id,
            "trace_id": g.trace_id if hasattr(g, "trace_id") else None,
            "stored_at": report_path,
        }

        try:
            _BUG_REPORT_RESPONSE_VALIDATOR.validate(response_payload)
        except ValidationError as exc:
            raise APIError(
                "Failed to save bug report",
                "BUG_REPORT_RESPONSE_INVALID",
                500,
                {"schema_error": exc.message},
            )

        return jsonify(response_payload), 201

    except APIError as e:
        return format_error_response(e)
    except Exception as exc:
        _log_storage_failure("Unexpected error saving bug report", exc)
        return format_error_response(
            APIError("Failed to save bug report", "BUG_REPORT_SAVE_FAILED", 500)
        )


@bug_reports_bp.route("/api/bug-reports", methods=["GET"])
@require_admin
def list_bug_reports_endpoint():
    """Return paginated list of bug reports from database."""
    try:
        status_filter = request.args.get("status")
        assignee_filter = request.args.get("assignee_id")
        automation_filter = request.args.get("automation_enabled")
        page = max(1, request.args.get("page", default=1, type=int))
        per_page = min(100, max(1, request.args.get("per_page", default=20, type=int)))

        # Convert string automation filter to boolean
        automation_enabled = None
        if automation_filter is not None:
            automation_enabled = automation_filter.lower() in ("true", "1", "yes")

        # Calculate offset
        offset = (page - 1) * per_page

        # Get reports from database
        reports = bug_report_service.list_bug_reports(
            status=status_filter,
            assignee_id=assignee_filter,
            automation_enabled=automation_enabled,
            limit=per_page,
            offset=offset,
        )

        # Get total count for pagination
        from server.database import BugReport

        query = BugReport.query
        if status_filter:
            query = query.filter_by(status=status_filter)
        if assignee_filter:
            query = query.filter_by(assignee_id=assignee_filter)
        if automation_enabled is not None:
            query = query.filter_by(automation_enabled=automation_enabled)
        total = query.count()

        return jsonify(
            {
                "reports": [report.to_dict(include_context=False) for report in reports],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": max(1, (total + per_page - 1) // per_page),
                },
            }
        )
    except APIError as error:
        return format_error_response(error)
    except Exception as exc:
        logger.exception("Failed to list bug reports from database")
        return format_error_response(
            APIError(
                "Failed to list bug reports",
                "BUG_REPORT_LIST_FAILED",
                500,
                {"error": str(exc)},
            )
        )
    except BadRequest as exc:
        # Surface bad pagination or filter inputs to the caller.
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - defensive
        _log_storage_failure("Failed to list bug reports", exc)
        return jsonify({"error": "Failed to list bug reports"}), 500


@bug_reports_bp.route("/api/bug-reports/<report_id>", methods=["GET"])
@require_admin
def get_bug_report(report_id: str):
    """Return full bug report payload for the given report ID."""
    try:
        payload = load_report(report_id, _get_reports_root())
        return jsonify({"report": payload})
    except FileNotFoundError:
        return jsonify({"error": f"Bug report {report_id} not found"}), 404
    except BugReportStorageError as exc:
        _log_storage_failure(f"Failed to load bug report {report_id}", exc)
        return jsonify({"error": "Failed to load bug report"}), 500


@bug_reports_bp.route("/api/bug-reports/<report_id>", methods=["PATCH"])
@require_admin
def update_bug_report(report_id: str):
    """Update bug report metadata such as status or resolution notes."""
    payload = request.get_json(silent=True) or {}
    status = payload.get("status")
    resolution = payload.get("resolution")

    try:
        updated = update_report(
            report_id,
            _get_reports_root(),
            status=status,
            resolution=resolution if isinstance(resolution, dict) else None,
        )
        return jsonify({"report": updated})
    except FileNotFoundError:
        return jsonify({"error": f"Bug report {report_id} not found"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except BugReportStorageError as exc:  # pragma: no cover - defensive
        _log_storage_failure(f"Failed to update bug report {report_id}", exc)
        return jsonify({"error": "Failed to update bug report"}), 500


@bug_reports_bp.route("/api/bug-reports/<report_id>", methods=["DELETE"])
@require_admin
def delete_bug_report_route(report_id: str):
    """Delete a stored bug report."""
    try:
        delete_report(report_id, _get_reports_root())
        return jsonify({"success": True})
    except FileNotFoundError:
        return jsonify({"error": f"Bug report {report_id} not found"}), 404
    except BugReportStorageError as exc:  # pragma: no cover - defensive
        _log_storage_failure(f"Failed to delete bug report {report_id}", exc)
        return jsonify({"error": "Failed to delete bug report"}), 500


@bug_reports_bp.route("/api/bug-reports/purge", methods=["POST"])
@require_admin
def purge_bug_reports():
    """Purge bug reports older than the configured retention period."""
    config = load_config()
    retention_cfg = config.get("bug_reports", {})
    default_days = int(retention_cfg.get("retention_days", 30))

    payload = request.get_json(silent=True) or {}
    days = int(payload.get("older_than_days", default_days))
    if days <= 0:
        return jsonify({"status": "skipped", "reason": "retention-disabled"}), 200

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    dry_run = bool(payload.get("dry_run", False))

    root = _get_reports_root()
    summaries = list_reports(root)
    stats = {
        "matched": sum(
            1 for summary in summaries if summary.submitted_at and summary.submitted_at < cutoff
        )
    }

    if dry_run:
        stats.update(
            {"deleted": 0, "skipped": 0, "cutoff": cutoff.isoformat().replace("+00:00", "Z")}
        )
        return jsonify({"status": "dry_run", "results": stats})

    results = purge_reports_older_than(root, cutoff)
    stats.update(results)
    return jsonify({"status": "success", "results": stats})
