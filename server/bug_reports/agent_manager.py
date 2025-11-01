"""
Coordinator for automated bug report remediation agents.
"""

from __future__ import annotations

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
from server.bug_reports.storage import (
    BugReportStorageError,
    list_reports,
    load_report,
    update_report,
)
from server.config_loader import PROJECT_ROOT, load_config

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
    """Single-concurrency manager that coordinates remediation agents."""

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

    def _start_worker(self) -> None:
        self._active = True
        self._thread = threading.Thread(target=self._run, name="bug-report-agent", daemon=True)
        self._thread.start()

    def _run(self) -> None:
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

    def _select_next_report(self) -> Optional[str]:
        while self._queue:
            candidate = self._queue.popleft()
            if candidate in self._inflight or candidate in self._recent_failures:
                continue
            return candidate

        # Fallback: pull newest open report from storage.
        summaries = list_reports(self._config.reports_root, status="open")
        for summary in summaries:
            if summary.report_id in self._inflight or summary.report_id in self._recent_failures:
                continue
            return summary.report_id
        return None

    def _process_report(self, report_id: str) -> None:
        try:
            payload = load_report(report_id, self._config.reports_root)
        except FileNotFoundError:
            logger.warning("Bug report %s no longer exists; skipping.", report_id)
            return
        except BugReportStorageError as exc:
            logger.error("Failed to load bug report %s: %s", report_id, exc)
            return

        runner = self._runner_factory(self._config)
        result = runner.run(report_id, payload)

        resolution = {
            "agent": {
                "status": result.status,
                "log_dir": str(result.log_dir),
            }
        }
        if result.summary:
            resolution["agent"]["summary"] = result.summary  # type: ignore[index]
        if result.error:
            resolution["agent"]["error"] = result.error  # type: ignore[index]

        if result.status == "success":
            commit_sha = (result.summary or {}).get("commit")
            resolution["agent"]["commit"] = commit_sha  # type: ignore[index]
            try:
                update_report(
                    report_id,
                    self._config.reports_root,
                    status="resolved",
                    resolution=resolution,
                )
                logger.info("Bug report %s resolved by agent.", report_id)
            except Exception as exc:
                logger.error("Failed to mark bug report %s resolved: %s", report_id, exc)
        else:
            with self._lock:
                self._recent_failures.add(report_id)
            try:
                update_report(
                    report_id,
                    self._config.reports_root,
                    status="open",
                    resolution=resolution,
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
