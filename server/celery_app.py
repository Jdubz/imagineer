"""
Celery configuration for async task processing
"""

import os

from celery import Celery


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
    )

    # Configure task routes
    celery.conf.task_routes = {
        "server.tasks.scraping.*": {"queue": "scraping"},
        "server.tasks.training.*": {"queue": "training"},
        "server.tasks.labeling.*": {"queue": "labeling"},
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
