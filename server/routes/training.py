"""
Training pipeline API endpoints
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, abort, current_app, jsonify, request

from server.auth import current_user, require_admin
from server.database import Album, AlbumImage, Image, TrainingRun, db
from server.tasks.training import (
    cleanup_training_data,
    get_model_cache_dir,
    get_training_dataset_root,
    purge_stale_training_artifacts,
    train_lora_task,
    training_log_path,
)
from server.utils.rate_limiter import enforce_rate_limit

logger = logging.getLogger(__name__)

training_bp = Blueprint("training", __name__, url_prefix="/api/training")


class TrainingValidationError(ValueError):
    """Raised when the training payload fails validation."""


def _parse_album_ids(album_ids_raw: object) -> list[int]:
    if not album_ids_raw:
        raise TrainingValidationError("At least one album must be specified")
    try:
        album_ids = [int(album_id) for album_id in album_ids_raw]
    except (TypeError, ValueError) as exc:
        raise TrainingValidationError("album_ids must be a list of integers") from exc

    albums = Album.query.filter(Album.id.in_(album_ids)).all()
    if len(albums) != len(album_ids):
        raise TrainingValidationError("One or more albums not found")
    return album_ids


def _validate_training_parameters(config: dict) -> None:
    """Validate training configuration parameters."""
    # Validate steps
    steps = config.get("steps")
    if steps is not None:
        if not isinstance(steps, (int, float)) or steps < 500 or steps > 5000:
            raise TrainingValidationError("steps must be between 500 and 5000")

    # Validate rank
    rank = config.get("rank")
    if rank is not None:
        if not isinstance(rank, int) or rank < 4 or rank > 32:
            raise TrainingValidationError("rank must be between 4 and 32")

    # Validate alpha
    alpha = config.get("alpha")
    if alpha is not None:
        if not isinstance(alpha, (int, float)) or alpha < 1:
            raise TrainingValidationError("alpha must be >= 1")

    # Validate learning_rate
    learning_rate = config.get("learning_rate")
    if learning_rate is not None:
        if not isinstance(learning_rate, (int, float)) or learning_rate <= 0 or learning_rate > 1:
            raise TrainingValidationError("learning_rate must be between 0 and 1")

    # Validate warmup_steps
    warmup_steps = config.get("warmup_steps")
    if warmup_steps is not None:
        if not isinstance(warmup_steps, int) or warmup_steps < 0:
            raise TrainingValidationError("warmup_steps must be >= 0")

    # Validate gradient_accumulation_steps
    grad_accum = config.get("gradient_accumulation_steps")
    if grad_accum is not None:
        if not isinstance(grad_accum, int) or grad_accum < 1:
            raise TrainingValidationError("gradient_accumulation_steps must be >= 1")

    # Validate boolean flags
    for flag in ["random_flip", "center_crop"]:
        value = config.get(flag)
        if value is not None and not isinstance(value, bool):
            raise TrainingValidationError(f"{flag} must be a boolean")


def _get_training_defaults() -> dict:
    """Get default training parameters from config.yaml."""
    config = getattr(current_app, "config", {})
    training_config = config.get("training", {})
    lora_config = training_config.get("lora", {})

    return {
        "steps": int(training_config.get("max_train_steps", 1500)),
        "rank": int(lora_config.get("rank", 8)),
        "alpha": int(lora_config.get("alpha", 32)),
        "learning_rate": float(training_config.get("learning_rate", 1e-4)),
        "warmup_steps": int(training_config.get("warmup_steps", 100)),
        "gradient_accumulation_steps": int(training_config.get("gradient_accumulation_steps", 4)),
        "random_flip": bool(training_config.get("random_flip", True)),
        "center_crop": bool(training_config.get("center_crop", True)),
    }


def _validate_album_selection(album_ids: list[int]) -> None:
    """Validate that selected albums have sufficient labeled images for training."""
    from server.database import Image, ImageLabel

    total_images = 0
    total_labeled = 0

    for album_id in album_ids:
        album = db.session.get(Album, album_id)
        if not album:
            continue

        # Count labeled images in this album
        labeled_count = (
            db.session.query(ImageLabel)
            .join(ImageLabel.image)
            .join(Image.album_images)
            .filter(AlbumImage.album_id == album.id, ImageLabel.label_type == "caption")
            .count()
        )

        total_images += len(album.album_images)
        total_labeled += labeled_count

    if total_labeled < 20:
        raise TrainingValidationError(
            f"Insufficient labeled images for training. "
            f"Found {total_labeled} labeled images, minimum 20 required. "
            f"Please label more images before starting training."
        )

    if total_labeled < 50:
        logger.warning(
            f"Training dataset has only {total_labeled} labeled images. "
            f"Recommended: 50+ images for better quality. Training may produce poor results."
        )


def _prepare_training_payload(data: dict) -> tuple[str, str, dict]:
    if not data.get("name"):
        raise TrainingValidationError("Name is required")

    album_ids = _parse_album_ids(data.get("album_ids"))

    # Validate album selection has sufficient labeled images
    _validate_album_selection(album_ids)

    # Get defaults and merge with user overrides
    defaults = _get_training_defaults()
    config_overrides = data.get("config", {}) or {}
    training_config = {**defaults, **config_overrides, "album_ids": album_ids}

    # Validate parameters
    _validate_training_parameters(training_config)

    description = data.get("description", "")
    return data["name"], description, training_config


def _training_rate_settings() -> tuple[int, int, int]:
    """Return (limit, window_seconds, max_concurrent_runs) for training starts."""
    limit_default = int(os.environ.get("IMAGINEER_TRAINING_RATE_LIMIT", "4"))
    window_default = int(os.environ.get("IMAGINEER_TRAINING_RATE_WINDOW_SECONDS", "3600"))
    max_concurrent_default = int(os.environ.get("IMAGINEER_TRAINING_MAX_CONCURRENT", "1"))

    config = getattr(current_app, "config", {})
    limit = int(config.get("TRAINING_RATE_LIMIT", limit_default))
    window = int(config.get("TRAINING_RATE_WINDOW_SECONDS", window_default))
    max_concurrent = int(config.get("TRAINING_MAX_CONCURRENT_RUNS", max_concurrent_default))
    return limit, window, max_concurrent


def _is_admin_user() -> bool:
    try:
        return bool(current_user.is_authenticated and current_user.is_admin())
    except Exception:  # pragma: no cover
        return False


def _serialize_training_run(run: TrainingRun, *, include_sensitive: bool) -> dict:
    """Return a sanitized representation of a training run for API responses."""
    payload = run.to_dict(include_sensitive=include_sensitive)

    if not include_sensitive:
        payload["training_config"] = None
        payload["final_checkpoint"] = None
        payload["error_message"] = None

    return payload


def _ensure_directory(preferred: Path, fallback: Path, *, kind: str) -> Path:
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        return preferred
    except OSError as exc:  # pragma: no cover - depends on host FS
        if os.environ.get("FLASK_ENV") == "production":
            raise RuntimeError(f"Unable to create {kind} directory at {preferred}: {exc}") from exc
        logger.warning(
            "Unable to create %s directory %s (%s); falling back to %s for development",
            kind,
            preferred,
            exc,
            fallback,
        )
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def get_training_run_or_404(run_id: int) -> TrainingRun:
    run = db.session.get(TrainingRun, run_id)
    if run is None:
        abort(404)
    return run


@training_bp.route("", methods=["GET"])
def list_training_runs():
    """List all training runs (public)"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    status = request.args.get("status")

    query = TrainingRun.query

    if status:
        query = query.filter(TrainingRun.status == status)

    training_runs = query.order_by(TrainingRun.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    include_sensitive = _is_admin_user()

    return jsonify(
        {
            "training_runs": [
                _serialize_training_run(run, include_sensitive=include_sensitive)
                for run in training_runs.items
            ],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": training_runs.total,
                "pages": training_runs.pages,
                "has_next": training_runs.has_next,
                "has_prev": training_runs.has_prev,
            },
        }
    )


