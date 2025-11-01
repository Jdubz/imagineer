from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from server.database import TrainingRun, db
from server.tasks.training import (
    purge_stale_training_artifacts,
    training_log_path,
)


def _create_training_run(*, app, tmp_path: Path, offset_days: int) -> int:
    """Helper to create a completed training run with artifacts."""
    with app.app_context():
        dataset_dir = tmp_path / "dataset"
        output_dir = tmp_path / "output" / "trained"
        dataset_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        run = TrainingRun(
            name="Completed Run",
            dataset_path=str(dataset_dir),
            output_path=str(output_dir / "model.safetensors"),
            training_config="{}",
            status="completed",
            progress=100,
            completed_at=datetime.now(timezone.utc) - timedelta(days=offset_days),
        )
        db.session.add(run)
        db.session.commit()

        log_path = training_log_path(run)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("training log\n", encoding="utf-8")

        return run.id


def test_purge_training_artifacts_dry_run(app, tmp_path):
    run_id = _create_training_run(app=app, tmp_path=tmp_path, offset_days=60)

    result = purge_stale_training_artifacts(retention_days=30, dry_run=True)

    assert result["status"] == "dry_run"
    assert result["runs_matched"] >= 1
    assert result["datasets_marked"] >= 1
    assert result["logs_marked"] >= 1

    dataset_dir = tmp_path / "dataset"
    log_path = tmp_path / "output" / "trained" / "logs" / f"training_{run_id}.log"
    assert dataset_dir.exists()
    assert log_path.exists()

    with app.app_context():
        run = db.session.get(TrainingRun, run_id)
        assert run is not None
        assert run.dataset_path == str(dataset_dir)


def test_purge_training_artifacts_executes_cleanup(app, tmp_path):
    run_id = _create_training_run(app=app, tmp_path=tmp_path, offset_days=60)

    result = purge_stale_training_artifacts(retention_days=30)

    assert result["status"] == "success"
    assert result["datasets_removed"] >= 1
    assert result["logs_removed"] >= 1
    assert result["runs_updated"] >= 1

    dataset_dir = tmp_path / "dataset"
    log_path = tmp_path / "output" / "trained" / "logs" / f"training_{run_id}.log"
    assert not dataset_dir.exists()
    assert not log_path.exists()

    with app.app_context():
        run = db.session.get(TrainingRun, run_id)
        assert run is not None
        assert run.dataset_path == ""
