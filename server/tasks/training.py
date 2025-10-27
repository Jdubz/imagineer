"""
LoRA training task integration
"""

import hashlib
import json
import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from server.celery_app import celery
from server.database import Album, AlbumImage, Image, TrainingRun, db

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="tasks.train_lora")
def train_lora_task(self, training_run_id):
    """
    Execute LoRA training from albums.

    Args:
        training_run_id: Database ID of training run
    """
    from server.api import app

    with app.app_context():
        run = TrainingRun.query.get(training_run_id)
        if not run:
            return {"status": "error", "message": "Training run not found"}

        run.status = "running"
        run.started_at = datetime.utcnow()
        db.session.commit()

        logger.info(f"Starting training run {training_run_id}: {run.name}")

        try:
            # Prepare training data
            training_dir = prepare_training_data(run)

            # Build training command
            output_dir = Path(f"/mnt/speedy/imagineer/models/lora/trained_{training_run_id}")
            output_dir.mkdir(parents=True, exist_ok=True)

            config = json.loads(run.training_config) if run.training_config else {}

            cmd = [
                "python",
                "examples/train_lora.py",
                "--data-dir",
                str(training_dir),
                "--output-dir",
                str(output_dir),
                "--steps",
                str(config.get("steps", 1000)),
                "--rank",
                str(config.get("rank", 4)),
                "--learning-rate",
                str(config.get("learning_rate", 1e-4)),
                "--batch-size",
                str(config.get("batch_size", 1)),
            ]

            logger.info(f"Training command: {' '.join(cmd)}")

            # Execute training
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=Path(__file__).parent.parent.parent,
            )

            # Stream output and update progress
            logs = []
            for line in process.stdout:
                logs.append(line)
                logger.info(f"Training: {line.strip()}")

                # Parse progress
                if "Step" in line and "/" in line:
                    try:
                        # Extract step number (e.g., "Step 100/1000")
                        parts = line.split("Step")[1].split("/")
                        current_step = int(parts[0].strip())
                        total_steps = int(parts[1].split()[0])

                        run.progress = (current_step / total_steps) * 100

                        # Update task progress
                        self.update_state(
                            state="PROGRESS",
                            meta={
                                "current_step": current_step,
                                "total_steps": total_steps,
                                "percentage": run.progress,
                            },
                        )

                        db.session.commit()

                    except (ValueError, IndexError):
                        # Ignore parsing errors
                        pass

            # Wait for completion
            return_code = process.wait()

            if return_code == 0:
                # Training completed successfully
                run.status = "completed"
                run.completed_at = datetime.utcnow()
                run.progress = 100

                # Find the final checkpoint
                checkpoint_files = list(output_dir.glob("*.safetensors"))
                if checkpoint_files:
                    run.final_checkpoint = str(checkpoint_files[0])

                # Parse final loss from logs
                for line in reversed(logs):
                    if "Final loss:" in line:
                        try:
                            loss_value = float(line.split("Final loss:")[1].strip())
                            run.training_loss = loss_value
                            break
                        except (ValueError, IndexError):
                            pass

                db.session.commit()

                logger.info(f"Training completed successfully: {run.name}")
                return {
                    "status": "completed",
                    "message": "Training completed successfully",
                    "checkpoint": run.final_checkpoint,
                }

            else:
                # Training failed
                run.status = "failed"
                run.error_message = f"Training process exited with code {return_code}"
                run.last_error_at = datetime.utcnow()
                db.session.commit()

                logger.error(f"Training failed: {run.name} - {run.error_message}")
                return {
                    "status": "failed",
                    "message": run.error_message,
                }

        except Exception as e:
            # Handle unexpected errors
            run.status = "failed"
            run.error_message = str(e)
            run.last_error_at = datetime.utcnow()
            db.session.commit()

            logger.error(f"Training error: {run.name} - {e}", exc_info=True)
            return {"status": "error", "message": str(e)}


def prepare_training_data(training_run):
    """
    Prepare training data from albums for LoRA training.

    Args:
        training_run: TrainingRun instance

    Returns:
        Path to prepared training directory
    """
    # Parse training config
    config = json.loads(training_run.training_config) if training_run.training_config else {}
    album_ids = config.get("album_ids", [])

    if not album_ids:
        raise ValueError("No albums specified for training")

    # Create training directory
    training_dir = Path(f"/tmp/training_{training_run.id}")
    training_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories for images and captions
    images_dir = training_dir / "images"
    captions_dir = training_dir / "captions"
    images_dir.mkdir(exist_ok=True)
    captions_dir.mkdir(exist_ok=True)

    total_images = 0

    # Process each album
    for album_id in album_ids:
        album = Album.query.get(album_id)
        if not album:
            logger.warning(f"Album {album_id} not found, skipping")
            continue

        # Get all images in album
        album_images = (
            db.session.query(Image).join(AlbumImage).filter(AlbumImage.album_id == album_id).all()
        )

        for image in album_images:
            # Copy image file
            src_path = Path(image.file_path)
            if not src_path.exists():
                logger.warning(f"Image file not found: {src_path}")
                continue

            # Generate unique filename
            file_hash = hashlib.md5(str(image.id).encode()).hexdigest()[:8]
            dst_filename = f"{file_hash}_{image.filename}"
            dst_path = images_dir / dst_filename

            try:
                shutil.copy2(src_path, dst_path)
                total_images += 1

                # Create caption file
                caption_filename = dst_filename.rsplit(".", 1)[0] + ".txt"
                caption_path = captions_dir / caption_filename

                # Get caption from labels
                caption_labels = [label for label in image.labels if label.label_type == "caption"]

                if caption_labels:
                    caption_text = caption_labels[0].label_text
                else:
                    # Fallback to prompt or filename
                    caption_text = image.prompt or image.filename

                caption_path.write_text(caption_text, encoding="utf-8")

            except Exception as e:
                logger.error(f"Error processing image {image.id}: {e}")
                continue

    if total_images == 0:
        raise ValueError("No valid images found in specified albums")

    logger.info(f"Prepared {total_images} images for training in {training_dir}")
    return training_dir


@celery.task(name="tasks.cleanup_training_data")
def cleanup_training_data(training_run_id):
    """
    Clean up temporary training data.

    Args:
        training_run_id: Database ID of training run
    """
    from server.api import app

    with app.app_context():
        run = TrainingRun.query.get(training_run_id)
        if not run:
            return {"status": "error", "message": "Training run not found"}

        try:
            # Clean up temporary training directory
            training_dir = Path(f"/tmp/training_{training_run_id}")
            if training_dir.exists():
                shutil.rmtree(training_dir)
                logger.info(f"Cleaned up training data for run {training_run_id}")

            return {"status": "success", "message": "Training data cleaned up"}

        except Exception as e:
            logger.error(f"Error cleaning up training data: {e}")
            return {"status": "error", "message": str(e)}
