"""
Helpers for calculating disk usage and directory sizes.
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from server.config_loader import load_config

DEFAULT_ALERT_THRESHOLD = int(os.environ.get("IMAGINEER_DISK_ALERT_PERCENT", "85"))


def get_disk_usage(path: str | Path) -> dict[str, float | int]:
    """Return disk usage metrics for the filesystem containing ``path``."""
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Path does not exist: {target}")

    stat = os.statvfs(target)
    total = stat.f_frsize * stat.f_blocks
    free = stat.f_frsize * stat.f_bavail
    used = total - free
    percent_used = (used / total * 100) if total else 0.0

    return {
        "path": str(target),
        "total_bytes": total,
        "used_bytes": used,
        "free_bytes": free,
        "percent_used": round(percent_used, 2),
    }


def _du_size(path: Path) -> int:
    """Try to use `du -sb` for fast directory sizing."""
    try:
        result = subprocess.run(
            ["du", "-sb", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        size_str = result.stdout.split()[0]
        return int(size_str)
    except Exception:
        return _walk_size(path)


def _walk_size(path: Path) -> int:
    """Fallback directory walk to compute size in bytes."""
    total = 0
    for root, dirs, files in os.walk(path, onerror=lambda _: None):
        for name in files:
            try:
                fp = Path(root) / name
                total += fp.stat().st_size
            except FileNotFoundError:
                continue
    return total


def get_directory_sizes(base_path: str | Path, subdirs: Iterable[str]) -> dict[str, int]:
    """Return byte sizes for the provided subdirectories."""
    base = Path(base_path)
    sizes: dict[str, int] = {}
    for subdir in subdirs:
        target = (base / subdir).resolve()
        if target.exists():
            sizes[str(subdir)] = _du_size(target)
        else:
            sizes[str(subdir)] = 0
    return sizes


def _path_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return _du_size(path)


def collect_disk_statistics() -> dict[str, object]:
    """Collect disk usage snapshots for key Imagineer directories."""
    config = load_config()

    targets: list[dict[str, object]] = []

    def add_target(label: str, path: str | None):
        if not path:
            return
        p = Path(path)
        targets.append({"label": label, "path": str(p.resolve())})

    add_target("model_cache", config.get("model", {}).get("cache_dir"))
    outputs_cfg = config.get("outputs", {})
    add_target("generation_outputs", outputs_cfg.get("base_dir"))
    add_target("scraped_outputs", outputs_cfg.get("scraped_dir"))
    add_target("training_checkpoints", config.get("training", {}).get("checkpoint_dir"))
    add_target("training_dataset", config.get("dataset", {}).get("data_dir"))
    add_target("bug_reports", config.get("bug_reports", {}).get("storage_path"))

    volumes: list[dict[str, object]] = []
    alerts: list[dict[str, object]] = []

    for target in targets:
        path = Path(target["path"])
        if not path.exists():
            volumes.append(
                {
                    "label": target["label"],
                    "path": target["path"],
                    "exists": False,
                }
            )
            continue

        usage = get_disk_usage(path)
        size_bytes = _path_size(path)
        entry = {
            "label": target["label"],
            "path": target["path"],
            "exists": True,
            "usage": usage,
            "size_bytes": size_bytes,
        }
        volumes.append(entry)

        if usage["percent_used"] >= DEFAULT_ALERT_THRESHOLD:
            alerts.append(
                {
                    "type": "capacity",
                    "path": usage["path"],
                    "percent_used": usage["percent_used"],
                    "threshold_percent": DEFAULT_ALERT_THRESHOLD,
                }
            )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "volumes": volumes,
        "alerts": alerts,
        "threshold_percent": DEFAULT_ALERT_THRESHOLD,
    }