@training_bp.route("/<int:run_id>", methods=["GET"])
def get_training_run(run_id):
    """Get training run details (public)"""
    run = get_training_run_or_404(run_id)
    return jsonify(_serialize_training_run(run, include_sensitive=_is_admin_user()))


@training_bp.route("", methods=["POST"])
@require_admin
def create_training_run():  # noqa: C901
    """Create new training run (admin only)"""
    data = request.json or {}

    try:
        name, description, training_config = _prepare_training_payload(data)
    except TrainingValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    # Create training run
    run = TrainingRun(
        name=name,
        description=description,
        dataset_path="",
        output_path="",
        training_config=json.dumps(training_config),
        status="pending",
        progress=0,
    )

    db.session.add(run)
    db.session.commit()

    # Derive dataset/output locations now that the run has an ID
    dataset_root = get_training_dataset_root()
    output_root = get_model_cache_dir() / "lora"

    dataset_path = _ensure_directory(
        dataset_root / f"training_run_{run.id}",
        Path(f"/tmp/imagineer/training/run_{run.id}"),
        kind="dataset",
    )
    output_path = _ensure_directory(
        output_root / f"trained_{run.id}",
        Path(f"/tmp/imagineer/models/lora/trained_{run.id}"),
        kind="output",
    )

    run.dataset_path = str(dataset_path)
    run.output_path = str(output_path)
    db.session.commit()

    logger.info(f"Created training run {run.id}: {run.name}")
    return jsonify(run.to_dict(include_sensitive=True)), 201


