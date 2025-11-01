"""
Background tasks for bug report maintenance.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from server.bug_reports.storage import purge_reports_older_than
from server.celery_app import celery
from server.config_loader import load_config
from server.routes.bug_reports import get_bug_reports_dir


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
        root = Path(get_bug_reports_dir()).expanduser()
        results = purge_reports_older_than(root, cutoff)
        return {"status": "success", "results": results}
