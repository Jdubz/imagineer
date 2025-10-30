"""
Configuration loading utilities shared across the Imagineer backend.

Provides helpers to read and write ``config.yaml`` along with a
fallback configuration that keeps tests and CI environments running
without the file.

The config is cached in memory and automatically invalidated when the
file is modified (via mtime checks). Manual cache clearing is also supported.
"""

from __future__ import annotations

import copy
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)

# Project structure: server/ -> project root lives one directory up.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

# Configuration cache with thread-safe access
_config_cache: Optional[Dict[str, Any]] = None
_config_mtime: Optional[float] = None
_config_lock = threading.Lock()

# Fallback configuration used when config.yaml is missing (e.g. CI).
_DEFAULT_CONFIG: Dict[str, Any] = {
    "model": {
        "default": "runwayml/stable-diffusion-v1-5",
        "alternatives": [
            "stabilityai/stable-diffusion-2-1",
            "stabilityai/stable-diffusion-xl-base-1.0",
        ],
        "cache_dir": "/tmp/imagineer/models",
    },
    "outputs": {
        "base_dir": "/tmp/imagineer/outputs",
        "scraped_dir": "/tmp/imagineer/scraped",
    },
    "generation": {
        "width": 512,
        "height": 512,
        "steps": 30,
        "guidance_scale": 8.0,
        "negative_prompt": (
            "blurry, low quality, low resolution, low detail, poorly drawn, "
            "bad anatomy, bad proportions, bad composition, distorted, deformed, "
            "disfigured, ugly, unattractive, gross, disgusting, mutation, mutated"
        ),
        "batch_size": 1,
        "num_images": 1,
    },
    "output": {
        "directory": "/tmp/imagineer/outputs",
        "format": "png",
        "save_metadata": True,
    },
    "sets": {"directory": "/tmp/imagineer/sets"},
    "training": {
        "learning_rate": 1e-5,
        "max_train_steps": 1000,
        "train_batch_size": 1,
        "gradient_accumulation_steps": 4,
        "checkpoint_dir": "/tmp/imagineer/checkpoints",
        "save_steps": 500,
        "lora": {"rank": 4, "alpha": 32, "dropout": 0.1},
    },
    "dataset": {
        "data_dir": "/tmp/imagineer/data/training",
        "resolution": 512,
        "center_crop": True,
        "random_flip": True,
    },
    "hardware": {
        "device": "auto",
        "mixed_precision": "fp16",
        "enable_attention_slicing": True,
        "enable_vae_slicing": False,
        "enable_xformers": False,
    },
    "bug_reports": {
        "storage_path": "/mnt/storage/imagineer/bug_reports",
        "retention_days": 30,
    },
}


def load_config(*, force_reload: bool = False) -> Dict[str, Any]:
    """
    Load ``config.yaml`` from disk with intelligent caching.

    The configuration is cached in memory and automatically reloaded when
    the file is modified (detected via mtime). This avoids expensive disk
    reads on every request while staying up-to-date with changes.

    Args:
        force_reload: If True, bypass cache and reload from disk

    Returns:
        Configuration dictionary (always a deep copy to prevent mutations)
    """
    global _config_cache, _config_mtime

    with _config_lock:
        global CONFIG_PATH
        override_path: Optional[Path] = None

        env_override = os.environ.get("IMAGINEER_CONFIG_PATH")
        if env_override:
            override_path = Path(env_override)
        else:
            api_module = sys.modules.get("server.api")
            if api_module is not None:
                candidate = getattr(api_module, "CONFIG_PATH", None)
                if candidate:
                    override_path = Path(candidate)

        if override_path and override_path != CONFIG_PATH:
            logger.info("Using configuration override at %s", override_path)
            CONFIG_PATH = override_path
            _config_cache = None
            _config_mtime = None

        # Check if we need to reload from disk
        should_reload = force_reload or _config_cache is None

        if not should_reload and CONFIG_PATH.exists():
            try:
                current_mtime = CONFIG_PATH.stat().st_mtime
                if _config_mtime is None or current_mtime != _config_mtime:
                    should_reload = True
                    logger.info("Config file modified, reloading from disk")
            except OSError as e:
                logger.warning("Failed to check config mtime: %s", e)

        # Load from disk if needed
        if should_reload:
            try:
                with CONFIG_PATH.open("r", encoding="utf-8") as handle:
                    config = yaml.safe_load(handle) or {}
                    _config_cache = config
                    _config_mtime = CONFIG_PATH.stat().st_mtime if CONFIG_PATH.exists() else None
                    logger.debug("Config loaded from disk and cached")
            except FileNotFoundError:
                logger.info("Config file not found at %s, using fallback config", CONFIG_PATH)
                _config_cache = _DEFAULT_CONFIG
                _config_mtime = None
            except Exception as error:  # noqa: BLE001 - intentional broad catch
                logger.warning(
                    "Failed to load config from %s: %s. Using fallback config.",
                    CONFIG_PATH,
                    error,
                    exc_info=True,
                )
                _config_cache = _DEFAULT_CONFIG
                _config_mtime = None

        # Always return a deep copy to prevent external mutations
        return copy.deepcopy(_config_cache)


def save_config(config: Dict[str, Any]) -> None:
    """
    Persist configuration back to ``config.yaml``.

    Automatically clears the cache after saving so the next load_config()
    call will read the fresh configuration from disk.
    """
    with CONFIG_PATH.open("w", encoding="utf-8") as handle:
        yaml.dump(config, handle, default_flow_style=False, sort_keys=False)

    # Clear cache to force reload on next access
    clear_config_cache()
    logger.info("Configuration saved to disk and cache cleared")


def clear_config_cache() -> None:
    """
    Clear the configuration cache, forcing the next load_config() to read from disk.

    This is useful for admins who want to ensure fresh configuration is loaded,
    or for testing scenarios where config needs to be reloaded.
    """
    global _config_cache, _config_mtime

    with _config_lock:
        _config_cache = None
        _config_mtime = None
        logger.info("Configuration cache cleared")


def get_cache_stats() -> Dict[str, Any]:
    """
    Get statistics about the configuration cache for monitoring.

    Returns:
        Dictionary with cache status including:
        - cached: Whether config is currently cached
        - mtime: Last modification time of cached config (if any)
        - config_path: Path to config file
        - file_exists: Whether config file exists on disk
    """
    with _config_lock:
        file_exists = CONFIG_PATH.exists()
        current_mtime = None
        if file_exists:
            try:
                current_mtime = CONFIG_PATH.stat().st_mtime
            except OSError:
                pass

        return {
            "cached": _config_cache is not None,
            "cached_mtime": _config_mtime,
            "file_mtime": current_mtime,
            "config_path": str(CONFIG_PATH),
            "file_exists": file_exists,
            "cache_stale": (
                _config_mtime is not None
                and current_mtime is not None
                and _config_mtime != current_mtime
            ),
        }


__all__ = [
    "CONFIG_PATH",
    "PROJECT_ROOT",
    "load_config",
    "save_config",
    "clear_config_cache",
    "get_cache_stats",
]
