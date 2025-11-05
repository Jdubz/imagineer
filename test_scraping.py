#!/usr/bin/env python3
"""
Quick test script for the new scraping implementation.

Tests the scraping pipeline without Celery or database dependencies.
"""

import asyncio
import logging
from pathlib import Path

from server.scraping import (
    ImageDeduplicator,
    ImageDownloader,
    ImageValidator,
    WebCrawler,
)
from server.scraping.config import get_scraping_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_scraping(url: str, output_dir: Path, max_images: int = 10):
    """
    Test the scraping pipeline end-to-end.

    Args:
        url: Website URL to scrape
        output_dir: Output directory for images
        max_images: Maximum images to download
    """
    logger.info(f"Starting scraping test for {url}")

    # Load config
    config = get_scraping_config()

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Phase 1: Crawl
    logger.info("Phase 1: Crawling website...")
    crawler = WebCrawler(config.crawler)
    image_urls = await crawler.crawl(url, max_images=max_images)
    logger.info(f"Discovered {len(image_urls)} images")

    if not image_urls:
        logger.warning("No images found!")
        return

    # Phase 2: Download
    logger.info("Phase 2: Downloading images...")
    downloader = ImageDownloader(config.downloader)
    metadata_list = await downloader.download_images(image_urls, output_dir, crawler.image_metadata)
    logger.info(f"Downloaded {len(metadata_list)} images")

    # Phase 3: Validate
    logger.info("Phase 3: Validating images...")
    validator = ImageValidator(config.validator)
    valid_metadata = validator.validate_batch(metadata_list)
    logger.info(f"Validated {len(valid_metadata)} images")

    # Phase 4: Deduplicate
    logger.info("Phase 4: Removing duplicates...")
    deduplicator = ImageDeduplicator(config.deduplicator)
    unique_metadata = deduplicator.deduplicate_batch(valid_metadata)
    logger.info(f"Unique images: {len(unique_metadata)}")

    # Summary
    logger.info("\n=== Scraping Summary ===")
    logger.info(f"URLs discovered: {len(image_urls)}")
    logger.info(f"Images downloaded: {len(metadata_list)}")
    logger.info(f"Images validated: {len(valid_metadata)}")
    logger.info(f"Unique images: {len(unique_metadata)}")
    logger.info(f"Output directory: {output_dir}")

    # Show some example metadata
    if unique_metadata:
        logger.info("\n=== Example Image Metadata ===")
        example = unique_metadata[0]
        logger.info(f"URL: {example.url}")
        logger.info(f"File: {example.local_path}")
        logger.info(f"Dimensions: {example.width}x{example.height}")
        logger.info(f"Format: {example.format}")
        if example.alt_text:
            logger.info(f"Alt text: {example.alt_text}")
        if example.title:
            logger.info(f"Title: {example.title}")
        if example.html_caption:
            logger.info(f"Caption: {example.html_caption}")


if __name__ == "__main__":
    import sys

    # Test with a simple URL (or use command line argument)
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.wopc.co.uk/"
    test_output = Path("/tmp/imagineer-scraping-test")

    # Run the test
    asyncio.run(test_scraping(test_url, test_output, max_images=10))
