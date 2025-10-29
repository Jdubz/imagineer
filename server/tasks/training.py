"""
LoRA training task integration
"""

import hashlib
import json
import logging
import os
import shutil
import subprocess
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

from server.celery_app import celery
from server.database import Album, AlbumImage, Image, TrainingRun, db
from server.utils.file_ops import safe_remove_path

logger = logging.getLogger(__name__)


TRAINING_MAX_DURATION_SECONDS = int(
    os.environ.get("IMAGINEER_TRAINING_TIMEOUT_SECONDS", str(4 * 60 * 60))
)
TRAINING_IDLE_TIMEOUT_SECONDS = int(
    os.environ.get("IMAGINEER_TRAINING_IDLE_TIMEOUT_SECONDS", "900")
)
TRAINING_TERMINATE_GRACE_SECONDS = int(
    os.environ.get("IMAGINEER_TRAINING_TERMINATE_GRACE_SECONDS", "30")
)
TRAINING_LOG_BUFFER_SIZE = int(os.environ.get("IMAGINEER_TRAINING_LOG_BUFFER", "2000"))
TRAINING_RETENTION_DAYS = int(os.environ.get("IMAGINEER_TRAINING_RETENTION_DAYS", "30"))


def get_model_cache_dir() -> Path:
    """Return the configured model cache directory."""
    candidate = os.environ.get("IMAGINEER_MODEL_CACHE_DIR")

    if not candidate:
        from server.api import load_config

        config = load_config()
        candidate = config.get("model", {}).get("cache_dir") if isinstance(config, dict) else None

    if not candidate:
        if os.environ.get("FLASK_ENV") == "production":
            raise RuntimeError(
                "Model cache directory not configured. "
                "Set IMAGINEER_MODEL_CACHE_DIR or add model.cache_dir "
                "to config.yaml."
            )
        candidate = "/tmp/imagineer/models"

    cache_dir = Path(candidate).expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_training_dataset_root() -> Path:
    """Return the configured dataset root for training runs."""
    candidate = os.environ.get("IMAGINEER_DATASET_ROOT")

    if not candidate:
        from server.api import load_config

        config = load_config()
        candidate = config.get("dataset", {}).get("data_dir") if isinstance(config, dict) else None

    if not candidate:
        if os.environ.get("FLASK_ENV") == "production":
            raise RuntimeError(
                "Dataset root not configured. "
                "Set IMAGINEER_DATASET_ROOT or add dataset.data_dir "
                "to config.yaml."
            )
        candidate = "/tmp/imagineer/data/training"

    dataset_root = Path(candidate).expanduser()
    dataset_root.mkdir(parents=True, exist_ok=True)
    return dataset_root


def training_log_path(run: TrainingRun) -> Path:
    """Derive filesystem path for a run's training log."""
    base_dir = Path(run.output_path).parent if run.output_path else get_model_cache_dir() / "lora"

    log_dir = base_dir / "logs"
    return log_dir / f"training_{run.id}.log"


def _cleanup_training_directory(run: TrainingRun) -> None:
    """Remove temporary training data for a run."""
    training_dir = (
        Path(run.dataset_path)
        if run.dataset_path
        else get_training_dataset_root() / f"training_run_{run.id}"
    )
    if training_dir.exists():
        try:
            shutil.rmtree(training_dir)
            logger.info(f"Cleaned up training data for run {run.id}")
        except Exception as exc:  # pragma: no cover - cleanup best effort
            logger.warning(f"Failed to clean training directory {training_dir}: {exc}")


def _register_trained_lora(run: TrainingRun, checkpoint_path: Path) -> None:
    """Insert training output into the LoRA index for discovery."""
    if not checkpoint_path or not checkpoint_path.exists():
        return

    output_dir = Path(run.output_path) if run.output_path else checkpoint_path.parent
    lora_base = output_dir.parent
    index_path = lora_base / "index.json"

    try:
        index = {}
        if index_path.exists():
            with index_path.open("r", encoding="utf-8") as handle:
                index = json.load(handle) or {}

        folder_name = output_dir.name
        entry = index.get(folder_name, {})
        entry.update(
            {
                "filename": checkpoint_path.name,
                "friendly_name": run.name,
                "training_run_id": run.id,
                "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "source": "training",
                "default_weight": entry.get("default_weight", 0.6),
            }
        )
        index[folder_name] = entry

        index_path.parent.mkdir(parents=True, exist_ok=True)
        with index_path.open("w", encoding="utf-8") as handle:
            json.dump(dict(sorted(index.items())), handle, indent=2)
    except Exception as exc:  # pragma: no cover - index updates shouldn't break training
        logger.warning(f"Failed to register trained LoRA in index: {exc}", exc_info=True)


