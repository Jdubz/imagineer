# Imagineer – Training Operations Guide

This guide covers day-to-day management of LoRA training runs once a job has been created from the admin UI.

## 1. Where assets live

Every training run now exposes its directories directly in the **Training** tab:

- **Dataset directory** – the curated images prepared for the run (`dataset_path`).  
  Use the `Copy` control to grab the full path if you need to inspect or archive the dataset.
- **Output directory** – the folder containing the trained weights (`output_path`).  
  Each run’s final checkpoint appears here as `<run>/model.safetensors`.
- **Final checkpoint** – the exact checkpoint path, shown once the run finishes. You can copy the path into an inference configuration or download it via `scp`.
- **Training configuration** – quick view of effective hyper‑parameters (steps, rank, learning rate, batch size) and the album IDs that seeded the job.

## 2. Logs and troubleshooting

Select **View Logs** on any run to open the live log viewer. The dialog displays:

- Tail of the training log (last 500 lines by default).  
- The absolute `log_path`, which can be copied for offline analysis (`less`, `tail -f`, etc.).

Use the copy button next to the path when you need to pull the full log:  
```bash
scp $SERVER:/tmp/imagineer/models/lora/logs/training_<id>.log .
```

## 3. Retention policy

- **During training** – datasets are staged in `dataset_path`. They are automatically removed after each run finishes or fails (see `cleanup_training_data` task).  
- **Scheduled cleanup** – a nightly Celery Beat job (`server.tasks.training.purge_stale_training_artifacts`) now prunes datasets and logs older than the configured retention window (`TRAINING_RETENTION_DAYS`, default 30 days). Adjust the hour via `IMAGINEER_PURGE_TRAINING_HOUR` if needed.
- **Manual cleanup** – if you need to reclaim disk immediately, click **Cleanup** on a completed/failed run or execute `python scripts/purge_training_artifacts.py --days 30` (pass `--dry-run` to preview). The CLI wraps the same purge logic used by the scheduler.
- **Outputs** – trained weights (`output_path`) remain available until you archive or delete them; they are intentionally retained for reuse.

Recommendation: after confirming that a checkpoint has been promoted or archived, press **Cleanup** so `/tmp/imagineer/data/training/*` stays small.

## 4. Suggested workflow

1. Launch the training run from the admin UI.
2. Monitor progress and logs directly in the run card.
3. When complete, copy the **Final checkpoint** path into your generation config or download the file.
4. Use the **Cleanup** button once assets are archived to keep staging storage tidy.

This UI-driven flow replaces the older manual lookup of paths, reducing time spent grepping logs or guessing where checkpoints were saved. For deeper operational automation (e.g., scheduled pruning of old checkpoints) consider extending this doc with your environment-specific policies.
