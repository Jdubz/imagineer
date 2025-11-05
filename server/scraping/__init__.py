"""
Web scraping package for Imagineer.

This package provides comprehensive web scraping functionality for discovering,
downloading, and processing images from websites. It includes:

- WebCrawler: Discovers image URLs using Playwright (supports JS rendering)
- ImageDownloader: Downloads images concurrently with retry logic
- ImageValidator: Validates images by format, dimensions, aspect ratio
- ImageDeduplicator: Removes duplicate images using perceptual hashing
- ClaudeCaptioner: Optional AI captioning using Anthropic Claude

Configuration is managed via Pydantic models loaded from config.yaml.
"""

from .config import ScrapingConfig
from .crawler import WebCrawler
from .deduplicator import ImageDeduplicator
from .downloader import ImageDownloader
from .models import FailureReason, ImageMetadata, ImageStatus, ScrapingSession
from .validator import ImageValidator

__all__ = [
    "ScrapingConfig",
    "WebCrawler",
    "ImageDownloader",
    "ImageValidator",
    "ImageDeduplicator",
    "ImageMetadata",
    "ScrapingSession",
    "ImageStatus",
    "FailureReason",
]