@celery.task(bind=True, name="server.tasks.training.train_lora")
def train_lora_task(self, training_run_id):  # noqa: C901
    """
    Execute LoRA training from albums.

    Args:
        training_run_id: Database ID of training run
    """
    from server.api import app

    with app.app_context():
        run = db.session.get(TrainingRun, training_run_id)
        if not run:
            return {"status": "error", "message": "Training run not found"}

        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        db.session.commit()

        logger.info(f"Starting training run {training_run_id}: {run.name}")

        result = {}
        try:
            # Prepare training data
            training_dir = prepare_training_data(run)
            run.dataset_path = str(training_dir)
            db.session.commit()

            # Build training command
            output_dir = (
                Path(run.output_path)
                if run.output_path
                else get_model_cache_dir() / "lora" / f"trained_{training_run_id}"
            )
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
            log_path = training_log_path(run)
            log_handle = None
            log_buffer: deque[str] = deque(maxlen=TRAINING_LOG_BUFFER_SIZE)
            try:
                log_path.parent.mkdir(parents=True, exist_ok=True)
                log_handle = log_path.open("w", encoding="utf-8")
            except OSError as exc:  # pragma: no cover - log dir issues should not abort training
                logger.warning(
                    "Unable to open training log at %s: %s", log_path, exc, exc_info=True
                )
                log_handle = None

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=Path(__file__).parent.parent.parent,
            )

            start_time = time.monotonic()
            last_output_time = start_time
            timeout_reason: str | None = None

            def _process_training_line(raw_line: str) -> None:
                nonlocal last_output_time
                stripped = raw_line.rstrip("\n")
                last_output_time = time.monotonic()
                log_buffer.append(raw_line)
                if log_handle:
                    log_handle.write(raw_line)
                    log_handle.flush()
                logger.info("Training: %s", stripped)

                if "Step" in raw_line and "/" in raw_line:
                    try:
                        parts = raw_line.split("Step")[1].split("/")
                        current_step = int(parts[0].strip())
                        total_steps = int(parts[1].split()[0])
                        if total_steps > 0:
                            run.progress = (current_step / total_steps) * 100
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
                        pass

            def _stream_training_output() -> None:
                try:
                    if not process.stdout:
                        return
                    stdout_obj = process.stdout
                    if hasattr(stdout_obj, "readline"):
                        iterator = iter(stdout_obj.readline, "")
                    else:
                        iterator = iter(stdout_obj)
                    for line in iterator:
                        if not line:
                            break
                        if not isinstance(line, str):
                            line = str(line)
                        _process_training_line(line)
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.warning("Training log reader error: %s", exc, exc_info=True)
                finally:
                    if process.stdout and hasattr(process.stdout, "close"):
                        try:
                            process.stdout.close()
                        except Exception:  # pragma: no cover - best effort
                            pass

            reader_thread = threading.Thread(
                target=_stream_training_output,
                name=f"train-log-{training_run_id}",
                daemon=True,
            )
            reader_thread.start()

            def _terminate_process(reason: str) -> None:
                nonlocal timeout_reason
                timeout_reason = reason
                logger.error("Training run %s terminating: %s", training_run_id, reason)
                try:
                    process.terminate()
                    try:
                        process.wait(timeout=TRAINING_TERMINATE_GRACE_SECONDS)
                    except subprocess.TimeoutExpired:
                        process.kill()
                except Exception as exc:  # pragma: no cover - termination best effort
                    logger.warning("Failed to terminate training process: %s", exc, exc_info=True)

            while True:
                return_code = process.poll()
                if return_code is not None:
                    break

                now = time.monotonic()
                if (
                    TRAINING_MAX_DURATION_SECONDS > 0
                    and now - start_time > TRAINING_MAX_DURATION_SECONDS
                    and timeout_reason is None
                ):
                    _terminate_process(
                        (
                            "Training exceeded maximum duration of "
                            f"{TRAINING_MAX_DURATION_SECONDS} seconds"
                        )
                    )
                    break

                if (
                    TRAINING_IDLE_TIMEOUT_SECONDS > 0
                    and now - last_output_time > TRAINING_IDLE_TIMEOUT_SECONDS
                    and timeout_reason is None
                ):
                    _terminate_process(
                        (
                            "Training produced no output for "
                            f"{TRAINING_IDLE_TIMEOUT_SECONDS} seconds"
                        )
                    )
                    break

                time.sleep(1)

            reader_thread.join(timeout=TRAINING_TERMINATE_GRACE_SECONDS)

            if timeout_reason:
                raise RuntimeError(timeout_reason)

            if isinstance(process.returncode, int):
                return_code = process.returncode
                if return_code is None:
                    return_code = process.wait()
            else:
                return_code = process.wait()

            if return_code == 0:
                # Training completed successfully
                run.status = "completed"
                run.completed_at = datetime.now(timezone.utc)
                run.progress = 100

                # Find the final checkpoint
                checkpoint_files = list(output_dir.glob("*.safetensors"))
                if checkpoint_files:
                    run.final_checkpoint = str(checkpoint_files[0])

                # Parse final loss from logs
                for line in reversed(log_buffer):
                    if "Final loss:" in line:
                        try:
                            loss_value = float(line.split("Final loss:")[1].strip())
                            run.training_loss = loss_value
                            break
                        except (ValueError, IndexError):
                            pass

                db.session.commit()

                logger.info(f"Training completed successfully: {run.name}")
                if checkpoint_files:
                    _register_trained_lora(run, checkpoint_files[0])
                result = {
                    "status": "completed",
                    "message": "Training completed successfully",
                    "checkpoint": run.final_checkpoint,
                }

            else:
                # Training failed
                run.status = "failed"
                run.error_message = f"Training process exited with code {return_code}"
                run.last_error_at = datetime.now(timezone.utc)
                db.session.commit()

                logger.error(f"Training failed: {run.name} - {run.error_message}")
                result = {
                    "status": "failed",
                    "message": run.error_message,
                }

        except Exception as e:
            # Handle unexpected errors
            run.status = "failed"
            run.error_message = str(e)
            run.last_error_at = datetime.now(timezone.utc)
            db.session.commit()

            logger.error(f"Training error: {run.name} - {e}", exc_info=True)
            result = {"status": "failed", "message": str(e)}

        finally:
            _cleanup_training_directory(run)
            if log_handle:
                try:
                    log_handle.close()
                except Exception:  # pragma: no cover - best effort close
                    pass

        return result


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
    training_dir = (
        Path(training_run.dataset_path)
        if training_run.dataset_path
        else get_training_dataset_root() / f"training_run_{training_run.id}"
    )
    training_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories for images and captions
    images_dir = training_dir / "images"
    captions_dir = training_dir / "captions"
    images_dir.mkdir(exist_ok=True)
    captions_dir.mkdir(exist_ok=True)

    total_images = 0

    # Process each album
    for album_id in album_ids:
        album = db.session.get(Album, album_id)
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


