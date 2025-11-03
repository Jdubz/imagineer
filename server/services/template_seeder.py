"""
Utility to ensure default batch templates are present in the database.

The production bug report highlighted that brand-new deployments were missing
the legacy batch templates (Card Deck, Zodiac, Tarot). This module loads the
authoritative template definitions from ``data/sets/config.yaml`` and creates
or refreshes the corresponding ``Album`` rows with ``is_set_template=True``.

The seeding routine is idempotent and safe to call on every startup.
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml
from flask import current_app

from server.database import Album, MigrationHistory, db

LOGGER = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CONFIG_PATHS: tuple[Path, ...] = (
    PROJECT_ROOT / "data" / "sets" / "config.yaml",
    PROJECT_ROOT / "config" / "deployment" / "sets" / "config.yaml",
)
MIGRATION_NAME = "seed_default_set_templates_v1"


@dataclass(frozen=True)
class TemplateDefinition:
    """Parsed template configuration paired with CSV rows."""

    key: str
    config: dict[str, Any]
    rows: list[dict[str, Any]]

    @property
    def name(self) -> str:
        value = self.config.get("name")
        if isinstance(value, str) and value.strip():
            return value.strip()
        return self.key.replace("_", " ").title()

    @property
    def description(self) -> str | None:
        value = self.config.get("description")
        return value.strip() if isinstance(value, str) and value.strip() else None

    @property
    def generation_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "slug": self.key,
            "base_prompt": self.config.get("base_prompt"),
            "prompt_template": self.config.get("prompt_template"),
            "style_suffix": self.config.get("style_suffix"),
            "example_theme": self.config.get("example_theme"),
        }
        width = self.config.get("width")
        height = self.config.get("height")
        negative_prompt = self.config.get("negative_prompt")
        if isinstance(width, int):
            payload["width"] = width
        if isinstance(height, int):
            payload["height"] = height
        if isinstance(negative_prompt, str) and negative_prompt.strip():
            payload["negative_prompt"] = negative_prompt.strip()
        return {key: value for key, value in payload.items() if value is not None}

    @property
    def lora_payload(self) -> str | None:
        loras = self.config.get("loras")
        if isinstance(loras, Iterable):
            lora_list = [entry for entry in loras if isinstance(entry, dict)]
            if lora_list:
                return json.dumps(lora_list)
        return None


def _load_sets_config(config_path: Path) -> dict[str, Any]:
    """Return a configuration mapping for a specific path."""

    try:
        with config_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
            if isinstance(data, dict):
                LOGGER.debug("Loaded set templates from %s", config_path)
                return data
            LOGGER.warning("Template config at %s is not a mapping; skipping", config_path)
    except (yaml.YAMLError, OSError) as exc:  # pragma: no cover - defensive logging
        LOGGER.error("Failed to read template config %s: %s", config_path, exc)
    return {}


def _load_csv_rows(
    config_path: Path, entry_key: str, entry_config: dict[str, Any]
) -> list[dict[str, Any]]:
    """Load CSV rows associated with a template definition."""

    csv_path_value = entry_config.get("csv_path")
    if isinstance(csv_path_value, str):
        csv_path = Path(csv_path_value)
        if not csv_path.is_absolute():
            csv_path = (config_path.parent / csv_path).resolve()
    else:
        csv_path = (config_path.parent / f"{entry_key}.csv").resolve()

    if not csv_path.exists():
        LOGGER.warning("CSV for template %s is missing: %s", entry_key, csv_path)
        return []

    try:
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return [row for row in reader]
    except (OSError, csv.Error) as exc:  # pragma: no cover - logged for observability
        LOGGER.error("Failed to read CSV %s for template %s: %s", csv_path, entry_key, exc)
        return []


def _collect_definitions() -> list[TemplateDefinition]:
    """Assemble template definitions from YAML + CSV data."""

    for candidate in DEFAULT_CONFIG_PATHS:
        if not candidate.exists():
            continue

        config = _load_sets_config(candidate)
        if not config:
            continue

        definitions: list[TemplateDefinition] = []
        for key, raw_config in config.items():
            if not isinstance(raw_config, dict):
                LOGGER.warning("Skipping template %s because config is not a mapping", key)
                continue
            rows = _load_csv_rows(candidate, key, raw_config)
            definitions.append(TemplateDefinition(key=key, config=raw_config, rows=rows))
        return definitions

    LOGGER.warning("No template configuration found in any default location")
    return []


def ensure_default_set_templates(app=None) -> dict[str, list[str]]:
    """
    Create or refresh the default set templates.

    Returns a summary dictionary containing the templates that were created or updated.
    """

    flask_app = app or current_app._get_current_object()  # type: ignore[attr-defined]
    created: list[str] = []
    updated: list[str] = []
    skipped: list[str] = []

    definitions = _collect_definitions()
    if not definitions:
        LOGGER.warning("Unable to seed default templates because no definitions were loaded")
        return {"created": created, "updated": updated, "skipped": skipped}

    with flask_app.app_context():
        for definition in definitions:
            if not definition.rows:
                skipped.append(definition.name)
                continue

            csv_payload = json.dumps(definition.rows)
            generation_payload = json.dumps(definition.generation_payload, sort_keys=True)

            album = (
                Album.query.filter(
                    Album.is_set_template.is_(True),
                    Album.name == definition.name,
                )
                .order_by(Album.id.asc())
                .first()
            )

            if album:
                album.description = definition.description
                album.album_type = definition.config.get("album_type", "set")
                album.is_public = bool(definition.config.get("is_public", True))
                album.is_training_source = bool(definition.config.get("is_training_source", False))
                album.created_by = (
                    definition.config.get("created_by") or album.created_by or "system"
                )
                album.generation_prompt = definition.config.get("base_prompt")
                album.generation_config = generation_payload
                album.is_set_template = True
                album.csv_data = csv_payload
                album.base_prompt = definition.config.get("base_prompt")
                album.prompt_template = definition.config.get("prompt_template")
                album.style_suffix = definition.config.get("style_suffix")
                album.example_theme = definition.config.get("example_theme")
                album.lora_config = definition.lora_payload
                updated.append(definition.name)
            else:
                album = Album(
                    name=definition.name,
                    description=definition.description,
                    album_type=definition.config.get("album_type", "set"),
                    is_public=bool(definition.config.get("is_public", True)),
                    is_training_source=bool(definition.config.get("is_training_source", False)),
                    created_by=definition.config.get("created_by") or "system",
                    generation_prompt=definition.config.get("base_prompt"),
                    generation_config=generation_payload,
                    is_set_template=True,
                    csv_data=csv_payload,
                    base_prompt=definition.config.get("base_prompt"),
                    prompt_template=definition.config.get("prompt_template"),
                    style_suffix=definition.config.get("style_suffix"),
                    example_theme=definition.config.get("example_theme"),
                    lora_config=definition.lora_payload,
                )
                db.session.add(album)
                created.append(definition.name)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        details = json.dumps(
            {
                "created": created,
                "updated": updated,
                "skipped": skipped,
            },
            sort_keys=True,
        )

        try:
            MigrationHistory.ensure_record(MIGRATION_NAME, details=details, refresh_timestamp=True)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    if created or updated:
        LOGGER.info(
            "Default set templates ensured (created=%s, updated=%s, skipped=%s)",
            created,
            updated,
            skipped,
        )
    else:
        LOGGER.info("No changes made while ensuring default set templates")

    return {"created": created, "updated": updated, "skipped": skipped}


__all__ = ["ensure_default_set_templates", "MIGRATION_NAME"]
