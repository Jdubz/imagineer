"""
Utilities for staging legacy assets into the repository.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml

from .models import LegacyImageRecord

logger = logging.getLogger(__name__)


@dataclass
class StageSummary:
    copied: int = 0
    skipped: int = 0
    metadata_copied: int = 0


def stage_records(
    records: Iterable[LegacyImageRecord],
    staging_root: Path | str,
    *,
    copy_metadata: bool = True,
    use_symlinks: bool = True,
) -> StageSummary:
    """
    Stage assets into the canonical `data/legacy` tree.
    """

    root = Path(staging_root).expanduser()
    root.mkdir(parents=True, exist_ok=True)

    summary = StageSummary()

    for record in records:
        dest_path = root / record.destination_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        if dest_path.exists():
            summary.skipped += 1
        else:
            if use_symlinks:
                os.symlink(record.source_path, dest_path)
            else:
                shutil.copy2(record.source_path, dest_path)
            summary.copied += 1

        if copy_metadata and record.metadata_path:
            dest_metadata = dest_path.with_suffix(".json")
            if dest_metadata.exists():
                continue
            shutil.copy2(record.metadata_path, dest_metadata)
            summary.metadata_copied += 1

    return summary


def write_manifest(records: Iterable[LegacyImageRecord], manifest_path: Path | str) -> None:
    """
    Persist a manifest describing the staged assets.
    """

    manifest_entries = [record.manifest_entry() for record in records]
    path = Path(manifest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(manifest_entries, fh, sort_keys=False)


def write_summary(summary: StageSummary, output_path: Path | str) -> None:
    """
    Write a small JSON summary file describing the staging results.
    """

    payload = {
        "copied": summary.copied,
        "skipped": summary.skipped,
        "metadata_copied": summary.metadata_copied,
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
