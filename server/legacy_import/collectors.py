"""
Collectors for discovering legacy image assets.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from .models import LegacyAlbum, LegacyImageRecord

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
TIMESTAMP_PATTERN = re.compile(
    r"(?P<date>\d{4})(?P<month>\d{2})(?P<day>\d{2})[_-]?"
    r"(?P<hour>\d{2})?(?P<minute>\d{2})?(?P<second>\d{2})?"
)


def collect_legacy_outputs(outputs_root: Path | str) -> List[LegacyImageRecord]:
    """
    Collect legacy assets from the Imagineer outputs directory.
    """

    root = Path(outputs_root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Outputs directory not found: {root}")

    records: List[LegacyImageRecord] = []

    for image_path in sorted(_iter_image_files(root)):
        relative = image_path.relative_to(root)
        album, destination = _resolve_album(relative, image_path)
        if album is None:
            logger.debug("Skipping image outside supported categories: %s", image_path)
            continue

        metadata_path = image_path.with_suffix(".json")
        metadata = _load_metadata(metadata_path)
        created_at = _derive_created_at(image_path, metadata)

        tags = _derive_tags(album, metadata, relative)

        record = LegacyImageRecord(
            source_path=image_path,
            metadata_path=metadata_path if metadata_path.exists() else None,
            destination_path=destination,
            album=album,
            created_at=created_at,
            metadata=metadata,
            tags=tags,
        )
        records.append(record)

    return records


def _iter_image_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        if "thumbnails" in path.parts:
            continue
        yield path


def _load_metadata(metadata_path: Path) -> dict:
    if not metadata_path.exists():
        return {}
    try:
        with metadata_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("Failed to parse metadata %s: %s", metadata_path, exc)
        return {}


def _derive_created_at(image_path: Path, metadata: dict) -> Optional[datetime]:
    timestamp = _extract_timestamp(metadata.get("created_at") or metadata.get("timestamp"))
    if timestamp:
        return timestamp

    timestamp = _extract_timestamp(image_path.stem)
    if timestamp:
        return timestamp

    return datetime.fromtimestamp(image_path.stat().st_mtime, tz=timezone.utc)


def _extract_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    match = TIMESTAMP_PATTERN.search(value)
    if not match:
        return None

    groups = match.groupdict(default="00")
    try:
        return datetime(
            int(groups["date"]),
            int(groups["month"]),
            int(groups["day"]),
            int(groups.get("hour", "00")),
            int(groups.get("minute", "00")),
            int(groups.get("second", "00")),
            tzinfo=timezone.utc,
        )
    except ValueError:
        return None


@dataclass(frozen=True)
class _Resolution:
    album: LegacyAlbum
    destination: Path


def _resolve_album(
    relative: Path, image_path: Path
) -> Tuple[Optional[LegacyAlbum], Optional[Path]]:
    parts = relative.parts
    if not parts:
        return None, None

    if len(parts) == 1:
        return _resolve_singles(parts[0], image_path.name)

    category_root = parts[0]
    remainder = Path(*parts[1:])

    if category_root.startswith("card_deck_") or category_root.startswith("tarot_deck_"):
        return _resolve_deck(category_root, remainder)

    if category_root.startswith("zodiac_"):
        return _resolve_zodiac(category_root, remainder)

    if category_root == "lora_tests":
        return _resolve_lora_tests(remainder)

    # Future categories: uploads/, scraped/ etc.
    return None, None


def _resolve_singles(filename: str, dest_name: str) -> Tuple[LegacyAlbum, Path]:
    timestamp = _extract_timestamp(filename)
    if timestamp:
        bucket = f"{timestamp.year:04d}-{timestamp.month:02d}"
    else:
        bucket = "unknown"

    album_slug = f"legacy-singles-{bucket}"
    album_name = (
        f"Legacy Singles {bucket.capitalize()}" if bucket != "unknown" else "Legacy Singles"
    )
    album = LegacyAlbum(
        slug=album_slug,
        name=album_name,
        album_type="singles",
        description="Imported single-shot generations from legacy outputs/",
    )
    destination = Path("singles") / bucket / dest_name
    return album, destination


def _resolve_deck(folder_name: str, remainder: Path) -> Tuple[LegacyAlbum, Path]:
    slug = folder_name
    album = LegacyAlbum(
        slug=slug,
        name=_humanise_slug(slug),
        album_type="deck",
        description=f"Imported deck batch from outputs/{slug}",
    )
    destination = Path("decks") / slug / remainder
    return album, destination


def _resolve_zodiac(folder_name: str, remainder: Path) -> Tuple[LegacyAlbum, Path]:
    slug = folder_name
    album = LegacyAlbum(
        slug=slug,
        name=f"Zodiac {_humanise_slug(slug.split('_', 1)[-1])}",
        album_type="zodiac",
        description=f"Imported zodiac batch from outputs/{slug}",
    )
    destination = Path("zodiac") / slug / remainder
    return album, destination


def _resolve_lora_tests(remainder: Path) -> Tuple[LegacyAlbum, Path]:
    slug = "lora-tests"
    album = LegacyAlbum(
        slug=slug,
        name="LoRA Experiments",
        album_type="lora-experiment",
        is_training_source=True,
        description="Imported LoRA experiment renders from outputs/lora_tests",
    )
    destination = Path("lora-experiments") / slug / remainder
    return album, destination


def _humanise_slug(slug: str) -> str:
    words = [word for word in re.split(r"[_-]+", slug) if word]
    return " ".join(word.capitalize() if not word.isdigit() else word for word in words)


def _derive_tags(album: LegacyAlbum, metadata: dict, relative: Path) -> Tuple[str, ...]:
    tags = set()
    if album.album_type == "deck":
        stem = relative.stem
        if "_" in stem:
            tags.add(stem.split("_", 1)[1].replace("_", " ").title())
    if album.album_type == "zodiac":
        tags.add(_humanise_slug(relative.stem))
    if "prompt" in metadata:
        prompt = metadata["prompt"]
        if isinstance(prompt, str) and len(prompt) < 160:
            tags.add(prompt.strip())
    return tuple(sorted(t for t in tags if t))
