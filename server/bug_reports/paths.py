"""Utilities for resolving bug report storage paths."""

from __future__ import annotations

import logging
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable, Optional

from flask import current_app

from server.config_loader import load_config

logger = logging.getLogger(__name__)

_DEFAULT_STORAGE_PATH = Path("/mnt/storage/imagineer/bug_reports")


def _resolve_app_root() -> Optional[Path]:
    try:
        app = current_app._get_current_object()
    except RuntimeError:
        return None

    override = app.config.get("BUG_REPORTS_PATH")
    if override:
        return Path(override).expanduser()

    if app.testing:
        storage_map = app.config.setdefault("_BUG_REPORTS_TEST_STORAGE_ROOTS", {})
        test_id = os.environ.get("PYTEST_CURRENT_TEST", "")
        test_slug = (
            re.sub(r"[^a-zA-Z0-9._-]+", "_", test_id.split(" ")[0]) if test_id else "default"
        )
        worker = os.environ.get("PYTEST_XDIST_WORKER", "master")
        key = f"{worker}:{test_slug}"

        cached_path = storage_map.get(key)
        if cached_path:
            return Path(cached_path).expanduser()

        root = Path(tempfile.gettempdir()) / "imagineer_bug_reports" / worker / test_slug
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        storage_map[key] = str(root)
        return root

    return None


def resolve_storage_root(config_loader: Optional[Callable[[], Any]] = None) -> Path:
    """Determine where bug reports should be stored."""
    env_override = os.getenv("BUG_REPORTS_PATH")
    if env_override:
        return Path(env_override).expanduser()

    app_root = _resolve_app_root()
    if app_root is not None:
        return app_root

    loader = config_loader or load_config
    try:
        config = loader() or {}
        storage_path = config.get("bug_reports", {}).get("storage_path")
        if storage_path:
            return Path(storage_path).expanduser()
    except Exception:
        logger.warning("Falling back to default bug report directory", exc_info=True)

    return _DEFAULT_STORAGE_PATH.expanduser()