@celery.task(name="server.tasks.training.purge_stale_training_artifacts")
def purge_stale_training_artifacts(retention_days: int | None = None):
    """Delete stale training datasets and logs that fall outside the retention window."""

    from server.api import app

    days = int(retention_days or TRAINING_RETENTION_DAYS)
    if days <= 0:
        return {"status": "skipped", "reason": "retention-disabled"}

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    updated_runs = 0
    logs_removed = 0
    datasets_removed = 0

    with app.app_context():
        candidates = TrainingRun.query.filter(
            TrainingRun.status.in_(["completed", "failed", "cancelled"])
        )
        for run in candidates:
            reference_ts = run.completed_at or run.last_error_at or run.created_at
            if not reference_ts or reference_ts >= cutoff:
                continue

            dataset_removed = False
            if run.dataset_path:
                dataset_path = Path(run.dataset_path)
                dataset_removed = safe_remove_path(dataset_path)
                if dataset_removed:
                    datasets_removed += 1
                    run.dataset_path = ""

            log_removed = safe_remove_path(training_log_path(run))
            if log_removed:
                logs_removed += 1

            if dataset_removed or log_removed:
                updated_runs += 1

        db.session.commit()

    return {
        "status": "success",
        "retention_days": days,
        "runs_updated": updated_runs,
        "datasets_removed": datasets_removed,
        "logs_removed": logs_removed,
    }


@celery.task(name="server.tasks.training.cleanup_training_data")
def cleanup_training_data(training_run_id):
    """
    Clean up temporary training data.

    Args:
        training_run_id: Database ID of training run
    """
    from server.api import app

    with app.app_context():
        run = db.session.get(TrainingRun, training_run_id)
        if not run:
            return {"status": "error", "message": "Training run not found"}

        try:
            # Clean up temporary training directory
            _cleanup_training_directory(run)

            return {"status": "success", "message": "Training data cleaned up"}

        except Exception as e:
            logger.error(f"Error cleaning up training data: {e}")
            return {"status": "error", "message": str(e)}
