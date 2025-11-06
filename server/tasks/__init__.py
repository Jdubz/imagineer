"""Celery task package initializer with lazy submodule loading.

Historically this package imported every task module eagerly so the Celery app
would register the tasks during import. That approach created a circular-import
loop once the scraping tasks began importing ``server.api`` (which itself
imports task modules). The eager import caused the package to be "partially
initialised" when Celery attempted to load ``server.tasks.scraping`` during
worker start-up, crashing the workers in a tight loop.

To avoid that, we now lazily populate task submodules on first access. Celery
still imports the individual modules explicitly (see
``server.celery_app.make_celery``), so task registration behaviour is
unchanged, but the package no longer triggers the circular import at module
import time.
"""

from importlib import import_module
from types import ModuleType
from typing import List

__all__ = ["bug_reports", "images", "labeling", "maintenance", "scraping", "training"]


def __getattr__(name: str) -> ModuleType:
    """Dynamically import task submodules when accessed."""
    if name in __all__:
        module = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__() -> List[str]:
    """Ensure ``dir(server.tasks)`` lists lazily imported members."""
    return sorted(set(__all__ + list(globals().keys())))
