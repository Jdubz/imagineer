"""
Celery configuration for async task processing
"""

import os

from celery import Celery
from celery.schedules import crontab


def make_celery(app=None):
    """Create Celery instance"""
    celery = Celery(
        app.import_name if app else "imagineer",
        backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
        broker=os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    )

    # Configure Celery
    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=30 * 60,  # 30 minutes
        task_soft_time_limit=25 * 60,  # 25 minutes
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        worker_disable_rate_limits=True,
        imports=(
            "server.tasks.labeling",
            "server.tasks.scraping",
            "server.tasks.training",
            "server.tasks.maintenance",
        ),
    )

    # Configure task routes
    celery.conf.task_routes = {
        "server.tasks.scraping.*": {"queue": "scraping"},
        "server.tasks.training.*": {"queue": "training"},
        "server.tasks.labeling.*": {"queue": "labeling"},
        "server.tasks.maintenance.*": {
            "queue": os.environ.get("IMAGINEER_MAINTENANCE_QUEUE", "default")
        },
    }

    purge_training_hour = int(os.environ.get("IMAGINEER_PURGE_TRAINING_HOUR", "3"))
    purge_scrape_hour = int(os.environ.get("IMAGINEER_PURGE_SCRAPE_HOUR", "4"))
    disk_interval_hours = max(1, int(os.environ.get("IMAGINEER_DISK_SAMPLE_HOURS", "6")))

    celery.conf.beat_schedule = {
        "purge-stale-training-artifacts": {
            "task": "server.tasks.training.purge_stale_training_artifacts",
            "schedule": crontab(hour=purge_training_hour, minute=15),
            "options": {"queue": "training"},
        },
        "purge-stale-scrape-artifacts": {
            "task": "server.tasks.scraping.purge_stale_scrape_artifacts",
            "schedule": crontab(hour=purge_scrape_hour, minute=45),
            "options": {"queue": "scraping"},
        },
        "reset-stuck-scrape-jobs": {
            "task": "server.tasks.scraping.reset_stuck_scrape_jobs",
            "schedule": crontab(minute="*/30"),  # Run every 30 minutes
            "options": {"queue": "scraping"},
        },
        "record-disk-usage": {
            "task": "server.tasks.maintenance.record_disk_usage",
            "schedule": crontab(hour=f"*/{disk_interval_hours}", minute=0),
            "options": {"queue": os.environ.get("IMAGINEER_MAINTENANCE_QUEUE", "default")},
        },
    }

    class ContextTask(celery.Task):
        """Make celery tasks work with Flask app context"""

        def __call__(self, *args, **kwargs):
            if app:
                with app.app_context():
                    return self.run(*args, **kwargs)
            else:
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


# Create default celery instance
celery = make_celery()
