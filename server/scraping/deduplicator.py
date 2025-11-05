"""Image deduplication using perceptual hashing."""

import logging
from typing import Optional

import imagehash
from PIL import Image

from .config import DeduplicatorConfig
from .models import FailureReason, ImageMetadata, ImageStatus

logger = logging.getLogger(__name__)


class ImageDeduplicator:
    """Detects and removes duplicate images using perceptual hashing (imagehash)."""

    def __init__(self, config: DeduplicatorConfig):
        """
        Initialize the deduplicator.

        Args:
            config: Deduplicator configuration
        """
        self.config = config
        self.hash_map: dict[str, ImageMetadata] = {}

    def compute_hash(self, metadata: ImageMetadata) -> Optional[str]:
        """
        Compute perceptual hash for an image.

        Args:
            metadata: Image metadata

        Returns:
            Hash string or None if computation fails
        """
        if not metadata.local_path or not metadata.local_path.exists():
            return None

        try:
            with Image.open(metadata.local_path) as img:
                # Use average hash (fast and effective for detecting duplicates)
                phash = imagehash.average_hash(img)
                hash_str = str(phash)
                metadata.perceptual_hash = hash_str
                return hash_str
        except Exception as e:
            logger.debug(f"Failed to compute hash for {metadata.local_path}: {e}")
            return None

    def is_duplicate(self, metadata: ImageMetadata) -> bool:
        """
        Check if an image is a duplicate of an already-seen image.

        Args:
            metadata: Image metadata

        Returns:
            True if image is a duplicate (updates metadata.status)
        """
        if not self.config.enabled:
            return False

        phash = self.compute_hash(metadata)
        if not phash:
            return False

        # Check against existing hashes
        for existing_hash, existing_metadata in self.hash_map.items():
            # Calculate Hamming distance between hashes
            hash1 = imagehash.hex_to_hash(phash)
            hash2 = imagehash.hex_to_hash(existing_hash)
            distance = hash1 - hash2

            if distance <= self.config.duplicate_threshold:
                metadata.status = ImageStatus.SKIPPED
                metadata.failure_reason = FailureReason.DUPLICATE
                metadata.error_message = f"Duplicate of {existing_metadata.url}"
                logger.debug(
                    f"Duplicate detected: {metadata.url} matches {existing_metadata.url} "
                    f"(distance: {distance})"
                )
                return True

        # Not a duplicate, add to hash map
        self.hash_map[phash] = metadata
        return False

    def deduplicate_batch(self, metadata_list: list[ImageMetadata]) -> list[ImageMetadata]:
        """
        Remove duplicates from a batch of images.

        Args:
            metadata_list: List of image metadata

        Returns:
            List of unique images
        """
        if not self.config.enabled:
            return metadata_list

        unique = []
        for metadata in metadata_list:
            if not self.is_duplicate(metadata):
                unique.append(metadata)

        duplicates_found = len(metadata_list) - len(unique)
        if duplicates_found > 0:
            logger.info(f"Removed {duplicates_found} duplicate images")

        return unique

    def reset(self) -> None:
        """Clear the hash map (useful for starting a new scraping session)."""
        self.hash_map.clear()
