"""
Background maintenance tasks for housekeeping and observability.
"""

from __future__ import annotations

import logging

from server.celery_app import celery
from server.utils.disk_stats import collect_disk_statistics

logger = logging.getLogger(__name__)


@celery.task(name="server.tasks.maintenance.record_disk_usage")
def record_disk_usage():
    """
    Capture disk usage snapshot for operational visibility.

    Returns:
        dict: Snapshot payload used for dashboarding and alerting.
    """

    snapshot = collect_disk_statistics()
    logger.info("maintenance.disk_usage", extra={"snapshot": snapshot})

    for alert in snapshot.get("alerts", []):
        logger.warning("maintenance.disk_usage.alert", extra={"alert": alert})

    return snapshot
