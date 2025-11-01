"""
Data models used during legacy image import.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


@dataclass(frozen=True)
class LegacyAlbum:
    """
    Normalised representation of a target album for legacy assets.

    Attributes:
        slug: Stable slug used to look up or create the album.
        name: Human friendly name surfaced in the UI.
        album_type: "singles", "deck", "zodiac", "lora-experiment", "reference-pack".
        is_public: Whether the album should be public after ingestion.
        is_training_source: Whether the album should be marked as training source.
        description: Optional descriptive copy for provenance.
    """

    slug: str
    name: str
    album_type: str
    is_public: bool = True
    is_training_source: bool = False
    description: Optional[str] = None


@dataclass(frozen=True)
class LegacyImageRecord:
    """
    Represents a single legacy asset discovered by the collectors.

    Attributes:
        source_path: Absolute path of the original asset.
        metadata_path: Optional path to a JSON sidecar.
        destination_path: Relative path (within staging area) for the asset.
        album: Target album metadata.
        created_at: Timestamp parsed from file name or filesystem metadata.
        metadata: Parsed key/value metadata (prompt, config, etc).
        tags: Optional list of free-form tags derived from context.
    """

    source_path: Path
    metadata_path: Optional[Path]
    destination_path: Path
    album: LegacyAlbum
    created_at: Optional[datetime]
    metadata: Dict[str, object] = field(default_factory=dict)
    tags: tuple[str, ...] = field(default_factory=tuple)

    def manifest_entry(self) -> Dict[str, object]:
        """
        Generate a manifest fragment for this asset.
        """

        return {
            "destination": str(self.destination_path),
            "source": str(self.source_path),
            "metadata": self.metadata,
            "album": {
                "slug": self.album.slug,
                "name": self.album.name,
                "type": self.album.album_type,
                "is_public": self.album.is_public,
                "is_training_source": self.album.is_training_source,
                "description": self.album.description,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "tags": list(self.tags),
        }
