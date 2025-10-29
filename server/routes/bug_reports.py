"""
Bug report submission endpoint.

Allows admin users to submit detailed bug reports with automatic context capture.
"""

import json
import os
from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, request

from server.auth import require_admin
from server.logging_config import logger
from server.utils.error_handler import APIError, format_error_response

bug_reports_bp = Blueprint("bug_reports", __name__)


def get_bug_reports_dir() -> str:
    """
    Get bug reports directory from config.

    Returns:
        Path to bug reports directory
    """
    try:
        from server.config import get_config

        config = get_config()
        return config.get("bug_reports", {}).get(
            "storage_path", "/mnt/storage/imagineer/bug_reports"
        )
    except Exception:
        # Fallback to environment variable or default
        return os.getenv("BUG_REPORTS_PATH", "/mnt/storage/imagineer/bug_reports")


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
        payload = request.get_json()

        if not payload:
            raise APIError("Request body is required", "MISSING_PAYLOAD", 400)

        if "description" not in payload:
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
            logger.error(
                f"Failed to create bug reports directory: {reports_dir}",
                exc_info=True,
            )
            raise APIError(
                "Failed to create bug reports directory",
                "STORAGE_ERROR",
                500,
                {"directory": reports_dir, "error": str(e)},
            )

        report_path = os.path.join(reports_dir, f"{report_id}.json")

        # Add metadata to report
        report = {
            "report_id": report_id,
            "trace_id": g.trace_id if hasattr(g, "trace_id") else None,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "submitted_by": g.user.email if hasattr(g, "user") else None,
            "user_role": g.user.role if hasattr(g, "user") else None,
            "status": "open",
            **payload,
        }

        # Write to disk
        try:
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2)
        except Exception as e:
            logger.error(
                f"Failed to write bug report to disk: {report_path}",
                exc_info=True,
            )
            raise APIError(
                "Failed to save bug report",
                "WRITE_ERROR",
                500,
                {"path": report_path, "error": str(e)},
            )

        logger.info(
            f"Bug report saved: {report_id}",
            extra={
                "report_id": report_id,
                "trace_id": g.trace_id if hasattr(g, "trace_id") else None,
                "user": g.user.email if hasattr(g, "user") else None,
            },
        )

        return (
            jsonify(
                {
                    "success": True,
                    "report_id": report_id,
                    "trace_id": g.trace_id if hasattr(g, "trace_id") else None,
                    "stored_at": report_path,
                }
            ),
            201,
        )

    except APIError as e:
        return format_error_response(e)
    except Exception:
        logger.error("Unexpected error saving bug report", exc_info=True)
        return format_error_response(
            APIError("Failed to save bug report", "BUG_REPORT_SAVE_FAILED", 500)
        )
