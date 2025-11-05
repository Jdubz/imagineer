"""Data models for web scraping in Imagineer."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class ImageStatus(str, Enum):
    """Status of an image during scraping pipeline."""

    DISCOVERED = "discovered"
    DOWNLOADED = "downloaded"
    VALIDATED = "validated"
    CAPTIONED = "captioned"
    SAVED = "saved"
    FAILED = "failed"
    SKIPPED = "skipped"


class FailureReason(str, Enum):
    """Reason for image failure or skip during scraping."""

    DOWNLOAD_ERROR = "download_error"
    INVALID_FORMAT = "invalid_format"
    TOO_SMALL = "too_small"
    INVALID_ASPECT_RATIO = "invalid_aspect_ratio"
    DUPLICATE = "duplicate"
    CAPTION_ERROR = "caption_error"
    SAVE_ERROR = "save_error"
    OTHER = "other"


@dataclass
class ImageMetadata:
    """Metadata for a single scraped image."""

    url: str
    source_domain: str
    discovered_at: datetime = field(default_factory=datetime.now)
    status: ImageStatus = ImageStatus.DISCOVERED
    failure_reason: Optional[FailureReason] = None
    error_message: Optional[str] = None

    # Image properties (populated after download)
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None
    file_size: Optional[int] = None
    perceptual_hash: Optional[str] = None

    # Processing info
    local_path: Optional[Path] = None
    caption: Optional[str] = None
    caption_path: Optional[Path] = None

    # HTML metadata (alt text, titles, etc.)
    alt_text: Optional[str] = None
    title: Optional[str] = None
    html_caption: Optional[str] = None

    @property
    def megapixels(self) -> Optional[float]:
        """Calculate megapixels."""
        if self.width and self.height:
            return (self.width * self.height) / 1_000_000
        return None

    @property
    def aspect_ratio(self) -> Optional[float]:
        """Calculate aspect ratio (max dimension / min dimension)."""
        if self.width and self.height:
            return max(self.width, self.height) / min(self.width, self.height)
        return None


@dataclass
class ScrapingSession:
    """Information about a scraping session for tracking and reporting."""

    url: str
    prompt: str
    output_dir: Path
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None

    # Statistics
    images_discovered: int = 0
    images_downloaded: int = 0
    images_validated: int = 0
    images_captioned: int = 0
    images_saved: int = 0
    images_failed: int = 0
    images_skipped: int = 0

    # Metadata for all images
    image_metadata: list[ImageMetadata] = field(default_factory=list)

    @property
    def duration(self) -> Optional[float]:
        """Calculate session duration in seconds."""
        if self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    @property
    def success_rate(self) -> float:
        """Calculate success rate (saved / discovered)."""
        if self.images_discovered == 0:
            return 0.0
        return self.images_saved / self.images_discovered

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "url": self.url,
            "prompt": self.prompt,
            "output_dir": str(self.output_dir),
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration,
            "statistics": {
                "discovered": self.images_discovered,
                "downloaded": self.images_downloaded,
                "validated": self.images_validated,
                "captioned": self.images_captioned,
                "saved": self.images_saved,
                "failed": self.images_failed,
                "skipped": self.images_skipped,
                "success_rate": self.success_rate,
            },
            "images": [
                {
                    "url": img.url,
                    "status": img.status.value,
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "megapixels": img.megapixels,
                    "local_path": str(img.local_path) if img.local_path else None,
                    "caption": img.caption,
                    "alt_text": img.alt_text,
                    "title": img.title,
                    "html_caption": img.html_caption,
                    "failure_reason": img.failure_reason.value if img.failure_reason else None,
                    "error_message": img.error_message,
                }
                for img in self.image_metadata
            ],
        }


@dataclass
class CaptionRequest:
    """Request for AI image captioning."""

    image_path: Path
    prompt_context: str
    metadata: ImageMetadata


@dataclass
class CaptionResponse:
    """Response from AI image captioning."""

    caption: str
    metadata: ImageMetadata
    success: bool = True
    error: Optional[str] = None
    nsfw_detected: bool = False
    tags: list[str] = field(default_factory=list)
    confidence: float = 0.0
