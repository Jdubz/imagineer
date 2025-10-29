"""
Training pipeline API endpoints
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, abort, jsonify, request

from server.auth import require_admin
from server.database import Album, TrainingRun, db
from server.tasks.training import (
    cleanup_training_data,
    get_model_cache_dir,
    get_training_dataset_root,
    train_lora_task,
    training_log_path,
)

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


def _prepare_training_payload(data: dict) -> tuple[str, str, dict]:
    if not data.get("name"):
        raise TrainingValidationError("Name is required")

    album_ids = _parse_album_ids(data.get("album_ids"))
    config_overrides = data.get("config", {}) or {}
    training_config = {**config_overrides, "album_ids": album_ids}
    description = data.get("description", "")
    return data["name"], description, training_config


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

    return jsonify(
        {
            "training_runs": [run.to_dict() for run in training_runs.items],
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
    return jsonify(run.to_dict())


@training_bp.route("", methods=["POST"])
@require_admin
def create_training_run():
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
    return jsonify(run.to_dict()), 201


@training_bp.route("/<int:run_id>/start", methods=["POST"])
@require_admin
def start_training(run_id):
    """Start training run (admin only)"""
    run = get_training_run_or_404(run_id)

    if run.status not in ["pending", "failed"]:
        return jsonify({"error": "Training run cannot be started"}), 400

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
            "training_run": run.to_dict(),
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
    return jsonify({"message": "Training cancelled", "training_run": run.to_dict()})


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
    """List albums available for training (public)"""
    albums = Album.query.filter(Album.is_training_source.is_(True)).all()
    return jsonify({"albums": [album.to_dict() for album in albums]})


@training_bp.route("/loras", methods=["GET"])
def list_trained_loras():
    """List trained LoRAs (public)"""
    from pathlib import Path

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
                        "checkpoint_path": str(checkpoint_path),
                        "filename": checkpoint_path.name,
                        "training_loss": run.training_loss,
                        "created_at": run.created_at.isoformat() if run.created_at else None,
                        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                        "file_size": (
                            checkpoint_path.stat().st_size if checkpoint_path.exists() else 0
                        ),
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
