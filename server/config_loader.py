"""
Configuration loading utilities shared across the Imagineer backend.

Provides helpers to read and write ``config.yaml`` along with a
fallback configuration that keeps tests and CI environments running
without the file.
"""

from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any, Dict

import yaml

logger = logging.getLogger(__name__)

# Project structure: server/ -> project root lives one directory up.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

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


def load_config() -> Dict[str, Any]:
    """Load ``config.yaml`` from disk, falling back to defaults when missing or on error."""
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle) or {}
            return config
    except FileNotFoundError:
        logger.info("Config file not found at %s, using fallback config", CONFIG_PATH)
    except Exception as error:  # noqa: BLE001 - intentional broad catch for resilience
        logger.warning(
            "Failed to load config from %s: %s. Using fallback config.",
            CONFIG_PATH,
            error,
            exc_info=True,
        )
    return copy.deepcopy(_DEFAULT_CONFIG)


def save_config(config: Dict[str, Any]) -> None:
    """Persist configuration back to ``config.yaml``."""
    with CONFIG_PATH.open("w", encoding="utf-8") as handle:
        yaml.dump(config, handle, default_flow_style=False, sort_keys=False)


__all__ = ["CONFIG_PATH", "PROJECT_ROOT", "load_config", "save_config"]