@training_bp.route("/<int:run_id>/start", methods=["POST"])
@require_admin
def start_training(run_id):
    """Start training run (admin only)"""
    run = get_training_run_or_404(run_id)

    if run.status not in ["pending", "failed"]:
        return jsonify({"error": "Training run cannot be started"}), 400

    limit, window_seconds, max_concurrent = _training_rate_settings()
    rate_identifier = getattr(current_user, "email", None) or request.remote_addr or "anonymous"
    rate_limit_response = enforce_rate_limit(
        namespace="training:start",
        limit=limit,
        window_seconds=window_seconds,
        identifier=rate_identifier,
        message=(
            "Too many training jobs have been queued recently. "
            "Please wait before starting another run."
        ),
        logger=logger,
    )
    if rate_limit_response:
        return rate_limit_response

    if max_concurrent > 0:
        active_runs = TrainingRun.query.filter(
            TrainingRun.status.in_(("queued", "running"))
        ).count()
        if active_runs >= max_concurrent:
            logger.warning(
                "Training concurrency limit reached",
                extra={
                    "operation": "training:start",
                    "active_runs": active_runs,
                    "max_concurrent": max_concurrent,
                },
            )
            response = jsonify(
                {
                    "success": False,
                    "error": (
                        "Training is already running. Please wait for current jobs "
                        "to finish before starting another."
                    ),
                    "active_runs": active_runs,
                    "limit": max_concurrent,
                }
            )
            response.headers["Retry-After"] = str(max(1, window_seconds))
            return response, 429

    # Start training task
    task = train_lora_task.delay(run_id)

    # Update run with task ID
    run.status = "queued"
    db.session.commit()

    logger.info(f"Started training run {run_id}: {run.name}")
    return jsonify(
        {
            "message": "Training started",
            "task_id": task.id,
            "training_run": run.to_dict(include_sensitive=True),
        }
    )


@training_bp.route("/<int:run_id>/cancel", methods=["POST"])
@require_admin
def cancel_training(run_id):
    """Cancel training run (admin only)"""
    run = get_training_run_or_404(run_id)

    if run.status not in ["pending", "queued", "running"]:
        return jsonify({"error": "Training run cannot be cancelled"}), 400

    # Update status
    run.status = "cancelled"
    run.error_message = "Cancelled by user"
    run.last_error_at = datetime.now(timezone.utc)
    db.session.commit()

    logger.info(f"Cancelled training run {run_id}: {run.name}")
    return jsonify(
        {"message": "Training cancelled", "training_run": run.to_dict(include_sensitive=True)}
    )


@training_bp.route("/<int:run_id>/cleanup", methods=["POST"])
@require_admin
def cleanup_training(run_id):
    """Clean up training data (admin only)"""
    run = get_training_run_or_404(run_id)

    # Start cleanup task
    task = cleanup_training_data.delay(run_id)

    logger.info(f"Started cleanup for training run {run_id}: {run.name}")
    return jsonify(
        {
            "message": "Cleanup started",
            "task_id": task.id,
        }
    )


@training_bp.route("/artifacts/purge", methods=["POST"])
@require_admin
def purge_training_artifacts():
    """Queue background cleanup of stale training datasets/logs (admin only)."""
    payload = request.get_json(silent=True) or {}
    retention_days = payload.get("retention_days")

    task = purge_stale_training_artifacts.delay(retention_days)
    return (
        jsonify(
            {
                "message": "Training artifact purge started",
                "task_id": task.id,
                "retention_days": retention_days,
            }
        ),
        202,
    )


@training_bp.route("/<int:run_id>/logs", methods=["GET"])
def get_training_logs(run_id):
    """Get training logs (public)"""
    run = get_training_run_or_404(run_id)

    log_path = training_log_path(run)

    tail_lines = request.args.get("tail", 200, type=int)
    tail_lines = max(tail_lines or 0, 0)

    log_exists = log_path.exists()

    if log_exists:
        with log_path.open("r", encoding="utf-8") as log_file:
            lines = log_file.readlines()
        if tail_lines:
            lines = lines[-tail_lines:]
        log_body = "".join(lines)
    else:
        log_body = ""

    return jsonify(
        {
            "training_run_id": run_id,
            "status": run.status,
            "progress": run.progress,
            "error_message": run.error_message,
            "log_path": str(log_path),
            "log_available": log_exists,
            "logs": log_body,
        }
    )


