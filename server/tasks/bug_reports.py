"""
Background tasks for bug report maintenance.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from server.celery_app import celery
from server.config_loader import load_config
from server.services import bug_reports as bug_report_service


@celery.task(name="server.tasks.bug_reports.purge_stale_reports")
def purge_stale_reports() -> dict:
    """
    Delete bug reports older than the configured retention window.

    Returns a dictionary with purge statistics.
    """
    from server.api import app  # Imported lazily to avoid circular imports

    with app.app_context():
        config = load_config()
        retention_cfg = config.get("bug_reports", {})
        retention_days = int(retention_cfg.get("retention_days", 30))
        if retention_days <= 0:
            return {"status": "skipped", "reason": "retention-disabled"}

        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        results = bug_report_service.purge_bug_reports(cutoff=cutoff, dry_run=False)
        results["cutoff"] = cutoff.isoformat().replace("+00:00", "Z")
        return {"status": "success", "results": results}
