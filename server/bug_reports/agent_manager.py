"""
Coordinator for automated bug report remediation agents.
"""

from __future__ import annotations

import fcntl
import logging
import os
import threading
from collections import deque
from pathlib import Path
from typing import Callable, Deque, Optional, Set

from server.bug_reports.agent_runner import (
    BugReportAgentConfig,
    BugReportDockerRunner,
)
from server.config_loader import PROJECT_ROOT, load_config
from server.services import bug_reports as bug_report_service

logger = logging.getLogger(__name__)


def _string_to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_reports_root() -> Path:
    env_override = os.getenv("BUG_REPORTS_PATH")
    if env_override:
        return Path(env_override).expanduser()
    try:
        config = load_config()
        storage_path = config.get("bug_reports", {}).get("storage_path")
        if storage_path:
            return Path(storage_path).expanduser()
    except Exception:
        logger.warning("Falling back to default bug report directory", exc_info=True)
    return Path("/mnt/storage/imagineer/bug_reports").expanduser()


def _resolve_agent_config() -> BugReportAgentConfig:
    config_dict = {}
    try:
        config_dict = load_config() or {}
    except Exception:
        logger.warning("Unable to load imagineer config; using defaults.", exc_info=True)

    agent_cfg = (
        config_dict.get("bug_reports", {}).get("agent", {}) if isinstance(config_dict, dict) else {}
    )

    enabled_env = os.getenv("BUG_REPORT_AGENT_ENABLED")
    enabled = _string_to_bool(enabled_env) if enabled_env else bool(agent_cfg.get("enabled", True))

    docker_image = os.getenv(
        "BUG_REPORT_AGENT_IMAGE",
        agent_cfg.get("docker_image", "ghcr.io/jdubz/imagineer/bug-cli:latest"),
    )
    target_branch = os.getenv(
        "BUG_REPORT_AGENT_BRANCH",
        agent_cfg.get("target_branch", "develop"),
    )
    timeout_minutes = int(
        os.getenv(
            "BUG_REPORT_AGENT_TIMEOUT",
            agent_cfg.get("timeout_minutes", 60),
        )
    )
    log_dir = Path(
        os.getenv(
            "BUG_REPORT_AGENT_LOG_DIR",
            agent_cfg.get("log_dir", PROJECT_ROOT / "logs" / "bug_reports"),
        )
    )

    git_author_name = os.getenv(
        "BUG_REPORT_AGENT_GIT_NAME",
        agent_cfg.get("git_author_name", "Imagineer Bug Agent"),
    )
    git_author_email = os.getenv(
        "BUG_REPORT_AGENT_GIT_EMAIL",
        agent_cfg.get("git_author_email", "agent@imagineer.local"),
    )

    git_remote_url = os.getenv("BUG_REPORT_AGENT_REMOTE")

    env_passthrough_keys = agent_cfg.get("env_passthrough", [])
    env_passthrough = {
        key: os.environ[key] for key in env_passthrough_keys if key in os.environ
    } or None

    log_dir = (PROJECT_ROOT / log_dir) if not log_dir.is_absolute() else log_dir

    return BugReportAgentConfig(
        enabled=enabled,
        docker_image=docker_image,
        target_branch=target_branch,
        timeout_minutes=timeout_minutes,
        log_dir=log_dir.expanduser(),
        reports_root=_resolve_reports_root(),
        repo_root=PROJECT_ROOT,
        git_author_name=git_author_name,
        git_author_email=git_author_email,
        git_remote_url=git_remote_url,
        env_passthrough=env_passthrough,
    )


