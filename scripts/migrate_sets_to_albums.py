#!/usr/bin/env python3
"""Import legacy CSV-based set templates into database albums."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Iterable

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.api import app  # noqa: E402
from server.config_loader import load_config  # noqa: E402
from server.database import Album, MigrationHistory, db  # noqa: E402

LOGGER = logging.getLogger("migrate_sets_to_albums")
MIGRATION_NAME = "sets_to_albums_v1"


def _get_default_sets_root() -> Path:
    """Get the sets directory from config.yaml or fallback to /tmp."""
    config = load_config()
    sets_dir = config.get("sets", {}).get("directory", "/tmp/imagineer/sets")
    return Path(sets_dir)


def _resolve_config_path(root: Path) -> Path | None:
    """Return the first existing config path from a set of fallbacks."""

    candidates: Iterable[Path] = (
        root / "config.yaml",
        Path("data/sets/config.yaml"),
        Path("config/deployment/sets/config.yaml"),
    )

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _load_sets_config(config_path: Path) -> Dict[str, Any]:
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
            if not isinstance(data, dict):
                LOGGER.error("Sets config at %s is not a mapping", config_path)
                return {}
            return data
    except yaml.YAMLError as exc:  # pragma: no cover - defensive logging
        LOGGER.error("Failed to parse %s: %s", config_path, exc)
    except OSError as exc:  # pragma: no cover
        LOGGER.error("Unable to read %s: %s", config_path, exc)
    return {}


def _load_csv_items(csv_path: Path) -> list[dict[str, Any]]:
    if not csv_path.exists():
        LOGGER.warning("CSV file missing: %s", csv_path)
        return []

    try:
        with csv_path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            return [row for row in reader]
    except (OSError, csv.Error) as exc:  # pragma: no cover - logged for ops
        LOGGER.error("Failed to read CSV %s: %s", csv_path, exc)
        return []


def _ensure_album(
    set_id: str,
    config: Dict[str, Any],
    csv_items: list[dict[str, Any]],
    *,
    dry_run: bool,
) -> None:
    """Create or update the album that represents a legacy set."""

    name = config.get("name") or set_id.replace("_", " ").title()
    description = config.get("description", "")
    album_type = config.get("album_type") or "set"
    created_by = config.get("created_by") or "system"

    # Handle generation_config field - preserves modern config or creates legacy fallback
    # Modern sets have a 'generation_config' dict in config.yaml with model settings
    # Legacy sets don't have this field, so we create a minimal config with just the
    # legacy_slug identifier to maintain backwards compatibility with older generation code
    generation_config = config.get("generation_config")
    if isinstance(generation_config, dict):
        generation_config_json = json.dumps(generation_config)
    else:
        # Legacy fallback: create minimal config with slug for old set templates
        legacy_slug = config.get("legacy_slug") or set_id
        generation_config_json = json.dumps({"legacy_slug": legacy_slug})

    loras = config.get("loras") or []
    if not isinstance(loras, list):
        loras = []

    csv_payload = json.dumps(csv_items)
    lora_payload = json.dumps(loras)

    existing = Album.query.filter_by(name=name).one_or_none()
    if existing:
        LOGGER.info("Updating existing album %s (id=%s)", name, existing.id)
        if dry_run:
            return

        existing.album_type = album_type
        existing.description = description
        existing.is_set_template = True
        existing.csv_data = csv_payload
        existing.base_prompt = config.get("base_prompt")
        existing.prompt_template = config.get("prompt_template")
        existing.style_suffix = config.get("style_suffix")
        existing.example_theme = config.get("example_theme")
        existing.lora_config = lora_payload
        existing.generation_prompt = config.get("base_prompt")
        existing.generation_config = generation_config_json
        existing.is_public = config.get("is_public", True)
        existing.is_training_source = config.get("is_training_source", False)
        existing.created_by = created_by
    else:
        LOGGER.info(
            "Creating new album %s with %d template items",
            name,
            len(csv_items),
        )
        if dry_run:
            return

        album = Album(
            name=name,
            description=description,
            album_type=album_type,
            is_public=config.get("is_public", True),
            is_training_source=config.get("is_training_source", False),
            created_by=created_by,
            generation_prompt=config.get("base_prompt"),
            generation_config=generation_config_json,
            is_set_template=True,
            csv_data=csv_payload,
            base_prompt=config.get("base_prompt"),
            prompt_template=config.get("prompt_template"),
            style_suffix=config.get("style_suffix"),
            example_theme=config.get("example_theme"),
            lora_config=lora_payload,
        )
        db.session.add(album)


def migrate_sets_to_albums(sets_root: Path, *, dry_run: bool = False) -> int:
    if not sets_root.exists():
        LOGGER.error("Sets directory does not exist: %s", sets_root)
        return 0

    config_path = _resolve_config_path(sets_root)
    if not config_path:
        LOGGER.error(
            "No sets config found. Checked %s, data/sets/config.yaml, and "
            "config/deployment/sets/config.yaml",
            sets_root / "config.yaml",
        )
        return 0

    sets_config = _load_sets_config(config_path)
    if not sets_config:
        LOGGER.warning("Sets config at %s is empty; nothing to migrate", config_path)
        return 0

    migrated = 0
    for set_id, set_config in sets_config.items():
        if not isinstance(set_config, dict):
            LOGGER.warning("Skipping set %s because config is not a mapping", set_id)
            continue

        csv_relative = set_config.get("csv_path")
        csv_path = None
        if isinstance(csv_relative, str):
            candidate = Path(csv_relative)
            csv_path = candidate if candidate.is_absolute() else (sets_root / candidate)
        if not csv_path:
            csv_path = sets_root / f"{set_id}.csv"

        csv_items = _load_csv_items(csv_path)
        if not csv_items:
            LOGGER.warning("No CSV rows found for set %s; continuing", set_id)

        _ensure_album(set_id, set_config, csv_items, dry_run=dry_run)
        migrated += 1

    if dry_run:
        LOGGER.info("Dry-run complete; no database changes were committed")
        db.session.rollback()
        return migrated

    MigrationHistory.ensure_record(
        MIGRATION_NAME,
        details=json.dumps(
            {
                "config": str(config_path),
                "sets_processed": migrated,
            }
        ),
    )
    db.session.commit()
    LOGGER.info("Migration complete. Processed %d set definitions", migrated)
    return migrated


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sets-dir",
        type=Path,
        default=_get_default_sets_root(),
        help=(
            "Root directory containing legacy set CSVs and config.yaml "
            "(default: from config.yaml)"
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Run without committing changes")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run migration even if migration_history already records it",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    with app.app_context():
        if not args.force and MigrationHistory.has_run(MIGRATION_NAME):
            LOGGER.info("Migration %s already recorded; exiting", MIGRATION_NAME)
            return 0

        try:
            migrate_sets_to_albums(args.sets_dir, dry_run=args.dry_run)
        except Exception as exc:  # pragma: no cover - guard unexpected failures
            LOGGER.exception("Migration failed: %s", exc)
            db.session.rollback()
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
