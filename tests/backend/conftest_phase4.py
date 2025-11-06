"""
Additional pytest configuration for Phase 4 scraping tests
"""

import json

import pytest

from server.database import Album, AlbumImage, Image, Label, ScrapeJob, db


@pytest.fixture
def sample_scrape_job(client):
    """Create a sample scrape job for testing"""
    with client.application.app_context():
        job = ScrapeJob(
            name="Test Scrape Job",
            description="Test scraping job for testing",
            source_url="https://example.com/gallery",
            scrape_config=json.dumps(
                {"depth": 3, "max_images": 100, "follow_links": True, "download_images": True}
            ),
            status="pending",
        )
        db.session.add(job)
        db.session.commit()
        yield job


@pytest.fixture
def sample_scraped_album(client):
    """Create a sample scraped album with images"""
    with client.application.app_context():
        # Create album
        album = Album(
            name="Scraped: Test Gallery",
            description="Test scraped album",
            album_type="scraped",
            is_public=True,
        )
        db.session.add(album)
        db.session.commit()

        # Create images
        images = []
        for i in range(3):
            image = Image(
                filename=f"scraped_{i:03d}.jpg",
                file_path=f"/tmp/scraped_{i:03d}.jpg",
                is_public=True,
                is_nsfw=False,
            )
            db.session.add(image)
            db.session.flush()

            # Add caption label
            label = Label(
                image_id=image.id,
                label_text=f"Beautiful artwork {i + 1} with vibrant colors",
                label_type="caption",
                source_model="scraper",
            )
            db.session.add(label)

            # Add to album
            assoc = AlbumImage(album_id=album.id, image_id=image.id, sort_order=i)
            db.session.add(assoc)
            images.append(image)

        db.session.commit()
        yield album, images


@pytest.fixture
def temp_scraped_images(temp_output_dir):
    """Create temporary scraped images for testing"""
    images_dir = temp_output_dir / "images"
    images_dir.mkdir()

    # Create test images with captions
    test_images = []
    for i in range(5):
        # Create image
        from PIL import Image as PILImage

        img = PILImage.new("RGB", (200, 200), color=(i * 50, 100, 150))
        img_path = images_dir / f"artwork_{i:03d}.jpg"
        img.save(img_path, "JPEG")
        test_images.append(img_path)

        # Create caption
        caption_path = images_dir / f"artwork_{i:03d}.txt"
        caption_path.write_text(
            f"Beautiful artwork {i + 1} with vibrant colors and artistic composition"
        )

    yield temp_output_dir, test_images


@pytest.fixture(autouse=True)
def clean_scraping_database(client):
    """Clean scraping-related database tables before each test"""
    with client.application.app_context():
        # Clear all tables
        db.session.query(Label).delete()
        db.session.query(AlbumImage).delete()
        db.session.query(Image).delete()
        db.session.query(Album).delete()
        db.session.query(ScrapeJob).delete()
        db.session.commit()
        yield
        # Cleanup after test
        db.session.query(Label).delete()
        db.session.query(AlbumImage).delete()
        db.session.query(Image).delete()
        db.session.query(Album).delete()
        db.session.query(ScrapeJob).delete()
        db.session.commit()


@pytest.fixture
def sample_scraping_config():
    """Sample scraping configuration for testing"""
    return {"depth": 3, "max_images": 1000, "follow_links": True, "download_images": True}


@pytest.fixture
def sample_scraping_jobs(client):
    """Create multiple sample scraping jobs for testing"""
    with client.application.app_context():
        jobs_data = [
            {
                "name": "Completed Job",
                "source_url": "https://example1.com",
                "status": "completed",
                "images_scraped": 100,
                "progress": 100,
            },
            {
                "name": "Running Job",
                "source_url": "https://example2.com",
                "status": "running",
                "images_scraped": 50,
                "progress": 50,
            },
            {
                "name": "Failed Job",
                "source_url": "https://example3.com",
                "status": "failed",
                "images_scraped": 0,
                "progress": 0,
                "error_message": "Connection timeout",
            },
            {
                "name": "Pending Job",
                "source_url": "https://example4.com",
                "status": "pending",
                "images_scraped": 0,
                "progress": 0,
            },
        ]

        jobs = []
        for job_data in jobs_data:
            job = ScrapeJob(**job_data)
            db.session.add(job)
            jobs.append(job)

        db.session.commit()
        yield jobs
