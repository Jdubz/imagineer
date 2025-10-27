"""
Integration tests for Phase 4: Web Scraping Integration
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from PIL import Image as PILImage
import io

from server.database import db, ScrapeJob, Album, Image, AlbumImage, Label


class TestScrapingWorkflowIntegration:
    """Test complete scraping workflow integration"""

    @patch('server.tasks.scraping.subprocess.Popen')
    @patch('server.tasks.scraping.TRAINING_DATA_PATH')
    def test_end_to_end_scraping_workflow(self, mock_training_path, mock_popen, client):
        """Test complete end-to-end scraping workflow"""
        # Setup mock training data path
        mock_training_path.exists.return_value = True
        mock_training_path.__truediv__ = lambda self, other: Path(f"/mock/training-data/{other}")

        # Mock successful scraping process
        mock_process = MagicMock()
        mock_process.stdout = [
            "Starting web scraper...",
            "Discovered: 100 images",
            "Downloaded: 50 images",
            "Downloaded: 100 images",
            "Scraping completed successfully"
        ]
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        with client.application.app_context():
            # Start scraping job via API
            with patch('server.auth.check_auth') as mock_auth:
                mock_auth.return_value = {'username': 'admin', 'role': 'admin'}

                scrape_data = {
                    'url': 'https://example.com/art-gallery',
                    'name': 'Art Gallery Scrape',
                    'description': 'Scraping art gallery for training data',
                    'depth': 3,
                    'max_images': 500
                }

                response = client.post('/api/scraping/start',
                                     json=scrape_data,
                                     headers={'Authorization': 'Bearer admin_token'})

                assert response.status_code == 201
                start_result = response.get_json()
                job_id = start_result['job_id']

            # Verify job was created
            job = ScrapeJob.query.get(job_id)
            assert job is not None
            assert job.name == "Art Gallery Scrape"
            assert job.source_url == "https://example.com/art-gallery"
            assert job.status == "pending"

            # Simulate task execution with real image import
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                images_dir = temp_path / 'images'
                images_dir.mkdir()

                # Create test images with captions
                test_images = []
                for i in range(5):
                    # Create image
                    img = PILImage.new('RGB', (200, 200), color=(i * 50, 100, 150))
                    img_path = images_dir / f'artwork_{i:03d}.jpg'
                    img.save(img_path, 'JPEG')
                    test_images.append(img_path)

                    # Create caption
                    caption_path = images_dir / f'artwork_{i:03d}.txt'
                    caption_path.write_text(f'Beautiful artwork {i+1} with vibrant colors and artistic composition')

                # Mock the output directory for import
                with patch('server.tasks.scraping.SCRAPED_OUTPUT_PATH') as mock_output_path:
                    mock_output_path.__truediv__ = lambda self, other: temp_path

                    # Execute scraping task
                    from server.tasks.scraping import scrape_site_task
                    task_result = scrape_site_task(job_id)

                    # Verify task completed successfully
                    assert task_result['status'] == 'success'
                    assert task_result['images_imported'] == 5
                    assert 'album_id' in task_result

            # Verify job was updated
            updated_job = ScrapeJob.query.get(job_id)
            assert updated_job.status == 'completed'
            assert updated_job.progress == 100
            assert updated_job.images_scraped == 5

            # Verify album was created
            album = Album.query.get(task_result['album_id'])
            assert album is not None
            assert album.name == "Scraped: Art Gallery Scrape"
            assert album.album_type == "scraped"
            assert album.is_public is True

            # Verify images were imported
            images = Image.query.filter_by(filename__like='artwork_%.jpg').all()
            assert len(images) == 5

            # Verify all images have correct properties
            for image in images:
                assert image.is_public is True
                assert image.is_nsfw is False  # Default, will be updated by AI labeling
                assert image.width == 200
                assert image.height == 200

            # Verify labels were created from captions
            labels = Label.query.filter_by(source_model='scraper').all()
            assert len(labels) == 5

            for i, label in enumerate(labels):
                assert label.label_type == 'caption'
                assert f'artwork {i+1}' in label.label_text.lower()

            # Verify album associations
            associations = AlbumImage.query.filter_by(album_id=album.id).all()
            assert len(associations) == 5

            # Test API endpoints for the completed job
            response = client.get(f'/api/scraping/jobs/{job_id}')
            assert response.status_code == 200
            job_data = response.get_json()
            assert job_data['status'] == 'completed'
            assert job_data['images_scraped'] == 5

            # Test album API
            response = client.get(f'/api/albums/{album.id}')
            assert response.status_code == 200
            album_data = response.get_json()
            assert len(album_data['images']) == 5

    def test_scraping_error_recovery(self, client):
        """Test scraping error recovery and cleanup"""
        with client.application.app_context():
            # Create a failed job
            job = ScrapeJob(
                name="Failed Job",
                source_url="https://invalid-url.com",
                status="failed",
                error_message="Connection timeout",
                images_scraped=0
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

            # Test job listing includes failed job
            response = client.get('/api/scraping/jobs')
            assert response.status_code == 200
            jobs_data = response.get_json()
            
            failed_job = next((j for j in jobs_data['jobs'] if j['id'] == job_id), None)
            assert failed_job is not None
            assert failed_job['status'] == 'failed'
            assert 'timeout' in failed_job['error_message']

            # Test cleanup of failed job
            with patch('server.auth.check_auth') as mock_auth:
                mock_auth.return_value = {'username': 'admin', 'role': 'admin'}

                with patch('server.tasks.scraping.cleanup_scrape_job') as mock_cleanup:
                    mock_cleanup.delay.return_value = MagicMock(id='cleanup-task-id')

                    response = client.post(f'/api/scraping/jobs/{job_id}/cleanup',
                                         headers={'Authorization': 'Bearer admin_token'})

                    assert response.status_code == 200
                    result = response.get_json()
                    assert result['success'] is True

    def test_scraping_with_large_dataset(self, client):
        """Test scraping with large dataset handling"""
        with client.application.app_context():
            # Create job for large dataset
            job = ScrapeJob(
                name="Large Dataset Scrape",
                source_url="https://example.com/large-gallery",
                scrape_config=json.dumps({
                    'depth': 5,
                    'max_images': 10000,
                    'follow_links': True,
                    'download_images': True
                }),
                status="running",
                progress=45,
                images_scraped=4500
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

            # Test job status shows progress
            response = client.get(f'/api/scraping/jobs/{job_id}')
            assert response.status_code == 200
            job_data = response.get_json()
            assert job_data['status'] == 'running'
            assert job_data['progress'] == 45
            assert job_data['images_scraped'] == 4500

            # Test pagination with many jobs
            jobs = []
            for i in range(50):
                job = ScrapeJob(
                    name=f"Batch Job {i}",
                    source_url=f"https://example{i}.com",
                    status="completed",
                    images_scraped=100
                )
                jobs.append(job)
            db.session.add_all(jobs)
            db.session.commit()

            # Test first page
            response = client.get('/api/scraping/jobs?page=1&per_page=20')
            assert response.status_code == 200
            result = response.get_json()
            assert len(result['jobs']) == 20
            assert result['total'] >= 50

    def test_scraping_statistics_accuracy(self, client):
        """Test scraping statistics accuracy"""
        with client.application.app_context():
            # Create various job types
            jobs_data = [
                {'status': 'completed', 'images_scraped': 100},
                {'status': 'completed', 'images_scraped': 250},
                {'status': 'running', 'images_scraped': 50},
                {'status': 'failed', 'images_scraped': 0},
                {'status': 'cancelled', 'images_scraped': 25},
            ]

            for i, job_data in enumerate(jobs_data):
                job = ScrapeJob(
                    name=f"Test Job {i}",
                    source_url=f"https://example{i}.com",
                    status=job_data['status'],
                    images_scraped=job_data['images_scraped']
                )
                db.session.add(job)
            db.session.commit()

            # Test statistics
            response = client.get('/api/scraping/stats')
            assert response.status_code == 200
            stats = response.get_json()

            assert stats['total_jobs'] == 5
            assert stats['total_images_scraped'] == 425  # 100 + 250 + 50 + 0 + 25
            assert stats['status_breakdown']['completed'] == 2
            assert stats['status_breakdown']['running'] == 1
            assert stats['status_breakdown']['failed'] == 1
            assert stats['status_breakdown']['cancelled'] == 1

    def test_scraping_with_duplicate_images(self, client, temp_output_dir):
        """Test handling of duplicate images during import"""
        with client.application.app_context():
            # Create existing image
            existing_image = Image(
                filename="duplicate.jpg",
                file_path="/tmp/duplicate.jpg",
                is_public=True
            )
            db.session.add(existing_image)
            db.session.commit()

            # Create job
            job = ScrapeJob(
                name="Duplicate Test Job",
                source_url="https://example.com",
                status="running"
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

            # Create test images including duplicate
            images_dir = temp_output_dir / 'images'
            images_dir.mkdir()

            # Create duplicate image
            img1 = PILImage.new('RGB', (100, 100), color='red')
            img1_path = images_dir / 'duplicate.jpg'
            img1.save(img1_path, 'JPEG')

            # Create unique image
            img2 = PILImage.new('RGB', (100, 100), color='blue')
            img2_path = images_dir / 'unique.jpg'
            img2.save(img2_path, 'JPEG')

            # Import images
            from server.tasks.scraping import import_scraped_images
            result = import_scraped_images(job_id, temp_output_dir)

            # Should import only unique image
            assert result['imported'] == 1
            assert result['skipped'] == 1

            # Verify only unique image was imported
            unique_image = Image.query.filter_by(filename='unique.jpg').first()
            assert unique_image is not None

            # Verify duplicate was skipped
            duplicate_images = Image.query.filter_by(filename='duplicate.jpg').all()
            assert len(duplicate_images) == 1  # Only the original

    def test_scraping_album_integration(self, client):
        """Test integration between scraping and album system"""
        with client.application.app_context():
            # Create scraped album
            album = Album(
                name="Scraped: Test Gallery",
                description="Test scraped album",
                album_type="scraped",
                is_public=True
            )
            db.session.add(album)
            db.session.commit()

            # Create images in album
            images = []
            for i in range(3):
                image = Image(
                    filename=f"scraped_{i}.jpg",
                    file_path=f"/tmp/scraped_{i}.jpg",
                    is_public=True
                )
                db.session.add(image)
                db.session.flush()

                # Add to album
                assoc = AlbumImage(album_id=album.id, image_id=image.id, sort_order=i)
                db.session.add(assoc)
                images.append(image)

            db.session.commit()

            # Test album API shows scraped images
            response = client.get(f'/api/albums/{album.id}')
            assert response.status_code == 200
            album_data = response.get_json()

            assert album_data['name'] == "Scraped: Test Gallery"
            assert album_data['album_type'] == "scraped"
            assert len(album_data['images']) == 3

            # Test images have correct properties
            for img_data in album_data['images']:
                assert img_data['is_public'] is True
                assert img_data['filename'].startswith('scraped_')

    def test_scraping_performance_metrics(self, client):
        """Test scraping performance metrics and monitoring"""
        with client.application.app_context():
            # Create job with timing data
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            
            job = ScrapeJob(
                name="Performance Test Job",
                source_url="https://example.com",
                status="completed",
                images_scraped=1000,
                created_at=now - timedelta(minutes=30),
                started_at=now - timedelta(minutes=25),
                completed_at=now - timedelta(minutes=5)
            )
            db.session.add(job)
            db.session.commit()

            # Test job timing data
            response = client.get(f'/api/scraping/jobs/{job.id}')
            assert response.status_code == 200
            job_data = response.get_json()

            # Verify timing fields are present
            assert 'created_at' in job_data
            assert 'started_at' in job_data
            assert 'completed_at' in job_data

            # Test recent jobs filter
            response = client.get('/api/scraping/stats')
            assert response.status_code == 200
            stats = response.get_json()
            assert 'recent_jobs' in stats
            assert stats['recent_jobs'] >= 1  # Should include our recent job