"""
Integration tests for Phase 5: Training Pipeline
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from server.database import Album, AlbumImage, Image, Label, TrainingRun, db


class TestTrainingWorkflowIntegration:
    """Test complete training workflow integration"""

    @patch("server.tasks.training.subprocess.Popen")
    @patch("server.tasks.training.prepare_training_data")
    def test_complete_training_workflow(self, mock_prepare, mock_popen, client, app):
        """Test complete training workflow from creation to completion"""
        with app.app_context():
            # Create test album with images
            album = Album(name="Training Album", is_training_source=True)
            db.session.add(album)
            db.session.commit()

            # Create test images
            images = []
            for i in range(3):
                image = Image(
                    filename=f"test_{i}.png",
                    file_path=f"/tmp/test_{i}.png",
                    prompt=f"Test prompt {i}",
                )
                db.session.add(image)
                db.session.flush()

                # Add to album
                album_image = AlbumImage(album_id=album.id, image_id=image.id)
                db.session.add(album_image)

                # Add caption label
                label = Label(
                    image_id=image.id,
                    label_text=f"Test caption {i}",
                    label_type="caption",
                )
                db.session.add(label)

                images.append(image)

            db.session.commit()

            # Mock prepare_training_data
            with tempfile.TemporaryDirectory() as temp_dir:
                mock_prepare.return_value = Path(temp_dir)

                # Mock subprocess for successful training
                mock_process = MagicMock()
                mock_process.stdout = [
                    "Step 10/100",
                    "Step 50/100",
                    "Step 100/100",
                    "Final loss: 0.123",
                ]
                mock_process.wait.return_value = 0
                mock_popen.return_value = mock_process

                # Mock checkpoint file creation
                with patch("pathlib.Path.mkdir"), patch("pathlib.Path.glob") as mock_glob:
                    mock_glob.return_value = [Path("/tmp/checkpoint.safetensors")]

                    # 1. Create training run
                    with patch("server.routes.training.require_admin"):
                        create_data = {
                            "name": "Integration Test Training",
                            "description": "Test workflow",
                            "album_ids": [album.id],
                            "config": {"steps": 100, "rank": 4},
                        }

                        response = client.post("/api/training", json=create_data)
                        assert response.status_code == 201

                        training_data = response.get_json()
                        training_id = training_data["id"]

                    # 2. Start training
                    with patch("server.tasks.training.train_lora_task.delay") as mock_task:
                        mock_task.return_value = MagicMock(id="task-123")

                        response = client.post(f"/api/training/{training_id}/start")
                        assert response.status_code == 200

                    # 3. Execute training task
                    result = train_lora_task(training_id)
                    assert result["status"] == "completed"

                    # 4. Verify training run completion
                    response = client.get(f"/api/training/{training_id}")
                    assert response.status_code == 200

                    training_data = response.get_json()
                    assert training_data["status"] == "completed"
                    assert training_data["progress"] == 100
                    assert training_data["training_loss"] == 0.123

    def test_training_data_preparation_integration(self, app, sample_album_with_images):
        """Test training data preparation with real album data"""
        with app.app_context():
            # Create training run
            run = TrainingRun(
                name="Data Prep Test",
                dataset_path="/tmp/test_data",
                output_path="/tmp/test_output",
                training_config=f'{{"album_ids": [{sample_album_with_images.id}]}}',
                status="pending",
            )
            db.session.add(run)
            db.session.commit()

            with tempfile.TemporaryDirectory() as temp_dir:
                with patch("server.tasks.training.Path") as mock_path:
                    mock_path.return_value = Path(temp_dir)

                    # Mock image files and operations
                    with patch("pathlib.Path.exists", return_value=True), patch(
                        "shutil.copy2"
                    ) as mock_copy, patch("pathlib.Path.write_text") as mock_write:
                        result = prepare_training_data(run)

                        # Verify directory structure
                        training_dir = Path(result)
                        assert training_dir.exists()
                        assert (training_dir / "images").exists()
                        assert (training_dir / "captions").exists()

                        # Verify files were processed
                        assert mock_copy.called
                        assert mock_write.called

                        # Verify caption files were created
                        caption_calls = [call for call in mock_write.call_args_list if "caption" in str(call)]
                        assert len(caption_calls) > 0

    def test_training_with_multiple_albums(self, client, app):
        """Test training with multiple albums"""
        with app.app_context():
            # Create multiple albums
            albums = []
            for i in range(2):
                album = Album(name=f"Album {i}", is_training_source=True)
                db.session.add(album)
                db.session.flush()

                # Add images to album
                for j in range(2):
                    image = Image(
                        filename=f"album_{i}_img_{j}.png",
                        file_path=f"/tmp/album_{i}_img_{j}.png",
                        prompt=f"Album {i} image {j}",
                    )
                    db.session.add(image)
                    db.session.flush()

                    # Add to album
                    album_image = AlbumImage(album_id=album.id, image_id=image.id)
                    db.session.add(album_image)

                    # Add caption
                    label = Label(
                        image_id=image.id,
                        label_text=f"Album {i} caption {j}",
                        label_type="caption",
                    )
                    db.session.add(label)

                albums.append(album)

            db.session.commit()

            # Create training run with multiple albums
            with patch("server.routes.training.require_admin"):
                create_data = {
                    "name": "Multi-Album Training",
                    "album_ids": [album.id for album in albums],
                    "config": {"steps": 100},
                }

                response = client.post("/api/training", json=create_data)
                assert response.status_code == 201

                training_data = response.get_json()
                training_id = training_data["id"]

                # Verify training run was created
                run = TrainingRun.query.get(training_id)
                assert run is not None
                assert run.name == "Multi-Album Training"

    def test_training_error_recovery(self, client, app):
        """Test training error recovery and status updates"""
        with app.app_context():
            # Create training run
            run = TrainingRun(
                name="Error Test",
                dataset_path="/tmp/data",
                output_path="/tmp/output",
                status="pending",
            )
            db.session.add(run)
            db.session.commit()

            # Test cancellation
            with patch("server.routes.training.require_admin"):
                response = client.post(f"/api/training/{run.id}/cancel")
                assert response.status_code == 200

                # Verify status updated
                updated_run = TrainingRun.query.get(run.id)
                assert updated_run.status == "cancelled"
                assert updated_run.error_message == "Cancelled by user"

    def test_training_stats_accuracy(self, client, app):
        """Test training statistics accuracy"""
        with app.app_context():
            # Create various training runs
            statuses = ["completed", "failed", "running", "pending", "cancelled"]
            for i, status in enumerate(statuses):
                run = TrainingRun(
                    name=f"Run {i}",
                    dataset_path="/tmp",
                    output_path="/tmp",
                    status=status,
                )
                if status == "completed":
                    run.progress = 100
                elif status == "running":
                    run.progress = 50
                elif status == "failed":
                    run.error_message = "Test error"

                db.session.add(run)

            db.session.commit()

            # Get statistics
            response = client.get("/api/training/stats")
            assert response.status_code == 200

            data = response.get_json()
            assert data["total_runs"] == 5
            assert data["completed_runs"] == 1
            assert data["failed_runs"] == 1
            assert data["running_runs"] == 1
            assert data["success_rate"] == 20.0  # 1/5 * 100

    def test_training_pagination(self, client, app):
        """Test training runs pagination"""
        with app.app_context():
            # Create multiple training runs
            for i in range(25):
                run = TrainingRun(
                    name=f"Run {i}",
                    dataset_path="/tmp",
                    output_path="/tmp",
                    status="completed",
                )
                db.session.add(run)

            db.session.commit()

            # Test first page
            response = client.get("/api/training?page=1&per_page=10")
            assert response.status_code == 200

            data = response.get_json()
            assert len(data["training_runs"]) == 10
            assert data["pagination"]["page"] == 1
            assert data["pagination"]["per_page"] == 10
            assert data["pagination"]["total"] == 25
            assert data["pagination"]["pages"] == 3

            # Test second page
            response = client.get("/api/training?page=2&per_page=10")
            assert response.status_code == 200

            data = response.get_json()
            assert len(data["training_runs"]) == 10
            assert data["pagination"]["page"] == 2

            # Test last page
            response = client.get("/api/training?page=3&per_page=10")
            assert response.status_code == 200

            data = response.get_json()
            assert len(data["training_runs"]) == 5
            assert data["pagination"]["page"] == 3

    def test_training_status_filtering(self, client, app):
        """Test filtering training runs by status"""
        with app.app_context():
            # Create runs with different statuses
            statuses = ["completed", "failed", "running"]
            for status in statuses:
                run = TrainingRun(
                    name=f"{status.title()} Run",
                    dataset_path="/tmp",
                    output_path="/tmp",
                    status=status,
                )
                db.session.add(run)

            db.session.commit()

            # Test filtering by completed status
            response = client.get("/api/training?status=completed")
            assert response.status_code == 200

            data = response.get_json()
            assert len(data["training_runs"]) == 1
            assert data["training_runs"][0]["status"] == "completed"

            # Test filtering by failed status
            response = client.get("/api/training?status=failed")
            assert response.status_code == 200

            data = response.get_json()
            assert len(data["training_runs"]) == 1
            assert data["training_runs"][0]["status"] == "failed"

    def test_training_cleanup_integration(self, client, app):
        """Test training cleanup integration"""
        with app.app_context():
            # Create completed training run
            run = TrainingRun(
                name="Cleanup Test",
                dataset_path="/tmp/data",
                output_path="/tmp/output",
                status="completed",
            )
            db.session.add(run)
            db.session.commit()

            # Test cleanup
            with patch("server.routes.training.require_admin"), patch(
                "pathlib.Path.exists", return_value=True
            ), patch("shutil.rmtree") as mock_rmtree:
                response = client.post(f"/api/training/{run.id}/cleanup")
                assert response.status_code == 200

                data = response.get_json()
                assert data["message"] == "Cleanup started"
                assert "task_id" in data

                # Verify cleanup task was called
                assert mock_rmtree.called

    def test_training_album_validation(self, client, app):
        """Test training with invalid album IDs"""
        with app.app_context():
            # Create valid album
            album = Album(name="Valid Album", is_training_source=True)
            db.session.add(album)
            db.session.commit()

            with patch("server.routes.training.require_admin"):
                # Test with non-existent album
                create_data = {
                    "name": "Invalid Album Test",
                    "album_ids": [99999],  # Non-existent album
                }

                response = client.post("/api/training", json=create_data)
                assert response.status_code == 400

                data = response.get_json()
                assert "not found" in data["error"]

                # Test with mixed valid and invalid albums
                create_data = {
                    "name": "Mixed Albums Test",
                    "album_ids": [album.id, 99999],
                }

                response = client.post("/api/training", json=create_data)
                assert response.status_code == 400

                data = response.get_json()
                assert "not found" in data["error"]