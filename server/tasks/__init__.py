"""
Celery task package initializer.

Importing the submodules at package import time guarantees the tasks are
registered with the shared Celery instance, regardless of whether the worker
is started via `server.api` or directly through `celery -A server.celery_app`.
"""

# Import task modules so Celery discovers task definitions on import.
from . import bug_reports, labeling, scraping, training  # noqa: F401

__all__ = ["bug_reports", "labeling", "scraping", "training"]
