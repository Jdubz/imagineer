"""
Training pipeline API endpoints
"""

import json
import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from server.auth import current_user, require_admin
from server.database import Album, TrainingRun, db
from server.tasks.training import cleanup_training_data, train_lora_task

logger = logging.getLogger(__name__)

training_bp = Blueprint("training", __name__, url_prefix="/api/training")


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
    run = TrainingRun.query.get_or_404(run_id)
    return jsonify(run.to_dict())


@training_bp.route("", methods=["POST"])
@require_admin
def create_training_run():
    """Create new training run (admin only)"""
    data = request.json

    # Validate required fields
    if not data.get("name"):
        return jsonify({"error": "Name is required"}), 400

    if not data.get("album_ids"):
        return jsonify({"error": "At least one album must be specified"}), 400

    # Validate albums exist
    album_ids = data["album_ids"]
    albums = Album.query.filter(Album.id.in_(album_ids)).all()
    if len(albums) != len(album_ids):
        return jsonify({"error": "One or more albums not found"}), 400

    # Create training run
    run = TrainingRun(
        name=data["name"],
        description=data.get("description", ""),
        dataset_path="",  # Will be set by prepare_training_data
        output_path=f"/mnt/speedy/imagineer/models/lora/trained_{len(TrainingRun.query.all()) + 1}",
        training_config=json.dumps(data.get("config", {})),
        status="pending",
        progress=0,
    )

    db.session.add(run)
    db.session.commit()

    logger.info(f"Created training run {run.id}: {run.name}")
    return jsonify(run.to_dict()), 201


@training_bp.route("/<int:run_id>/start", methods=["POST"])
@require_admin
def start_training(run_id):
    """Start training run (admin only)"""
    run = TrainingRun.query.get_or_404(run_id)

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
    run = TrainingRun.query.get_or_404(run_id)

    if run.status not in ["pending", "queued", "running"]:
        return jsonify({"error": "Training run cannot be cancelled"}), 400

    # Update status
    run.status = "cancelled"
    run.error_message = "Cancelled by user"
    run.last_error_at = datetime.utcnow()
    db.session.commit()

    logger.info(f"Cancelled training run {run_id}: {run.name}")
    return jsonify({"message": "Training cancelled", "training_run": run.to_dict()})


@training_bp.route("/<int:run_id>/cleanup", methods=["POST"])
@require_admin
def cleanup_training(run_id):
    """Clean up training data (admin only)"""
    run = TrainingRun.query.get_or_404(run_id)

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
    run = TrainingRun.query.get_or_404(run_id)

    # For now, return basic info
    # In a full implementation, you'd store logs in the database
    return jsonify(
        {
            "training_run_id": run_id,
            "status": run.status,
            "progress": run.progress,
            "error_message": run.error_message,
            "logs": "Logs not yet implemented",  # TODO: Implement log storage
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
    albums = Album.query.filter(Album.is_training_source == True).all()
    return jsonify({"albums": [album.to_dict() for album in albums]})


@training_bp.route("/loras", methods=["GET"])
def list_trained_loras():
    """List trained LoRAs (public)"""
    import os
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
        run = TrainingRun.query.get_or_404(run_id)

        if run.status != "completed" or not run.final_checkpoint:
            return jsonify({"error": "Training run not completed or no checkpoint available"}), 400

        checkpoint_path = Path(run.final_checkpoint)
        if not checkpoint_path.exists():
            return jsonify({"error": "Checkpoint file not found"}), 404

        # Create destination path in the main LoRA directory
        lora_base_dir = Path("/mnt/speedy/imagineer/models/lora")
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
