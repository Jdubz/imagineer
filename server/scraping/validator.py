"""Image validation module."""

import logging

from .config import ValidatorConfig
from .models import FailureReason, ImageMetadata, ImageStatus

logger = logging.getLogger(__name__)


class ImageValidator:
    """Validates images against quality criteria (dimensions, format, aspect ratio)."""

    def __init__(self, config: ValidatorConfig):
        """
        Initialize the image validator.

        Args:
            config: Validator configuration
        """
        self.config = config

    def validate(self, metadata: ImageMetadata) -> bool:
        """
        Validate an image against configured criteria.

        Args:
            metadata: Image metadata to validate

        Returns:
            True if image is valid, False otherwise (updates metadata.status)
        """
        # Check if already failed
        if metadata.status == ImageStatus.FAILED:
            return False

        # Validate format
        if not self._validate_format(metadata):
            metadata.status = ImageStatus.SKIPPED
            metadata.failure_reason = FailureReason.INVALID_FORMAT
            metadata.error_message = f"Format {metadata.format} not in allowed formats"
            logger.debug(f"Skipped {metadata.url}: invalid format")
            return False

        # Validate dimensions
        if not self._validate_dimensions(metadata):
            metadata.status = ImageStatus.SKIPPED
            metadata.failure_reason = FailureReason.TOO_SMALL
            metadata.error_message = (
                f"Image {metadata.width}x{metadata.height} below minimum "
                f"{self.config.min_width}x{self.config.min_height}"
            )
            logger.debug(f"Skipped {metadata.url}: too small")
            return False

        # Validate megapixels
        if not self._validate_megapixels(metadata):
            metadata.status = ImageStatus.SKIPPED
            metadata.failure_reason = FailureReason.TOO_SMALL
            metadata.error_message = (
                f"Image {metadata.megapixels:.2f}MP below minimum "
                f"{self.config.min_megapixels}MP"
            )
            logger.debug(f"Skipped {metadata.url}: insufficient megapixels")
            return False

        # Validate aspect ratio
        if not self._validate_aspect_ratio(metadata):
            metadata.status = ImageStatus.SKIPPED
            metadata.failure_reason = FailureReason.INVALID_ASPECT_RATIO
            metadata.error_message = (
                f"Aspect ratio {metadata.aspect_ratio:.2f} exceeds maximum "
                f"{self.config.max_aspect_ratio}"
            )
            logger.debug(f"Skipped {metadata.url}: extreme aspect ratio")
            return False

        # All validations passed
        metadata.status = ImageStatus.VALIDATED
        return True

    def _validate_format(self, metadata: ImageMetadata) -> bool:
        """Validate image format is in allowed list."""
        if not metadata.format:
            return False
        return metadata.format.lower() in self.config.allowed_formats

    def _validate_dimensions(self, metadata: ImageMetadata) -> bool:
        """Validate image meets minimum dimensions."""
        if not metadata.width or not metadata.height:
            return False
        return metadata.width >= self.config.min_width and metadata.height >= self.config.min_height

    def _validate_megapixels(self, metadata: ImageMetadata) -> bool:
        """Validate image meets minimum megapixels."""
        mp = metadata.megapixels
        if mp is None:
            return False
        return mp >= self.config.min_megapixels

    def _validate_aspect_ratio(self, metadata: ImageMetadata) -> bool:
        """Validate aspect ratio is not too extreme."""
        ar = metadata.aspect_ratio
        if ar is None:
            return False
        return ar <= self.config.max_aspect_ratio

    def validate_batch(self, metadata_list: list[ImageMetadata]) -> list[ImageMetadata]:
        """
        Validate a batch of images.

        Args:
            metadata_list: List of image metadata

        Returns:
            List of valid image metadata
        """
        valid = []
        skipped = []

        for metadata in metadata_list:
            if self.validate(metadata):
                valid.append(metadata)
            else:
                skipped.append(metadata)

        logger.info(f"Validated {len(valid)} / {len(metadata_list)} images")
        if skipped:
            logger.debug(f"Skipped {len(skipped)} images due to validation failures")

        return valid
