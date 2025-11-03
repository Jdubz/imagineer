# Bug Report System Modernization Plan

**Last updated:** November 3, 2025  
**Status:** Draft ✅

**2025-11-03 Update:** Queue strategy now reuses the in-process worker pattern from the image generation system instead of introducing Celery/Redis dependencies.

## Objective

Replace the current flat-file bug report storage with a database-backed workflow that supports automated remediation agents while capturing richer lifecycle metadata, telemetry links, and deduplication. Deliver a thin status view for humans (CLI/table output), but keep the primary interface optimized for agents.

## Success Criteria

- Bug reports persist in the primary application database with migrations, ORM models, and audit timestamps.
- Reports expose triage metadata (severity, category, assignee, SLA timestamps) and lifecycle events for automated agents.
- API surface (`/api/bug-reports`) allows agents to list, claim, update, mark resolved, and attach notes without touching the filesystem.
- Telemetry correlations (trace IDs, request IDs, release hashes) stored/queried directly from the DB.
- Deduplication mechanism clusters incoming reports and links duplicates to a canonical incident.
- CLI or lightweight status endpoint surfaces at-a-glance open/closed counts and allows human spot checks.

## Scope

### In Scope

- Database schema design + migrations for bug report entities, lifecycle history, deduplication keys, and agent run logs.
- Service layer + repository functions for CRUD operations on bug reports.
- REST API endpoints consumed by remediation agents (list, fetch, claim, resolve, attach notes).
- Background jobs or hooks to enrich reports with telemetry details (trace IDs, release version, request context).
- Deduplication heuristics (stack hash, component+message, time window) with grouping support in the DB.
- CLI enhancements (and/or JSON API) to surface status summaries for humans.
- Migration script to ingest existing JSON reports into the new tables.

### Out of Scope

- Full admin UI dashboards or analytics visualizations (deferred).
- Complex workflow tooling (Kanban, SLA calendars) beyond basic lifecycle timestamps.
- Integration with third-party ticketing systems (e.g., Jira) at this phase.

## Workstreams & Milestones

| Milestone | Description | Deliverables | Target |
|-----------|-------------|--------------|--------|
| **M1: Schema & Migration** | Define DB schema, run migrations, backfill existing JSON reports. | ERD, SQLAlchemy models, Alembic migration, backfill script. | Nov 10 |
| **M2: Service Layer & Telemetry Enrichment** | Implement repository/services for bug reports, link trace IDs, release versions. | CRUD services, telemetry enrichment job/hook. | Nov 14 |
| **M2.5: Queue Integration (In-Process)** | Reuse the existing image generation worker pattern for bug remediation tasks. | Shared queue module, typed payloads, worker wiring, metrics plan. | Nov 16 |
| **M3: Deduplication Engine** | Add normalization + hashing to group duplicates and expose relationships. | Dedup strategy doc, DB columns, automated grouping job. | Nov 18 |
| **M4: Agent-Facing API** | Provide REST endpoints and auth guards tailored for automated agents. | `/api/bug-reports` endpoints, OpenAPI spec updates, auth policies. | Nov 21 |
| **M5: CLI / Status View** | Extend existing CLI to read from DB, produce summaries for humans. | Updated `scripts/bug_reports.py`, documentation, smoke tests. | Nov 24 |
| **M6: Rollout & Cleanup** | Cut over agents to new API, remove flat-file paths, archive legacy JSON. | Deployment playbook, environment toggles, legacy cleanup script. | Nov 26 |

## Implementation Notes

- **Schema**:  
  - `bug_reports`: id (UUID), title, description, severity, category, status (enum), source (`user`, `agent`, `system`), reporter_id, assignee_id, trace_id, request_id, release_sha, duplicate_of_id, created_at, updated_at, resolved_at, sla_due_at.  
  - `bug_report_events`: track lifecycle transitions, notes, agent actions.  
  - `bug_report_dedup`: hash keys + occurrence counts for grouping.
- **Lifecycle**: adopt statuses `new`, `triaged`, `in_progress`, `awaiting_verification`, `resolved`, `closed`. Automated agents update `resolution_notes`, `resolved_at`, attach commit SHAs.
- **Telemetry**: intercept submissions, enrich with current trace ID + release metadata via middleware; allow jobs to populate missing data asynchronously.
- **Deduplication**: start with deterministic hash (stack trace + component + route); allow manual overrides to merge/split groups later.
- **API**:  
  - `GET /api/bug-reports?status=open&assigned_to=agent`  
  - `POST /api/bug-reports` (existing submission path, now DB-backed)  
  - `PATCH /api/bug-reports/:id` for lifecycle updates/resolution metadata  
  - `POST /api/bug-reports/:id/events` for agent logs
- **Agent UX**: provide structured payloads with severity, trace data, dedup group, and convenience fields (repo path hints). Support optimistic locking or claim tokens to prevent duplicate work.
- **Monitoring**: log any failed writes, set up alerts for backlog size (e.g., open > X for Y hours).

## Queue Strategy (Updated November 3, 2025)

- **In-process worker, no Celery**: Mirror the proven pattern from `server/routes/generation.py` that uses Python's `queue.Queue` plus a background thread for image jobs. Bug remediation work will enqueue lightweight payloads (report ID + metadata) into the same abstraction to avoid new infrastructure.
- **Shared queue module**: Extract a reusable helper (e.g., `server/queues/work_queue.py`) that encapsulates enqueue/dequeue, thread lifecycle management, and graceful shutdown hooks so both generation and bug remediation share the same implementation.
- **Typed payloads & metrics**: Define a `BugReportWorkItem` dataclass (report ID, priority, retry count) and surface queue depth/processing durations via the existing admin status endpoint (`/api/admin/status`). Stick with simple logging initially; add Prometheus gauges only if required.
- **Retry semantics**: Failed items remain in the DB as `status='open'` with an error note. The worker re-enqueues them after a configurable cooldown, matching today's `BugReportAgentManager` behaviour without introducing external retry stores.
- **Activation plan**: Once DB-backed submission lands, the worker reads `bug_reports` rows needing automation (e.g., `status IN ('new','triaged')` and `automation_enabled = true`) and hands them off to the Docker runner. Successful runs mark the record resolved and drop any outstanding queue entries.

## Risks & Mitigations

- **Backfill errors**: Validate JSON before insert; run in dry-run + checkpoint batches.
- **Agent regression**: Provide compatibility layer during rollout (API proxies reading old files until agents updated).
- **Performance**: Index trace_id, status, created_at to keep agent queries fast.
- **Data consistency**: enforce foreign keys and cascade when merging duplicates.

## Next Steps

1. Draft schema + ERD, review with backend team.  
2. Implement migrations and run backfill in staging.  
3. Update remediation agent configuration to use new API endpoints.  
4. Document new workflow for operators and update runbooks.  
5. Schedule removal of legacy flat-file cron jobs and storage cleanup.