@training_bp.route("/stats", methods=["GET"])
def get_training_stats():
    """Get training statistics (public)"""
    total_runs = TrainingRun.query.count()
    completed_runs = TrainingRun.query.filter(TrainingRun.status == "completed").count()
    failed_runs = TrainingRun.query.filter(TrainingRun.status == "failed").count()
    running_runs = TrainingRun.query.filter(TrainingRun.status == "running").count()

    return jsonify(
        {
            "total_runs": total_runs,
            "completed_runs": completed_runs,
            "failed_runs": failed_runs,
            "running_runs": running_runs,
            "success_rate": (completed_runs / total_runs * 100) if total_runs > 0 else 0,
        }
    )


@training_bp.route("/albums", methods=["GET"])
def list_available_albums():
    """
    List albums available for training (public).

    Returns ALL albums with metadata about their suitability for training:
    - total_images: Total images in album
    - labeled_images: Images with caption labels
    - ready_for_training: Whether album has enough labeled images (20+ recommended)
    """
    from server.database import ImageLabel

    albums = Album.query.all()

    albums_with_metadata = []
    for album in albums:
        # Count images with caption labels
        labeled_count = (
            db.session.query(ImageLabel)
            .join(ImageLabel.image)
            .join(Image.album_images)
            .filter(AlbumImage.album_id == album.id, ImageLabel.label_type == "caption")
            .count()
        )

        total_count = len(album.album_images)

        album_dict = album.to_dict()
        album_dict.update(
            {
                "total_images": total_count,
                "labeled_images": labeled_count,
                "ready_for_training": labeled_count >= 20,  # Minimum recommended
            }
        )
        albums_with_metadata.append(album_dict)

    return jsonify({"albums": albums_with_metadata})


@training_bp.route("/loras", methods=["GET"])
def list_trained_loras():
    """List trained LoRAs (public)"""
    from pathlib import Path

    include_sensitive = _is_admin_user()

    try:
        # Get all completed training runs
        completed_runs = TrainingRun.query.filter(
            TrainingRun.status == "completed", TrainingRun.final_checkpoint.isnot(None)
        ).all()

        trained_loras = []
        for run in completed_runs:
            checkpoint_path = Path(run.final_checkpoint)
            if checkpoint_path.exists():
                trained_loras.append(
                    {
                        "id": run.id,
                        "name": run.name,
                        "description": run.description,
                        "checkpoint_path": str(checkpoint_path) if include_sensitive else None,
                        "filename": checkpoint_path.name,
                        "training_loss": run.training_loss,
                        "created_at": run.created_at.isoformat() if run.created_at else None,
                        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                        "file_size": (
                            checkpoint_path.stat().st_size if checkpoint_path.exists() else 0
                        ),
                        "public_download_available": include_sensitive,
                    }
                )

        return jsonify({"trained_loras": trained_loras})

    except Exception as e:
        logger.error(f"Error listing trained LoRAs: {e}")
        return jsonify({"error": str(e)}), 500


@training_bp.route("/loras/<int:run_id>/integrate", methods=["POST"])
@require_admin
def integrate_trained_lora(run_id):
    """Integrate a trained LoRA into the system (admin only)"""
    import shutil
    from pathlib import Path

    try:
        run = get_training_run_or_404(run_id)

        if run.status != "completed" or not run.final_checkpoint:
            return jsonify({"error": "Training run not completed or no checkpoint available"}), 400

        checkpoint_path = Path(run.final_checkpoint)
        if not checkpoint_path.exists():
            return jsonify({"error": "Checkpoint file not found"}), 404

        # Load config
        from server.api import load_config

        config = load_config()

        # Create destination path in the main LoRA directory
        lora_base_dir = Path(config["model"]["cache_dir"]) / "lora"
        lora_base_dir.mkdir(parents=True, exist_ok=True)

        # Generate a safe filename
        safe_name = "".join(c for c in run.name if c.isalnum() or c in (" ", "-", "_")).rstrip()
        safe_name = safe_name.replace(" ", "_").lower()
        dest_filename = f"{safe_name}_{run.id}.safetensors"
        dest_path = lora_base_dir / dest_filename

        # Copy the checkpoint to the main LoRA directory
        shutil.copy2(checkpoint_path, dest_path)

        # Update the training run with the integrated path
        run.final_checkpoint = str(dest_path)
        db.session.commit()

        logger.info(f"Integrated trained LoRA {run.name} to {dest_path}")

        return jsonify(
            {
                "message": "LoRA integrated successfully",
                "lora_path": str(dest_path),
                "filename": dest_filename,
            }
        )

    except Exception as e:
        logger.error(f"Error integrating LoRA: {e}")
        return jsonify({"error": str(e)}), 500
