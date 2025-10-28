"""
Compatibility layer for AI labeling services.

Historically the codebase exposed helpers from ``server.services.labeling``.
The implementation now lives in ``labeling_cli`` but several tests (and likely
external integrations) still import from the legacy module path.  Re-exporting
the helpers keeps the public API stable while the underlying implementation
continues to use the Docker-based Claude CLI.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from . import labeling_cli as _labeling_cli


def label_image_with_claude(image_path: str, prompt_type: str = "default") -> Dict[str, Any]:
    """
    Backwards-compatible wrapper around :func:`labeling_cli.label_image_with_claude`.
    """

    return _labeling_cli.label_image_with_claude(image_path=image_path, prompt_type=prompt_type)


def batch_label_images(
    image_paths: Iterable[str],
    prompt_type: str = "default",
    progress_callback: Optional[callable] = None,
) -> Dict[str, Any]:
    """
    Backwards-compatible wrapper around :func:`labeling_cli.batch_label_images`.
    """

    return _labeling_cli.batch_label_images(
        image_paths=image_paths, prompt_type=prompt_type, progress_callback=progress_callback
    )
