#!/usr/bin/env python3
"""Migrate legacy image storage into album-scoped directories."""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.orm import joinedload  # noqa: E402

from server.api import app  # noqa: E402
from server.config_loader import load_config  # noqa: E402
from server.database import Album, AlbumImage, db  # noqa: E402

LOGGER = logging.getLogger("migrate_media_to_albums")


def _resolve_path(raw_path: str, *, outputs_root: Path) -> Path | None:
    """Return concrete path for an image entry, handling legacy relative paths."""
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / raw_path
    if candidate.exists():
        return candidate

    # Fallback: image may already live directly in outputs with filename only.
    filename = Path(raw_path).name
    fallback = outputs_root / filename
    if fallback.exists():
        return fallback

    return None


def _ensure_directory(path: Path, *, dry_run: bool) -> None:
    if dry_run:
        return
    path.mkdir(parents=True, exist_ok=True)


def _move_sidecar(source: Path, destination: Path, *, dry_run: bool) -> None:
    """Move accompanying metadata sidecars when present."""
    if not source.suffix:
        return
    sidecar = source.with_suffix(".json")
    if not sidecar.exists():
        return

    dest_sidecar = destination.with_suffix(".json")
    if dest_sidecar.exists():
        LOGGER.debug("Metadata already present at %s", str(dest_sidecar))
        if not dry_run:
            try:
                sidecar.unlink()
            except OSError:
                pass
        return

    if dry_run:
        LOGGER.info("Would move metadata %s -> %s", str(sidecar), str(dest_sidecar))
        return

    dest_sidecar.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(sidecar), str(dest_sidecar))


def migrate_media(*, dry_run: bool = False, prune_legacy_symlinks: bool = True) -> dict[str, int]:
    config = load_config()
    outputs_root = Path(
        config.get("outputs", {}).get("base_dir", "/tmp/imagineer/outputs")
    ).resolve()
    albums_root = outputs_root / "albums"
    _ensure_directory(albums_root, dry_run=dry_run)

    stats = defaultdict(int)
    processed_images: set[int] = set()

    albums: Iterable[Album] = (
        Album.query.options(joinedload(Album.album_images).joinedload(AlbumImage.image))
        .order_by(Album.created_at.asc())
        .all()
    )

    for album in albums:
        dest_dir = albums_root / album.slug
        _ensure_directory(dest_dir, dry_run=dry_run)

        for association in sorted(
            album.album_images, key=lambda assoc: (assoc.sort_order or 0, assoc.id)
        ):
            image = association.image
            if image is None or image.id in processed_images:
                continue

            processed_images.add(image.id)
            current_entry = image.file_path
            if not current_entry:
                LOGGER.warning("Image %s has no file_path stored; skipping", image.id)
                stats["missing_path"] += 1
                continue

            legacy_path = _resolve_path(current_entry, outputs_root=outputs_root)
            if legacy_path is None or not legacy_path.exists():
                LOGGER.error("Image %s missing on disk: %s", image.id, current_entry)
                stats["missing_files"] += 1
                continue

            resolved_source = legacy_path.resolve()
            destination_path = (dest_dir / image.filename).resolve()

            if destination_path == resolved_source:
                LOGGER.debug("Image %s already in destination %s", image.id, str(destination_path))
            else:
                if destination_path.exists():
                    LOGGER.info(
                        "Destination already exists for image %s (%s); assuming migrated",
                        image.id,
                        str(destination_path),
                    )
                else:
                    if dry_run:
                        LOGGER.info(
                            "Would move %s -> %s", str(resolved_source), str(destination_path)
                        )
                    else:
                        destination_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(resolved_source), str(destination_path))
                        stats["moved"] += 1

                _move_sidecar(resolved_source, destination_path, dry_run=dry_run)

            new_file_path = str(destination_path)
            if image.file_path != new_file_path:
                LOGGER.debug(
                    "Updating DB path for image %s: %s -> %s",
                    image.id,
                    image.file_path,
                    new_file_path,
                )
                if not dry_run:
                    image.file_path = new_file_path
                stats["updated_records"] += 1

            if prune_legacy_symlinks and not dry_run and legacy_path != destination_path:
                try:
                    if legacy_path.is_symlink():
                        legacy_path.unlink()
                        stats["symlinks_removed"] += 1
                    elif legacy_path.is_file():
                        pass
                except OSError as exc:
                    LOGGER.warning("Failed to remove legacy entry %s: %s", str(legacy_path), exc)

    if not dry_run:
        db.session.commit()

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Move legacy Imagineer media into album-specific directories."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Perform checks without moving files"
    )
    parser.add_argument(
        "--keep-legacy-symlinks",
        action="store_true",
        help="Retain legacy data/legacy symlinks instead of pruning them",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    with app.app_context():
        stats = migrate_media(
            dry_run=args.dry_run, prune_legacy_symlinks=not args.keep_legacy_symlinks
        )

    LOGGER.info("Migration summary:")
    for key, value in sorted(stats.items()):
        LOGGER.info("  %s: %s", key, value)


if __name__ == "__main__":
    main()
