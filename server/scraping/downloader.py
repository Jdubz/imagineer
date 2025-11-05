"""Image downloader with async support and retry logic."""

import asyncio
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
from PIL import Image

from .config import DownloaderConfig
from .models import FailureReason, ImageMetadata, ImageStatus

logger = logging.getLogger(__name__)


class ImageDownloader:
    """Downloads images asynchronously with concurrency control."""

    def __init__(self, config: DownloaderConfig):
        """
        Initialize the image downloader.

        Args:
            config: Downloader configuration
        """
        self.config = config
        self.semaphore = asyncio.Semaphore(config.concurrent_downloads)

    async def download_images(
        self, image_urls: list[str], temp_dir: Path, html_metadata: dict[str, dict] = None
    ) -> list[ImageMetadata]:
        """
        Download multiple images concurrently.

        Args:
            image_urls: List of image URLs to download
            temp_dir: Temporary directory for downloads
            html_metadata: Optional dict mapping URL -> {alt_text, title, html_caption}

        Returns:
            List of image metadata for successfully downloaded images
        """
        temp_dir.mkdir(parents=True, exist_ok=True)

        tasks = [
            self._download_single(url, temp_dir, html_metadata.get(url) if html_metadata else None)
            for url in image_urls
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out failed downloads
        metadata_list = []
        for result in results:
            if isinstance(result, ImageMetadata):
                metadata_list.append(result)
            elif isinstance(result, Exception):
                logger.debug(f"Download failed: {result}")

        logger.info(f"Downloaded {len(metadata_list)} / {len(image_urls)} images")
        return metadata_list

    async def _download_single(
        self, url: str, temp_dir: Path, html_metadata: dict = None
    ) -> ImageMetadata:
        """
        Download a single image with retries.

        Args:
            url: Image URL
            temp_dir: Temporary directory
            html_metadata: Optional metadata from HTML (alt_text, title, html_caption)

        Returns:
            Image metadata

        Raises:
            Exception if download fails after all retries
        """
        async with self.semaphore:
            parsed = urlparse(url)
            source_domain = parsed.netloc

            metadata = ImageMetadata(
                url=url,
                source_domain=source_domain,
                discovered_at=datetime.now(),
            )

            # Add HTML metadata if provided
            if html_metadata:
                metadata.alt_text = html_metadata.get("alt_text")
                metadata.title = html_metadata.get("title")
                metadata.html_caption = html_metadata.get("html_caption")

            for attempt in range(self.config.max_retries):
                try:
                    async with httpx.AsyncClient(
                        follow_redirects=True,
                        timeout=self.config.timeout,
                    ) as client:
                        response = await client.get(
                            url,
                            headers={"User-Agent": self.config.user_agent},
                        )
                        response.raise_for_status()

                        # Generate unique filename using URL hash + extension
                        filename = self._generate_filename(url, response.content)
                        file_path = temp_dir / filename

                        # Save to disk
                        file_path.write_bytes(response.content)

                        # Open and validate image
                        try:
                            with Image.open(file_path) as img:
                                metadata.width = img.width
                                metadata.height = img.height
                                metadata.format = img.format.lower() if img.format else None
                                metadata.file_size = file_path.stat().st_size
                                metadata.local_path = file_path
                                metadata.status = ImageStatus.DOWNLOADED

                                logger.debug(
                                    f"Downloaded {filename} ({metadata.width}x{metadata.height})"
                                )
                                return metadata

                        except Exception as e:
                            # Invalid image file
                            file_path.unlink(missing_ok=True)
                            metadata.status = ImageStatus.FAILED
                            metadata.failure_reason = FailureReason.INVALID_FORMAT
                            metadata.error_message = str(e)
                            raise Exception(f"Invalid image format: {e}")

                except httpx.HTTPStatusError as e:
                    if attempt == self.config.max_retries - 1:
                        metadata.status = ImageStatus.FAILED
                        metadata.failure_reason = FailureReason.DOWNLOAD_ERROR
                        metadata.error_message = f"HTTP {e.response.status_code}"
                        raise
                    await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff

                except Exception as e:
                    if attempt == self.config.max_retries - 1:
                        metadata.status = ImageStatus.FAILED
                        metadata.failure_reason = FailureReason.DOWNLOAD_ERROR
                        metadata.error_message = str(e)
                        raise
                    await asyncio.sleep(1 * (attempt + 1))

            return metadata

    def _generate_filename(self, url: str, content: bytes = None) -> str:
        """
        Generate a unique filename from URL and content hash.

        Args:
            url: Image URL
            content: Optional image content for hashing

        Returns:
            Generated filename
        """
        parsed = urlparse(url)
        path = parsed.path

        # Get the last part of the path for extension
        url_filename = path.split("/")[-1]

        # Extract extension
        if "." in url_filename:
            ext = url_filename.split(".")[-1].lower()
            # Validate extension
            if ext not in ["jpg", "jpeg", "png", "webp", "gif", "bmp", "jfif"]:
                ext = "jpg"
        else:
            ext = "jpg"

        # Generate unique hash-based filename
        if content:
            # Use content hash for uniqueness
            content_hash = hashlib.md5(content).hexdigest()[:12]
        else:
            # Use URL hash if no content
            content_hash = hashlib.md5(url.encode()).hexdigest()[:12]

        # Sanitize domain
        domain = parsed.netloc.replace("www.", "").replace(".", "_")
        domain = "".join(c for c in domain if c.isalnum() or c == "_")[:20]

        filename = f"{domain}_{content_hash}.{ext}"

        return filename
