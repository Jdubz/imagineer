"""
Tests for Phase 5: Training Pipeline
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from server.database import Album, AlbumImage, Image, Label, TrainingRun, db
from server.tasks.training import (
    cleanup_training_data,
    prepare_training_data,
    train_lora_task,
)


@pytest.fixture(autouse=True)
def clean_database(app):
    """Clean database before each test"""
    with app.app_context():
        # Clean up all tables
        db.session.query(TrainingRun).delete()
        db.session.query(AlbumImage).delete()
        db.session.query(Label).delete()
        db.session.query(Image).delete()
        db.session.query(Album).delete()
        db.session.commit()
    yield
    # Clean up after test as well
    with app.app_context():
        db.session.query(TrainingRun).delete()
        db.session.query(AlbumImage).delete()
        db.session.query(Label).delete()
        db.session.query(Image).delete()
        db.session.query(Album).delete()
        db.session.commit()


@pytest.fixture
def mock_admin_user():
    """Mock admin user for authentication"""
    from unittest.mock import MagicMock

    mock_user = MagicMock()
    mock_user.is_authenticated = True
    mock_user.is_admin.return_value = True
    return mock_user


class TestTrainingRunModel:
    """Test TrainingRun database model"""

    def test_training_run_creation(self, app):
        """Test creating a training run"""
        with app.app_context():
            run = TrainingRun(
                name="Test Training",
                description="Test description",
                dataset_path="/tmp/test_data",
                output_path="/tmp/test_output",
                training_config='{"steps": 1000, "rank": 4}',
                status="pending",
                progress=0,
            )

            db.session.add(run)
            db.session.commit()

            assert run.id is not None
            assert run.name == "Test Training"
            assert run.status == "pending"
            assert run.progress == 0

    def test_training_run_to_dict(self, app):
        """Test TrainingRun to_dict method"""
        with app.app_context():
            run = TrainingRun(
                name="Test Training",
                description="Test description",
                dataset_path="/tmp/test_data",
                output_path="/tmp/test_output",
                training_config='{"steps": 1000}',
                status="completed",
                progress=100,
                final_checkpoint="/tmp/checkpoint.safetensors",
                training_loss=0.123,
            )

            db.session.add(run)
            db.session.commit()

            data = run.to_dict()
            assert data["name"] == "Test Training"
            assert data["status"] == "completed"
            assert data["progress"] == 100
            assert data["final_checkpoint"] == "/tmp/checkpoint.safetensors"
            assert data["training_loss"] == 0.123


class TestTrainingTasks:
    """Test training Celery tasks"""

    @patch("server.tasks.training.subprocess.Popen")
    @patch("server.tasks.training.prepare_training_data")
    def test_train_lora_task_success(self, mock_prepare, mock_popen, app):
        """Test successful LoRA training task"""
        with app.app_context():
            # Create training run
            run = TrainingRun(
                name="Test Training",
                dataset_path="/tmp/test_data",
                output_path="/tmp/test_output",
                training_config='{"steps": 100, "rank": 4}',
                status="pending",
            )
            db.session.add(run)
            db.session.commit()
            run_id = run.id

            # Mock prepare_training_data
            mock_prepare.return_value = Path("/tmp/training_data")

            # Mock subprocess
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

                # Execute task
                result = train_lora_task(run_id)

                # Verify result
                assert result["status"] == "completed"
                assert "checkpoint" in result

                # Verify database updates
                db.session.refresh(run)
                assert run.status == "completed"
                assert run.progress == 100
                assert run.training_loss == 0.123

    @patch("server.tasks.training.subprocess.Popen")
    @patch("server.tasks.training.prepare_training_data")
    @patch("pathlib.Path.mkdir")
    @patch("server.api.load_config")
    def test_train_lora_task_failure(
        self, mock_load_config, mock_mkdir, mock_prepare, mock_popen, app
    ):
        """Test failed LoRA training task"""
        # Mock config to use test directories
        mock_load_config.return_value = {
            "model": {"cache_dir": "/tmp/imagineer/models"},
            "training": {"checkpoint_dir": "/tmp/imagineer/checkpoints"},
        }

        with app.app_context():
            # Create training run
            run = TrainingRun(
                name="Test Training",
                dataset_path="/tmp/test_data",
                output_path="/tmp/test_output",
                training_config='{"steps": 100}',
                status="pending",
            )
            db.session.add(run)
            db.session.commit()
            run_id = run.id

            # Mock prepare_training_data
            mock_prepare.return_value = Path("/tmp/training_data")

            # Mock subprocess failure
            mock_process = MagicMock()
            mock_process.stdout = ["Error occurred"]
            mock_process.wait.return_value = 1
            mock_popen.return_value = mock_process

            # Execute task
            result = train_lora_task(run_id)

            # Verify result
            assert result["status"] == "failed"
            assert "code 1" in result["message"]

            # Verify database updates
            db.session.refresh(run)
            assert run.status == "failed"
            assert run.error_message is not None

    def test_train_lora_task_not_found(self, app):
        """Test training task with non-existent run"""
        with app.app_context():
            result = train_lora_task(99999)
            assert result["status"] == "error"
            assert "not found" in result["message"]

    def test_prepare_training_data(self, app):
        """Test training data preparation"""
        with app.app_context():
            # Create test album with images
            album = Album(name="Test Album", is_training_source=True)
            db.session.add(album)
            db.session.commit()

            # Create test images
            images = []
            import time

            timestamp = int(time.time() * 1000)  # Use timestamp for uniqueness
            for i in range(3):
                image = Image(
                    filename=f"test_{timestamp}_{i}.png",
                    file_path=f"/tmp/test_{timestamp}_{i}.png",
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

            # Create training run
            run = TrainingRun(
                name="Test Training",
                dataset_path="/tmp/test_data",
                output_path="/tmp/test_output",
                training_config=f'{{"album_ids": [{album.id}]}}',
                status="pending",
            )
            db.session.add(run)
            db.session.commit()

            with tempfile.TemporaryDirectory() as temp_dir:
                with patch("server.tasks.training.Path") as mock_path:
                    mock_path.return_value = Path(temp_dir)

                    # Mock image files
                    with patch("pathlib.Path.exists", return_value=True), patch(
                        "shutil.copy2"
                    ) as mock_copy, patch("pathlib.Path.write_text") as mock_write:
                        result = prepare_training_data(run)

                        # Verify directory structure
                        assert Path(result).exists()
                        assert (Path(result) / "images").exists()
                        assert (Path(result) / "captions").exists()

                        # Verify files were processed
                        assert mock_copy.called
                        assert mock_write.called

    def test_prepare_training_data_no_albums(self, app):
        """Test training data preparation with no albums"""
        with app.app_context():
            run = TrainingRun(
                name="Test Training",
                dataset_path="/tmp/test_data",
                output_path="/tmp/test_output",
                training_config='{"album_ids": []}',
                status="pending",
            )
            db.session.add(run)
            db.session.commit()

            with pytest.raises(ValueError, match="No albums specified"):
                prepare_training_data(run)

    def test_prepare_training_data_no_images(self, app):
        """Test training data preparation with no valid images"""
        with app.app_context():
            # Create empty album
            album = Album(name="Empty Album", is_training_source=True)
            db.session.add(album)
            db.session.commit()

            run = TrainingRun(
                name="Test Training",
                dataset_path="/tmp/test_data",
                output_path="/tmp/test_output",
                training_config=f'{{"album_ids": [{album.id}]}}',
                status="pending",
            )
            db.session.add(run)
            db.session.commit()

            with patch("pathlib.Path.exists", return_value=False):
                with pytest.raises(ValueError, match="No valid images found"):
                    prepare_training_data(run)

    def test_cleanup_training_data(self, app):
        """Test training data cleanup"""
        with app.app_context():
            run = TrainingRun(
                name="Test Training",
                dataset_path="/tmp/test_data",
                output_path="/tmp/test_output",
                training_config="{}",
                status="completed",
            )
            db.session.add(run)
            db.session.commit()

            with patch("pathlib.Path.exists", return_value=True), patch(
                "shutil.rmtree"
            ) as mock_rmtree:
                result = cleanup_training_data(run.id)

                assert result["status"] == "success"
                assert mock_rmtree.called

    def test_cleanup_training_data_not_found(self, app):
        """Test cleanup with non-existent training run"""
        with app.app_context():
            result = cleanup_training_data(99999)
            assert result["status"] == "error"
            assert "not found" in result["message"]


class TestTrainingAPI:
    """Test training API endpoints"""

    def test_list_training_runs(self, client):
        """Test listing training runs"""
        response = client.get("/api/training")
        assert response.status_code == 200

        data = response.get_json()
        assert "training_runs" in data
        assert "pagination" in data

    def test_get_training_run(self, client, app):
        """Test getting specific training run"""
        with app.app_context():
            run = TrainingRun(
                name="Test Run",
                dataset_path="/tmp/data",
                output_path="/tmp/output",
                status="pending",
            )
            db.session.add(run)
            db.session.commit()

            response = client.get(f"/api/training/{run.id}")
            assert response.status_code == 200

            data = response.get_json()
            assert data["name"] == "Test Run"

    def test_get_training_run_not_found(self, client):
        """Test getting non-existent training run"""
        response = client.get("/api/training/99999")
        assert response.status_code == 404

    def test_create_training_run(self, client, app, mock_admin_user):
        """Test creating training run (admin)"""
        with app.app_context():
            # Create test album
            album = Album(name="Test Album", is_training_source=True)
            db.session.add(album)
            db.session.commit()

            data = {
                "name": "Test Training",
                "description": "Test description",
                "album_ids": [album.id],
                "config": {"steps": 1000, "rank": 4},
            }

            with patch("server.auth.current_user", mock_admin_user):
                response = client.post("/api/training", json=data)
                assert response.status_code == 201

                data = response.get_json()
                assert data["name"] == "Test Training"

    def test_create_training_run_validation(self, client, mock_admin_user):
        """Test training run creation validation"""
        with patch("server.auth.current_user", mock_admin_user):
            # Missing name
            response = client.post("/api/training", json={"album_ids": [1]})
            assert response.status_code == 400

            # Missing albums
            response = client.post("/api/training", json={"name": "Test"})
            assert response.status_code == 400

    def test_start_training(self, client, app, mock_admin_user):
        """Test starting training run (admin)"""
        with app.app_context():
            run = TrainingRun(
                name="Test Run",
                dataset_path="/tmp/data",
                output_path="/tmp/output",
                status="pending",
            )
            db.session.add(run)
            db.session.commit()

            with patch("server.tasks.training.train_lora_task.delay") as mock_task, patch(
                "server.auth.current_user", mock_admin_user
            ):
                mock_task.return_value = MagicMock(id="task-123")

                response = client.post(f"/api/training/{run.id}/start")
                assert response.status_code == 200

                data = response.get_json()
                assert data["message"] == "Training started"
                assert "task_id" in data

    def test_cancel_training(self, client, app, mock_admin_user):
        """Test cancelling training run (admin)"""
        with app.app_context():
            run = TrainingRun(
                name="Test Run",
                dataset_path="/tmp/data",
                output_path="/tmp/output",
                status="running",
            )
            db.session.add(run)
            db.session.commit()

            with patch("server.auth.current_user", mock_admin_user):
                response = client.post(f"/api/training/{run.id}/cancel")
                assert response.status_code == 200

                data = response.get_json()
                assert data["message"] == "Training cancelled"

                # Verify status updated
                updated_run = db.session.get(TrainingRun, run.id)
                assert updated_run.status == "cancelled"

    def test_list_available_albums(self, client, app):
        """Test listing albums available for training"""
        with app.app_context():
            # Create training source album
            album = Album(name="Training Album", is_training_source=True)
            db.session.add(album)
            db.session.commit()

            response = client.get("/api/training/albums")
            assert response.status_code == 200

            data = response.get_json()
            assert len(data["albums"]) == 1
            assert data["albums"][0]["name"] == "Training Album"

    def test_list_trained_loras(self, client, app):
        """Test listing trained LoRAs"""
        with app.app_context():
            # Create completed training run
            run = TrainingRun(
                name="Test Training",
                dataset_path="/tmp/data",
                output_path="/tmp/output",
                status="completed",
                final_checkpoint="/tmp/checkpoint.safetensors",
                training_loss=0.123,
            )
            db.session.add(run)
            db.session.commit()

            with patch("pathlib.Path.exists", return_value=True), patch(
                "pathlib.Path.stat"
            ) as mock_stat:
                mock_stat.return_value.st_size = 1024

                response = client.get("/api/training/loras")
                assert response.status_code == 200

                data = response.get_json()
                assert len(data["trained_loras"]) == 1
                assert data["trained_loras"][0]["name"] == "Test Training"

    def test_integrate_trained_lora(self, client, app, mock_admin_user):
        """Test integrating trained LoRA (admin)"""
        with app.app_context():
            run = TrainingRun(
                name="Test Training",
                dataset_path="/tmp/data",
                output_path="/tmp/output",
                status="completed",
                final_checkpoint="/tmp/checkpoint.safetensors",
            )
            db.session.add(run)
            db.session.commit()

            with patch("pathlib.Path.exists", return_value=True), patch("shutil.copy2"), patch(
                "pathlib.Path.mkdir"
            ), patch("server.auth.current_user", mock_admin_user):
                response = client.post(f"/api/training/loras/{run.id}/integrate")
                assert response.status_code == 200

                data = response.get_json()
                assert data["message"] == "LoRA integrated successfully"
                assert "lora_path" in data

    def test_training_stats(self, client, app):
        """Test training statistics"""
        with app.app_context():
            # Create various training runs
            runs = [
                TrainingRun(
                    name="Run 1", dataset_path="/tmp", output_path="/tmp", status="completed"
                ),
                TrainingRun(name="Run 2", dataset_path="/tmp", output_path="/tmp", status="failed"),
                TrainingRun(
                    name="Run 3", dataset_path="/tmp", output_path="/tmp", status="running"
                ),
            ]
            for run in runs:
                db.session.add(run)
            db.session.commit()

            response = client.get("/api/training/stats")
            assert response.status_code == 200

            data = response.get_json()
            assert data["total_runs"] == 3
            assert data["completed_runs"] == 1
            assert data["failed_runs"] == 1
            assert data["running_runs"] == 1
            assert abs(data["success_rate"] - 33.333333333333336) < 0.0001
