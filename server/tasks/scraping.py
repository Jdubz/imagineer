"""
Web scraping using internal server.scraping package.

Modern async implementation with no external dependencies.
"""

import asyncio
import logging
from datetime import datetime, timezone

from celery import Task

from server.celery_app import celery
from server.database import Album, Image, Label, ScrapeJob, db
from server.scraping import (
    ImageDeduplicator,
    ImageDownloader,
    ImageValidator,
    ScrapingSession,
    WebCrawler,
)
from server.scraping.config import get_scraping_config

logger = logging.getLogger(__name__)


@celery.task(bind=True, base=Task)
def scrape_site_async(self, scrape_job_id: int):
    """
    Execute web scraping using internal scraping package.

    This is the Celery task version that can be called asynchronously.

    Args:
        scrape_job_id: Database ID of scrape job

    Returns:
        Dict with results
    """
    # Run async scraping in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_scrape_site_internal(scrape_job_id, self))
        return result
    finally:
        loop.close()


async def _scrape_site_internal(scrape_job_id: int, celery_task=None):
    """
    Internal async implementation of web scraping.

    Args:
        scrape_job_id: Database ID of scrape job
        celery_task: Optional Celery task for progress updates

    Returns:
        Dict with scraping results
    """
    from server.api import app

    with app.app_context():
        # Load job from database
        job = db.session.get(ScrapeJob, scrape_job_id)
        if not job:
            return {"status": "error", "message": "Job not found"}

        # Load scraping configuration
        config = get_scraping_config()

        # Update job status
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        job.progress = 0
        job.description = "Initializing scraping"
        db.session.commit()

        logger.info(f"Starting scrape job {scrape_job_id}: {job.source_url}")

        try:
            # Create output directory
            output_dir = config.output_base_dir / f"job_{scrape_job_id}"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Initialize scraping session
            session = ScrapingSession(
                url=job.source_url,
                prompt="",  # Not used for scraping, only for captioning
                output_dir=output_dir,
            )

            # Phase 1: Crawl website to discover image URLs
            job.description = "Crawling website"
            job.progress = 10
            db.session.commit()

            crawler = WebCrawler(config.crawler)
            image_urls = await crawler.crawl(
                job.source_url, max_images=job.max_images or config.crawler.max_images
            )

            session.images_discovered = len(image_urls)
            logger.info(f"Discovered {len(image_urls)} images")

            if len(image_urls) == 0:
                job.status = "completed"
                job.completed_at = datetime.now(timezone.utc)
                job.progress = 100
                job.description = "No images found"
                db.session.commit()
                return {"status": "success", "images_imported": 0, "album_id": None}

            # Phase 2: Download images
            job.description = f"Downloading {len(image_urls)} images"
            job.progress = 30
            db.session.commit()

            downloader = ImageDownloader(config.downloader)
            metadata_list = await downloader.download_images(
                image_urls, output_dir, crawler.image_metadata
            )

            session.images_downloaded = len(metadata_list)
            logger.info(f"Downloaded {len(metadata_list)} images")

            # Phase 3: Validate images
            job.description = "Validating images"
            job.progress = 60
            db.session.commit()

            validator = ImageValidator(config.validator)
            valid_metadata = validator.validate_batch(metadata_list)

            session.images_validated = len(valid_metadata)
            logger.info(f"Validated {len(valid_metadata)} images")

            # Phase 4: Remove duplicates
            job.description = "Removing duplicates"
            job.progress = 75
            db.session.commit()

            deduplicator = ImageDeduplicator(config.deduplicator)
            unique_metadata = deduplicator.deduplicate_batch(valid_metadata)

            session.images_saved = len(unique_metadata)
            session.images_skipped = len(metadata_list) - len(unique_metadata)
            logger.info(f"Deduplicated to {len(unique_metadata)} unique images")

            # Phase 5: Import to database and create album
            job.description = "Importing to database"
            job.progress = 90
            db.session.commit()

            album = _create_album_from_metadata(job, unique_metadata, session)

            # Update session metadata
            session.image_metadata = unique_metadata
            session.finished_at = datetime.now(timezone.utc)

            # Complete job
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job.progress = 100
            job.output_directory = str(output_dir)
            job.album_id = album.id
            job.description = "Scraping completed successfully"
            db.session.commit()

            logger.info(
                f"Scrape job {scrape_job_id} completed: "
                f"{session.images_saved} images in album {album.id}"
            )

            return {
                "status": "success",
                "images_imported": session.images_saved,
                "album_id": album.id,
                "output_directory": str(output_dir),
                "session": session.to_dict(),
            }

        except Exception as e:
            error_msg = f"Scraping error: {str(e)}"
            logger.error(f"Scrape job {scrape_job_id} failed: {e}", exc_info=True)

            job.status = "failed"
            job.completed_at = datetime.now(timezone.utc)
            job.error_message = error_msg
            job.last_error_at = datetime.now(timezone.utc)
            job.description = error_msg
            db.session.commit()

            return {"status": "error", "message": error_msg}


def _create_album_from_metadata(job: ScrapeJob, metadata_list, session) -> Album:
    """
    Create an album and import images from scraped metadata.

    Args:
        job: ScrapeJob instance
        metadata_list: List of ImageMetadata objects
        session: ScrapingSession with statistics

    Returns:
        Created Album instance
    """
    # Create album
    album = Album(
        name=job.name or f"Scraped from {job.source_url}",
        description=job.description or f"Scraped {len(metadata_list)} images",
        album_type="scraped",
        source_type="scrape",
        source_id=job.id,
        created_by=job.created_by,
    )
    db.session.add(album)
    db.session.flush()  # Get album ID

    # Import each image
    for idx, metadata in enumerate(metadata_list):
        if not metadata.local_path or not metadata.local_path.exists():
            logger.warning(f"Skipping image with missing file: {metadata.url}")
            continue

        # Create Image record
        image = Image(
            filename=metadata.local_path.name,
            file_path=str(metadata.local_path),
            width=metadata.width,
            height=metadata.height,
            created_by=job.created_by,
        )
        db.session.add(image)
        db.session.flush()  # Get image ID

        # Create labels from HTML metadata
        if metadata.alt_text:
            label = Label(
                image_id=image.id,
                label_text=metadata.alt_text,
                label_type="scrape_alt_text",
                source_model="html_metadata",
                created_by=job.created_by,
            )
            db.session.add(label)

        if metadata.title:
            label = Label(
                image_id=image.id,
                label_text=metadata.title,
                label_type="scrape_title",
                source_model="html_metadata",
                created_by=job.created_by,
            )
            db.session.add(label)

        if metadata.html_caption:
            label = Label(
                image_id=image.id,
                label_text=metadata.html_caption,
                label_type="scrape_caption",
                source_model="html_metadata",
                created_by=job.created_by,
            )
            db.session.add(label)

        # Add image to album
        from server.database import AlbumImage

        album_image = AlbumImage(
            album_id=album.id,
            image_id=image.id,
            sort_order=idx,
            added_by=job.created_by,
        )
        db.session.add(album_image)

    db.session.commit()

    logger.info(f"Created album {album.id} with {len(metadata_list)} images")

    return album
