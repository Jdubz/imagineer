# Celery Worker Expectations

**Last updated:** 2025-10-30  
**Audience:** SRE / Operations / Backend on-call  

This guide documents how Imagineer uses Celery, the queues we expect to be online,
and the resource envelopes needed to keep inference, training, and background
maintenance healthy in production.

---

## Quick Overview

| Queue       | Purpose                                  | Default Concurrency | Recommended Memory | Notes |
|-------------|-------------------------------------------|---------------------|--------------------|-------|
| `default`   | Lightweight tasks & maintenance jobs      | 2                   | 512 MB             | Hosts beat-driven disk sampling & low-cost jobs. |
| `training`  | LoRA / fine-tune orchestration            | 1                   | 8 GB               | GPU or high-memory CPU. Timeouts: 30 min hard. |
| `scraping`  | Dataset ingestion, web scraping           | 2                   | 2 GB               | Handles network-heavy collectors; rate-limit externally. |
| `labeling`  | Async metadata & labeling pipelines       | 4                   | 1 GB               | Burst traffic from admin labeling endpoints. |

All queues use:

- `task_acks_late = true` (workers acknowledge after completion)
- `worker_prefetch_multiplier = 1` (strict fairness)
- `task_soft_time_limit = 25m`, `task_time_limit = 30m`

Environment variables:

| Variable | Purpose | Default |
|----------|---------|---------|
| `CELERY_BROKER_URL` | Redis URL for broker | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | Redis URL for results | `redis://localhost:6379/0` |
| `IMAGINEER_MAINTENANCE_QUEUE` | Queue name for maintenance jobs | `default` |
| `IMAGINEER_PURGE_TRAINING_HOUR` | Cron hour for stale training purge | `3` (UTC) |
| `IMAGINEER_PURGE_SCRAPE_HOUR` | Cron hour for stale scrape purge | `4` (UTC) |
| `IMAGINEER_DISK_SAMPLE_HOURS` | Cron interval (hours) for disk stats | `6` |

---

## Worker Sizing & Placement

### Production

- **Broker / Backend:** Managed Redis (>= Standard, persistence ON).  
- **Training queue:** Dedicated GPU node or large CPU node (8 vCPU / 16 GB RAM).
  Launch with `--concurrency=1` to avoid multi-job GPU contention.
- **Scraping queue:** CPU node with outbound internet access, `--concurrency=2`.
- **Labeling queue:** Co-locate with API tier or default worker; `--concurrency=4`.
- **Default queue:** Runs beat + low-cost jobs. Co-locate with API or labeling worker.

CPU sizing rule of thumb: `concurrency = min(vCPU, configured concurrency)`. Memory
should allow each task to hold one model checkpoint in RAM plus 30%.

### Staging / Preview Environments

- Use a single worker process with multiple queues:
  ```bash
  celery -A server.celery_app.celery worker \
      --pool=prefork \
      --hostname=preview@%h \
      --loglevel=INFO \
      --concurrency=2 \
      -Q default,scraping,labeling
  ```
- Skip the training queue unless GPU resources exist.  
- Reduce beat frequency via environment overrides to cut Redis chatter.

---

## Deployment Patterns

### Systemd Units

Example unit for the training queue:

```ini
[Unit]
Description=Imagineer Celery Worker (training queue)
After=network.target redis.service

[Service]
Type=simple
Environment="CELERY_BROKER_URL=redis://redis.internal:6379/0"
Environment="IMAGINEER_CONFIG=/etc/imagineer/config.yaml"
WorkingDirectory=/opt/imagineer
ExecStart=/opt/imagineer/venv/bin/celery \
    -A server.celery_app.celery worker \
    --loglevel=INFO \
    --concurrency=1 \
    -Q training
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Add similar units for `scraping`, `labeling`, and `default` queues with the
concurrency guidance above.

### Kubernetes / Helm Snippet

```yaml
workers:
  brokerUrl: redis://redis.default.svc.cluster.local:6379/0

  training:
    replicas: 1
    resources:
      requests: { cpu: "2", memory: "12Gi", nvidia.com/gpu: 1 }
      limits:   { cpu: "4", memory: "16Gi", nvidia.com/gpu: 1 }
    args: ["-A", "server.celery_app.celery", "worker", "--loglevel=INFO", "-Q", "training", "--concurrency=1"]

  scraping:
    replicas: 1
    resources:
      requests: { cpu: "500m", memory: "1Gi" }
      limits:   { cpu: "2", memory: "2Gi" }
    args: ["-A", "server.celery_app.celery", "worker", "--loglevel=INFO", "-Q", "scraping", "--concurrency=2"]

  default:
    replicas: 1
    args: ["-A", "server.celery_app.celery", "worker", "--loglevel=INFO", "-Q", "default,labeling", "--concurrency=4"]
```

Remember to deploy `celery beat` (or enable `--beat` on the default worker) if
you rely on scheduled maintenance tasks. In production we recommend a dedicated
beat pod / service for predictable scheduling.

---

## Monitoring & Alerting

- Track queue lengths (Redis list size) and worker heartbeats via Prometheus +
  Celery Exporter or the Redis `celery` events stream.
- Critical alerts:
  - Queue length > 25 for >15 minutes (scraping/labeling)
  - Training queue idle > 6 hours during active training campaign
  - Beat failures (no `record_disk_usage` task run in 12 hours)
- Log aggregation should capture the structured fields added in
  `server/logging_config.py` including `operation=config_reload` and
  queue names.

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Tasks stuck in `PENDING` | Worker offline or queue mis-typed | Check `celery inspect active`; ensure worker subscribed to queue name. |
| Frequent `SoftTimeLimitExceeded` | Concurrency too high or model download cost | Lower concurrency, pre-warm checkpoints, or move task to dedicated node. |
| Redis memory spikes | Prefetch or orphaned results store | Verify `worker_prefetch_multiplier=1`, tune `CELERY_RESULT_EXPIRES`. |
| Beat tasks not running | Beat not deployed or clock skew | Deploy dedicated beat service; enforce NTP on worker nodes. |

Need deeper help? Page `#imagineer-backend` or consult `docs/deployment/DEPLOYMENT_README.md`.

---

## References

- Source: `server/celery_app.py`
- Tasks: `server/tasks/{training,scraping,labeling,maintenance}.py`
- Config: `config.yaml`, `IMAGINEER_*` environment variables
