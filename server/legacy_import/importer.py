"""
Database ingestion helpers for legacy assets.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from sqlalchemy import func, text

from server.database import Album, AlbumImage, Image, MigrationHistory, db, utcnow

from .models import LegacyAlbum, LegacyImageRecord

logger = logging.getLogger(__name__)


@dataclass
class ImportStats:
    created_albums: int = 0
    reused_albums: int = 0
    inserted_images: int = 0
    skipped_images: int = 0
    attached_images: int = 0
    missing_files: int = 0

    def to_json(self) -> str:
        return json.dumps(self.__dict__)


def import_records(
    records: Iterable[LegacyImageRecord],
    staging_root: Path | str,
    *,
    added_by: str = "legacy-importer",
    record_migration: bool = True,
) -> ImportStats:
    """
    Persist staged legacy assets into the Imagineer database.
    """

    stats = ImportStats()
    root = Path(staging_root).expanduser()

    album_cache: dict[str, Album] = {}

    _ensure_album_schema()

    for record in records:
        staged_path = root / record.destination_path
        if not staged_path.exists():
            logger.warning(
                "Skipping legacy image; staged file missing",
                extra={"destination": str(staged_path), "source": str(record.source_path)},
            )
            stats.missing_files += 1
            continue

        album = _get_or_create_album(record.album, album_cache, stats)

        image = _upsert_image(record, staged_path, album)
        if image is None:
            stats.skipped_images += 1
            continue

        stats.inserted_images += 1 if image[1] else 0
        stats.skipped_images += 0 if image[1] else 1
        image_obj = image[0]

        if _attach_to_album(image_obj.id, album.id, added_by):
            stats.attached_images += 1

    db.session.flush()

    if record_migration:
        MigrationHistory.ensure_record(
            "legacy_image_import_stage1",
            details=stats.to_json(),
            refresh_timestamp=True,
        )

    db.session.commit()
    return stats


def _get_or_create_album(
    legacy_album: LegacyAlbum, cache: dict[str, Album], stats: ImportStats
) -> Album:
    album = cache.get(legacy_album.slug)
    if album:
        stats.reused_albums += 1
        return album

    album = Album.query.filter_by(
        name=legacy_album.name, album_type=legacy_album.album_type
    ).one_or_none()
    if album:
        cache[legacy_album.slug] = album
        stats.reused_albums += 1
        return album

    album = Album(
        name=legacy_album.name,
        album_type=legacy_album.album_type,
        description=legacy_album.description,
        is_public=legacy_album.is_public,
        is_training_source=legacy_album.is_training_source,
        created_by="legacy-importer",
        generation_config=json.dumps({"legacy_slug": legacy_album.slug}),
    )
    db.session.add(album)
    db.session.flush()
    cache[legacy_album.slug] = album
    stats.created_albums += 1
    return album


def _ensure_album_schema() -> None:
    engine = db.session.get_bind()
    with engine.connect() as conn:
        existing_columns = {row[1] for row in conn.execute(text("PRAGMA table_info(albums)"))}
    required_columns = [
        ("is_set_template", "BOOLEAN", "0"),
        ("csv_data", "TEXT", None),
        ("base_prompt", "TEXT", None),
        ("prompt_template", "TEXT", None),
        ("style_suffix", "TEXT", None),
        ("example_theme", "TEXT", None),
        ("lora_config", "TEXT", None),
    ]
    for name, column_type, default in required_columns:
        if name in existing_columns:
            continue
        default_clause = ""
        if default is not None:
            default_clause = f" DEFAULT {default}"
        with engine.begin() as ddl_conn:
            ddl_conn.execute(
                text(f"ALTER TABLE albums ADD COLUMN {name} {column_type}{default_clause}")
            )


def _sanitize_filename(record: LegacyImageRecord) -> str:
    candidate = record.destination_path.as_posix().replace("/", "__")
    if len(candidate) <= 255:
        return candidate
    return candidate[-255:]


def _upsert_image(
    record: LegacyImageRecord, staged_path: Path, album: Album
) -> tuple[Image, bool] | None:
    existing = Image.query.filter_by(file_path=str(staged_path)).one_or_none()
    if existing:
        return existing, False

    metadata = record.metadata or {}
    image = Image(
        filename=_sanitize_filename(record),
        file_path=str(staged_path),
        prompt=metadata.get("prompt"),
        negative_prompt=metadata.get("negative_prompt"),
        seed=_safe_int(metadata.get("seed")),
        steps=_safe_int(metadata.get("steps")),
        guidance_scale=_safe_float(metadata.get("guidance_scale")),
        width=_safe_int(metadata.get("width")),
        height=_safe_int(metadata.get("height")),
        lora_config=json.dumps(metadata.get("lora")) if metadata.get("lora") else None,
        is_public=album.is_public,
        created_at=record.created_at or utcnow(),
    )
    db.session.add(image)
    db.session.flush()
    return image, True


def _attach_to_album(image_id: int, album_id: int, added_by: str) -> bool:
    association = AlbumImage.query.filter_by(album_id=album_id, image_id=image_id).one_or_none()
    if association:
        return False

    sort_order = (
        db.session.query(func.max(AlbumImage.sort_order)).filter_by(album_id=album_id).scalar() or 0
    ) + 1
    association = AlbumImage(
        album_id=album_id,
        image_id=image_id,
        sort_order=sort_order,
        added_by=added_by,
    )
    db.session.add(association)
    return True


def _safe_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