class BugReportAgentManager:
    """
    Single-concurrency manager that coordinates remediation agents.

    Uses a cross-process file lock to ensure only one agent worker runs
    across all Gunicorn worker processes.
    """

    def __init__(
        self,
        *,
        runner_factory: Optional[Callable[[BugReportAgentConfig], BugReportDockerRunner]] = None,
    ):
        self._config = _resolve_agent_config()
        self._runner_factory = runner_factory or (lambda cfg: BugReportDockerRunner(cfg))
        self._queue: Deque[str] = deque()
        self._lock = threading.Lock()
        self._active = False
        self._thread: Optional[threading.Thread] = None
        self._inflight: Set[str] = set()
        self._recent_failures: Set[str] = set()

        # Cross-process lock to prevent multiple Gunicorn workers from running agents concurrently
        self._lock_file_path = self._config.log_dir / ".agent_worker.lock"
        self._lock_file_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_file: Optional[int] = None

    def refresh_config(self) -> None:
        """Reload configuration from disk/environment."""
        with self._lock:
            self._config = _resolve_agent_config()

    def enqueue(self, report_id: str) -> None:
        """Add a report to the queue and spin up the worker."""
        with self._lock:
            self._recent_failures.discard(report_id)
            if report_id not in self._queue:
                self._queue.appendleft(report_id)
            if not self._config.enabled:
                logger.debug(
                    "Bug report agent disabled; skipping enqueue for %s",
                    report_id,
                )
                return
            if not self._active:
                self._start_worker()

    # ------------------------------------------------------------------ internal

    def _acquire_cross_process_lock(self) -> bool:
        """
        Attempt to acquire a cross-process lock using flock.
        Returns True if lock was acquired, False if another process holds it.
        """
        try:
            self._lock_file = os.open(str(self._lock_file_path), os.O_CREAT | os.O_RDWR, 0o644)
            fcntl.flock(self._lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            logger.info("Acquired cross-process agent worker lock")
            return True
        except (OSError, IOError) as exc:
            logger.debug("Could not acquire cross-process lock: %s", exc)
            if self._lock_file is not None:
                try:
                    os.close(self._lock_file)
                except Exception:
                    pass
                self._lock_file = None
            return False

    def _release_cross_process_lock(self) -> None:
        """Release the cross-process lock."""
        if self._lock_file is not None:
            try:
                fcntl.flock(self._lock_file, fcntl.LOCK_UN)
                os.close(self._lock_file)
                logger.info("Released cross-process agent worker lock")
            except Exception as exc:
                logger.warning("Failed to release cross-process lock: %s", exc)
            finally:
                self._lock_file = None

    def _start_worker(self) -> None:
        self._active = True
        self._thread = threading.Thread(target=self._run, name="bug-report-agent", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        # Attempt to acquire cross-process lock
        if not self._acquire_cross_process_lock():
            logger.info("Another agent worker is already running in a different process. Exiting.")
            with self._lock:
                self._active = False
            return

        try:
            logger.info("Bug report agent worker started")
            while True:
                with self._lock:
                    if not self._config.enabled:
                        logger.info("Bug report agent disabled; worker exiting")
                        self._active = False
                        return
                    next_report = self._select_next_report()
                    if not next_report:
                        logger.info("No queued bug reports. Worker exiting.")
                        self._active = False
                        return
                    self._inflight.add(next_report)

                try:
                    self._process_report(next_report)
                except Exception:  # pragma: no cover - defensive
                    logger.exception("Unhandled agent error for report %s", next_report)
                finally:
                    with self._lock:
                        self._inflight.discard(next_report)
        finally:
            self._release_cross_process_lock()

    def _select_next_report(self) -> Optional[str]:
        while self._queue:
            candidate = self._queue.popleft()
            if candidate in self._inflight or candidate in self._recent_failures:
                continue
            return candidate

        # Fallback: pull pending automation reports from database
        # Note: Requires Flask app context
        try:
            from flask import current_app

            if current_app:
                pending_reports = bug_report_service.get_pending_automation_reports(limit=10)
                for report in pending_reports:
                    if (
                        report.report_id in self._inflight
                        or report.report_id in self._recent_failures
                    ):
                        continue
                    return report.report_id
        except Exception as exc:
            logger.debug("Database fallback not available (no app context): %s", exc)
        return None

    def _process_report(self, report_id: str) -> None:
        # Load from database - requires app context
        try:
            from flask import current_app

            # Check if app context exists
            try:
                _ = current_app._get_current_object()
                has_context = True
            except RuntimeError:
                has_context = False

            if not has_context:
                logger.warning(
                    "No Flask app context for bug report %s; cannot access database",
                    report_id,
                )
                return

            bug_report = bug_report_service.get_bug_report(report_id)
            if not bug_report:
                logger.warning("Bug report %s no longer exists; skipping.", report_id)
                return

            # Convert to payload format expected by runner
            payload = bug_report.to_dict(include_context=True)

            # Increment automation attempts counter
            bug_report_service.increment_automation_attempts(report_id)

        except Exception as exc:
            logger.error("Failed to load bug report %s from database: %s", report_id, exc)
            return

        runner = self._runner_factory(self._config)
        result = runner.run(report_id, payload)

        # Prepare resolution notes
        resolution_data = {
            "agent": {
                "status": result.status,
                "log_dir": str(result.log_dir),
            }
        }
        if result.summary:
            resolution_data["agent"]["summary"] = result.summary  # type: ignore[index]
        if result.error:
            resolution_data["agent"]["error"] = result.error  # type: ignore[index]

        import json

        resolution_notes = json.dumps(resolution_data)

        if result.status == "success":
            commit_sha = (result.summary or {}).get("commit")
            try:
                bug_report_service.update_bug_report_status(
                    report_id=report_id,
                    status="resolved",
                    actor_id="bug-agent",
                    resolution_notes=resolution_notes,
                    resolution_commit_sha=commit_sha,
                )
                bug_report_service.add_bug_report_event(
                    report_id=report_id,
                    event_type="agent_run",
                    event_data={"result": "success", "commit_sha": commit_sha},
                    actor_id="bug-agent",
                    actor_type="agent",
                )
                logger.info("Bug report %s resolved by agent.", report_id)
            except Exception as exc:
                logger.error("Failed to mark bug report %s resolved: %s", report_id, exc)
        else:
            with self._lock:
                self._recent_failures.add(report_id)
            try:
                bug_report_service.add_bug_report_event(
                    report_id=report_id,
                    event_type="agent_run",
                    event_data={"result": "failure", "error": result.error},
                    actor_id="bug-agent",
                    actor_type="agent",
                )
                logger.info("Bug report %s left open after agent failure.", report_id)
            except Exception as exc:
                logger.error("Failed to update bug report %s after failure: %s", report_id, exc)


# -----------------------------------------------------------------------------
# Global helpers
# -----------------------------------------------------------------------------

_MANAGER: Optional[BugReportAgentManager] = None


def get_bug_report_agent_manager() -> BugReportAgentManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = BugReportAgentManager()
    return _MANAGER


def refresh_bug_report_agent_config() -> None:
    get_bug_report_agent_manager().refresh_config()
