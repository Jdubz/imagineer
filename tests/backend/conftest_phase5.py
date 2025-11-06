"""
Additional pytest configuration for Phase 5 training tests
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from server.database import Album, AlbumImage, Image, Label, TrainingRun, db


@pytest.fixture
def sample_training_run(app):
    """Create a sample training run for testing"""
    with app.app_context():
        run = TrainingRun(
            name="Test Training Run",
            description="A test training run",
            dataset_path="/tmp/test_dataset",
            output_path="/tmp/test_output",
            training_config='{"steps": 1000, "rank": 4, "learning_rate": 0.0001}',
            status="pending",
            progress=0,
        )
        db.session.add(run)
        db.session.commit()
        yield run


@pytest.fixture
def sample_completed_training_run(app):
    """Create a completed training run for testing"""
    with app.app_context():
        run = TrainingRun(
            name="Completed Training Run",
            description="A completed training run",
            dataset_path="/tmp/test_dataset",
            output_path="/tmp/test_output",
            training_config='{"steps": 1000, "rank": 4}',
            status="completed",
            progress=100,
            final_checkpoint="/tmp/checkpoint.safetensors",
            training_loss=0.123,
        )
        db.session.add(run)
        db.session.commit()
        yield run


@pytest.fixture
def sample_failed_training_run(app):
    """Create a failed training run for testing"""
    with app.app_context():
        run = TrainingRun(
            name="Failed Training Run",
            description="A failed training run",
            dataset_path="/tmp/test_dataset",
            output_path="/tmp/test_output",
            training_config='{"steps": 1000, "rank": 4}',
            status="failed",
            progress=50,
            error_message="Training failed due to insufficient memory",
        )
        db.session.add(run)
        db.session.commit()
        yield run


@pytest.fixture
def sample_training_album(app):
    """Create a sample album for training"""
    with app.app_context():
        album = Album(
            name="Training Dataset",
            description="A dataset for training",
            is_training_source=True,
        )
        db.session.add(album)
        db.session.commit()
        yield album


@pytest.fixture
def sample_training_album_with_images(app, sample_training_album):
    """Create a training album with images and labels"""
    with app.app_context():
        images = []
        for i in range(5):
            # Create image
            image = Image(
                filename=f"training_image_{i:03d}.png",
                file_path=f"/tmp/training_image_{i:03d}.png",
                prompt=f"Training prompt {i}",
                width=512,
                height=512,
            )
            db.session.add(image)
            db.session.flush()

            # Add to album
            album_image = AlbumImage(
                album_id=sample_training_album.id,
                image_id=image.id,
                added_by="test@example.com",
            )
            db.session.add(album_image)

            # Add caption label
            caption_label = Label(
                image_id=image.id,
                label_text=f"Training caption {i} with detailed description",
                label_type="caption",
                source_model="manual",
            )
            db.session.add(caption_label)

            # Add tag labels
            for tag in ["training", "test", f"category_{i % 3}"]:
                tag_label = Label(
                    image_id=image.id,
                    label_text=tag,
                    label_type="tag",
                    source_model="manual",
                )
                db.session.add(tag_label)

            images.append(image)

        db.session.commit()
        yield sample_training_album, images


@pytest.fixture
def mock_training_subprocess():
    """Mock subprocess for training tasks"""
    with patch("server.tasks.training.subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_process.stdout = [
            "Starting training...",
            "Step 10/100",
            "Step 50/100",
            "Step 100/100",
            "Final loss: 0.123",
        ]
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        yield mock_popen


@pytest.fixture
def mock_training_subprocess_failure():
    """Mock subprocess for failed training tasks"""
    with patch("server.tasks.training.subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_process.stdout = [
            "Starting training...",
            "Error: CUDA out of memory",
        ]
        mock_process.wait.return_value = 1
        mock_popen.return_value = mock_process
        yield mock_popen


@pytest.fixture
def mock_checkpoint_creation():
    """Mock checkpoint file creation"""
    with patch("pathlib.Path.glob") as mock_glob:
        mock_glob.return_value = [Path("/tmp/checkpoint.safetensors")]
        yield mock_glob


@pytest.fixture
def temp_training_directory():
    """Create a temporary directory for training tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_training_config():
    """Sample training configuration"""
    return {
        "steps": 1000,
        "rank": 4,
        "learning_rate": 0.0001,
        "batch_size": 1,
        "gradient_accumulation_steps": 4,
        "lora_alpha": 4,
        "lora_dropout": 0.1,
    }


@pytest.fixture
def sample_training_runs(app):
    """Create multiple training runs for testing"""
    with app.app_context():
        runs = []
        statuses = ["pending", "running", "completed", "failed", "cancelled"]

        for i, status in enumerate(statuses):
            run = TrainingRun(
                name=f"Training Run {i}",
                description=f"Test run with status {status}",
                dataset_path=f"/tmp/dataset_{i}",
                output_path=f"/tmp/output_{i}",
                training_config=json.dumps({"steps": 1000, "rank": 4}),
                status=status,
                progress=20 * i if status != "pending" else 0,
            )

            if status == "completed":
                run.final_checkpoint = f"/tmp/checkpoint_{i}.safetensors"
                run.training_loss = 0.1 + (i * 0.01)
            elif status == "failed":
                run.error_message = f"Error in run {i}"

            db.session.add(run)
            runs.append(run)

        db.session.commit()
        yield runs


@pytest.fixture
def mock_celery_task():
    """Mock Celery task execution"""
    with patch("server.tasks.training.train_lora_task.delay") as mock_task, patch(
        "server.tasks.training.cleanup_training_data.delay"
    ) as mock_cleanup:
        mock_task.return_value = MagicMock(id="task-123")
        mock_cleanup.return_value = MagicMock(id="cleanup-123")
        yield {"train": mock_task, "cleanup": mock_cleanup}


@pytest.fixture
def clean_training_database(app):
    """Clean training database after each test"""
    yield
    with app.app_context():
        # Clean up training runs
        TrainingRun.query.delete()
        db.session.commit()
