"""
Tests for Phase 4: Web Scraping Integration
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from PIL import Image as PILImage
import io

from server.database import db, ScrapeJob, Album, Image, AlbumImage, Label
from server.tasks.scraping import scrape_site_task, import_scraped_images, cleanup_scrape_job


class TestScrapeJobModel:
    """Test ScrapeJob database model"""

    def test_scrape_job_creation(self, client):
        """Test creating a scrape job"""
        with client.application.app_context():
            job = ScrapeJob(
                name="Test Scrape Job",
                description="Testing scrape job creation",
                source_url="https://example.com/gallery",
                scrape_config='{"depth": 3, "max_images": 100}',
                status="pending"
            )
            db.session.add(job)
            db.session.commit()

            assert job.id is not None
            assert job.name == "Test Scrape Job"
            assert job.description == "Testing scrape job creation"
            assert job.source_url == "https://example.com/gallery"
            assert job.status == "pending"
            assert job.progress == 0
            assert job.images_scraped == 0

    def test_scrape_job_to_dict(self, client):
        """Test ScrapeJob to_dict method"""
        with client.application.app_context():
            job = ScrapeJob(
                name="Test Job",
                description="Test Description",
                source_url="https://example.com",
                status="completed",
                progress=100,
                images_scraped=50
            )
            db.session.add(job)
            db.session.commit()

            job_dict = job.to_dict()
            
            assert job_dict['name'] == "Test Job"
            assert job_dict['description'] == "Test Description"
            assert job_dict['source_url'] == "https://example.com"
            assert job_dict['status'] == "completed"
            assert job_dict['progress'] == 100
            assert job_dict['images_scraped'] == 50
            assert 'created_at' in job_dict


class TestScrapingTasks:
    """Test scraping Celery tasks"""

    @patch('server.tasks.scraping.subprocess.Popen')
    def test_scrape_site_task_success(self, mock_popen, client):
        """Test successful scraping task"""
        with client.application.app_context():
            # Create test job
            job = ScrapeJob(
                name="Test Job",
                source_url="https://example.com",
                scrape_config='{"depth": 3, "max_images": 100}',
                status="pending"
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

            # Mock successful subprocess
            mock_process = MagicMock()
            mock_process.stdout = [
                "Starting scrape...",
                "Discovered: 50 images",
                "Downloaded: 25 images",
                "Downloaded: 50 images",
                "Scraping completed successfully"
            ]
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            # Mock import_scraped_images
            with patch('server.tasks.scraping.import_scraped_images') as mock_import:
                mock_import.return_value = {
                    'imported': 50,
                    'album_id': 1
                }

                # Run task
                result = scrape_site_task(job_id)

                # Verify result
                assert result['status'] == 'success'
                assert result['images_imported'] == 50
                assert result['album_id'] == 1

                # Verify job was updated
                updated_job = ScrapeJob.query.get(job_id)
                assert updated_job.status == 'completed'
                assert updated_job.progress == 100
                assert updated_job.images_scraped == 50

    @patch('server.tasks.scraping.subprocess.Popen')
    def test_scrape_site_task_failure(self, mock_popen, client):
        """Test failed scraping task"""
        with client.application.app_context():
            # Create test job
            job = ScrapeJob(
                name="Test Job",
                source_url="https://example.com",
                scrape_config='{"depth": 3, "max_images": 100}',
                status="pending"
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

            # Mock failed subprocess
            mock_process = MagicMock()
            mock_process.stdout = ["Error: Failed to connect"]
            mock_process.wait.return_value = 1
            mock_popen.return_value = mock_process

            # Run task
            result = scrape_site_task(job_id)

            # Verify result
            assert result['status'] == 'error'
            assert 'failed' in result['message']

            # Verify job was updated
            updated_job = ScrapeJob.query.get(job_id)
            assert updated_job.status == 'failed'
            assert updated_job.error_message is not None

    def test_scrape_site_task_job_not_found(self, client):
        """Test scraping task with non-existent job"""
        with client.application.app_context():
            result = scrape_site_task(99999)
            assert result['status'] == 'error'
            assert 'not found' in result['message']

    def test_import_scraped_images(self, client, temp_output_dir):
        """Test importing scraped images"""
        with client.application.app_context():
            # Create test job
            job = ScrapeJob(
                name="Test Job",
                source_url="https://example.com",
                status="running"
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

            # Create test images directory
            images_dir = temp_output_dir / 'images'
            images_dir.mkdir()

            # Create test images
            for i in range(3):
                # Create image file
                img = PILImage.new('RGB', (100, 100), color='red')
                img_path = images_dir / f'test_{i}.jpg'
                img.save(img_path, 'JPEG')

                # Create caption file
                caption_path = images_dir / f'test_{i}.txt'
                caption_path.write_text(f'Test caption {i}')

            # Import images
            result = import_scraped_images(job_id, temp_output_dir)

            # Verify result
            assert result['imported'] == 3
            assert result['album_id'] is not None

            # Verify album was created
            album = Album.query.get(result['album_id'])
            assert album is not None
            assert album.name == f"Scraped: {job.name}"
            assert album.album_type == "scraped"

            # Verify images were imported
            images = Image.query.filter_by(filename__like='test_%.jpg').all()
            assert len(images) == 3

            # Verify labels were created
            labels = Label.query.filter_by(source_model='scraper').all()
            assert len(labels) == 3

            # Verify album associations
            associations = AlbumImage.query.filter_by(album_id=album.id).all()
            assert len(associations) == 3

    def test_cleanup_scrape_job(self, client, temp_output_dir):
        """Test cleaning up scrape job"""
        with client.application.app_context():
            # Create test job with output directory
            job = ScrapeJob(
                name="Test Job",
                source_url="https://example.com",
                status="completed",
                output_directory=str(temp_output_dir)
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

            # Create some test files
            test_file = temp_output_dir / 'test.txt'
            test_file.write_text('test content')

            # Mock shutil.rmtree
            with patch('server.tasks.scraping.shutil.rmtree') as mock_rmtree:
                result = cleanup_scrape_job(job_id)

                # Verify result
                assert result['status'] == 'success'
                mock_rmtree.assert_called_once_with(temp_output_dir)

                # Verify job status
                updated_job = ScrapeJob.query.get(job_id)
                assert updated_job.status == 'cleaned_up'


class TestScrapingAPI:
    """Test scraping API endpoints"""

    def test_start_scrape_unauthorized(self, client):
        """Test starting scrape without admin auth"""
        response = client.post('/api/scraping/start', json={'url': 'https://example.com'})
        assert response.status_code == 401

    @patch('server.tasks.scraping.scrape_site_task')
    def test_start_scrape_success(self, mock_task, client):
        """Test successful scrape start"""
        mock_task.delay.return_value = MagicMock(id='test-task-id')

        with patch('server.auth.check_auth') as mock_auth:
            mock_auth.return_value = {'username': 'admin', 'role': 'admin'}

            data = {
                'url': 'https://example.com/gallery',
                'name': 'Test Gallery Scrape',
                'description': 'Testing gallery scraping',
                'depth': 3,
                'max_images': 500
            }

            response = client.post('/api/scraping/start',
                                 json=data,
                                 headers={'Authorization': 'Bearer admin_token'})

            assert response.status_code == 201
            result = response.get_json()
            assert result['success'] is True
            assert 'job_id' in result
            assert 'task_id' in result

    def test_start_scrape_invalid_url(self, client):
        """Test starting scrape with invalid URL"""
        with patch('server.auth.check_auth') as mock_auth:
            mock_auth.return_value = {'username': 'admin', 'role': 'admin'}

            data = {'url': 'invalid-url'}

            response = client.post('/api/scraping/start',
                                 json=data,
                                 headers={'Authorization': 'Bearer admin_token'})

            assert response.status_code == 400
            result = response.get_json()
            assert 'Invalid URL format' in result['error']

    def test_start_scrape_invalid_parameters(self, client):
        """Test starting scrape with invalid parameters"""
        with patch('server.auth.check_auth') as mock_auth:
            mock_auth.return_value = {'username': 'admin', 'role': 'admin'}

            data = {
                'url': 'https://example.com',
                'depth': 15,  # Invalid depth
                'max_images': 50000  # Invalid max images
            }

            response = client.post('/api/scraping/start',
                                 json=data,
                                 headers={'Authorization': 'Bearer admin_token'})

            assert response.status_code == 400

    def test_list_scrape_jobs(self, client):
        """Test listing scrape jobs"""
        with client.application.app_context():
            # Create test jobs
            job1 = ScrapeJob(name="Job 1", source_url="https://example1.com", status="completed")
            job2 = ScrapeJob(name="Job 2", source_url="https://example2.com", status="running")
            db.session.add_all([job1, job2])
            db.session.commit()

            response = client.get('/api/scraping/jobs')
            assert response.status_code == 200

            result = response.get_json()
            assert 'jobs' in result
            assert 'total' in result
            assert len(result['jobs']) == 2

    def test_get_scrape_job(self, client):
        """Test getting specific scrape job"""
        with client.application.app_context():
            job = ScrapeJob(name="Test Job", source_url="https://example.com", status="pending")
            db.session.add(job)
            db.session.commit()
            job_id = job.id

            response = client.get(f'/api/scraping/jobs/{job_id}')
            assert response.status_code == 200

            result = response.get_json()
            assert result['name'] == "Test Job"
            assert result['source_url'] == "https://example.com"
            assert result['status'] == "pending"

    def test_get_scrape_job_not_found(self, client):
        """Test getting non-existent scrape job"""
        response = client.get('/api/scraping/jobs/99999')
        assert response.status_code == 404

    def test_cancel_scrape_job_unauthorized(self, client):
        """Test cancelling scrape job without admin auth"""
        response = client.post('/api/scraping/jobs/1/cancel')
        assert response.status_code == 401

    def test_cancel_scrape_job_success(self, client):
        """Test successful job cancellation"""
        with client.application.app_context():
            job = ScrapeJob(name="Test Job", source_url="https://example.com", status="running")
            db.session.add(job)
            db.session.commit()
            job_id = job.id

        with patch('server.auth.check_auth') as mock_auth:
            mock_auth.return_value = {'username': 'admin', 'role': 'admin'}

            response = client.post(f'/api/scraping/jobs/{job_id}/cancel',
                                 headers={'Authorization': 'Bearer admin_token'})

            assert response.status_code == 200
            result = response.get_json()
            assert result['success'] is True

            # Verify job was cancelled
            with client.application.app_context():
                updated_job = ScrapeJob.query.get(job_id)
                assert updated_job.status == 'cancelled'

    def test_cancel_scrape_job_invalid_status(self, client):
        """Test cancelling job with invalid status"""
        with client.application.app_context():
            job = ScrapeJob(name="Test Job", source_url="https://example.com", status="completed")
            db.session.add(job)
            db.session.commit()
            job_id = job.id

        with patch('server.auth.check_auth') as mock_auth:
            mock_auth.return_value = {'username': 'admin', 'role': 'admin'}

            response = client.post(f'/api/scraping/jobs/{job_id}/cancel',
                                 headers={'Authorization': 'Bearer admin_token'})

            assert response.status_code == 400
            result = response.get_json()
            assert 'cannot be cancelled' in result['error']

    def test_cleanup_job_unauthorized(self, client):
        """Test cleaning up job without admin auth"""
        response = client.post('/api/scraping/jobs/1/cleanup')
        assert response.status_code == 401

    @patch('server.tasks.scraping.cleanup_scrape_job')
    def test_cleanup_job_success(self, mock_cleanup, client):
        """Test successful job cleanup"""
        with client.application.app_context():
            job = ScrapeJob(name="Test Job", source_url="https://example.com", status="completed")
            db.session.add(job)
            db.session.commit()
            job_id = job.id

        mock_cleanup.delay.return_value = MagicMock(id='cleanup-task-id')

        with patch('server.auth.check_auth') as mock_auth:
            mock_auth.return_value = {'username': 'admin', 'role': 'admin'}

            response = client.post(f'/api/scraping/jobs/{job_id}/cleanup',
                                 headers={'Authorization': 'Bearer admin_token'})

            assert response.status_code == 200
            result = response.get_json()
            assert result['success'] is True
            assert 'task_id' in result

    def test_get_scraping_stats(self, client):
        """Test getting scraping statistics"""
        with client.application.app_context():
            # Create test jobs
            job1 = ScrapeJob(name="Job 1", source_url="https://example1.com", 
                           status="completed", images_scraped=50)
            job2 = ScrapeJob(name="Job 2", source_url="https://example2.com", 
                           status="running", images_scraped=25)
            job3 = ScrapeJob(name="Job 3", source_url="https://example3.com", 
                           status="failed", images_scraped=0)
            db.session.add_all([job1, job2, job3])
            db.session.commit()

            response = client.get('/api/scraping/stats')
            assert response.status_code == 200

            result = response.get_json()
            assert result['total_jobs'] == 3
            assert result['total_images_scraped'] == 75
            assert 'status_breakdown' in result
            assert result['status_breakdown']['completed'] == 1
            assert result['status_breakdown']['running'] == 1
            assert result['status_breakdown']['failed'] == 1


class TestScrapingIntegration:
    """Test scraping integration workflows"""

    @patch('server.tasks.scraping.subprocess.Popen')
    @patch('server.tasks.scraping.import_scraped_images')
    def test_complete_scraping_workflow(self, mock_import, mock_popen, client):
        """Test complete scraping workflow from start to finish"""
        with client.application.app_context():
            # Mock successful scraping
            mock_process = MagicMock()
            mock_process.stdout = ["Scraping completed successfully"]
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            mock_import.return_value = {'imported': 25, 'album_id': 1}

            # Start scrape job
            with patch('server.auth.check_auth') as mock_auth:
                mock_auth.return_value = {'username': 'admin', 'role': 'admin'}

                data = {
                    'url': 'https://example.com/gallery',
                    'name': 'Test Gallery',
                    'depth': 2,
                    'max_images': 100
                }

                response = client.post('/api/scraping/start',
                                     json=data,
                                     headers={'Authorization': 'Bearer admin_token'})

                assert response.status_code == 201
                result = response.get_json()
                job_id = result['job_id']

            # Verify job was created
            job = ScrapeJob.query.get(job_id)
            assert job is not None
            assert job.name == "Test Gallery"
            assert job.source_url == "https://example.com/gallery"
            assert job.status == "pending"

            # Simulate task execution
            task_result = scrape_site_task(job_id)

            # Verify task completed successfully
            assert task_result['status'] == 'success'
            assert task_result['images_imported'] == 25

            # Verify job was updated
            updated_job = ScrapeJob.query.get(job_id)
            assert updated_job.status == 'completed'
            assert updated_job.progress == 100

    def test_scraping_error_handling(self, client):
        """Test scraping error handling"""
        with patch('server.auth.check_auth') as mock_auth:
            mock_auth.return_value = {'username': 'admin', 'role': 'admin'}

            # Test with missing URL
            response = client.post('/api/scraping/start',
                                 json={},
                                 headers={'Authorization': 'Bearer admin_token'})

            assert response.status_code == 400
            result = response.get_json()
            assert 'URL is required' in result['error']

    def test_scraping_pagination(self, client):
        """Test scraping jobs pagination"""
        with client.application.app_context():
            # Create multiple jobs
            jobs = []
            for i in range(25):
                job = ScrapeJob(name=f"Job {i}", source_url=f"https://example{i}.com", status="completed")
                jobs.append(job)
            db.session.add_all(jobs)
            db.session.commit()

            # Test pagination
            response = client.get('/api/scraping/jobs?page=1&per_page=10')
            assert response.status_code == 200

            result = response.get_json()
            assert len(result['jobs']) == 10
            assert result['total'] == 25
            assert result['page'] == 1
            assert result['per_page'] == 10

            # Test second page
            response = client.get('/api/scraping/jobs?page=2&per_page=10')
            assert response.status_code == 200

            result = response.get_json()
            assert len(result['jobs']) == 10
            assert result['page'] == 2