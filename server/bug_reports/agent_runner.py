"""
Docker runner for automated bug report remediation agents.
"""

from __future__ import annotations

import json
import logging
import shlex
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional

logger = logging.getLogger(__name__)


@dataclass
class BugReportAgentResult:
    """Outcome returned by the Docker runner."""

    status: str  # "success" | "failed"
    log_dir: Path
    summary: Optional[dict] = None
    error: Optional[str] = None


@dataclass
class BugReportAgentConfig:
    """Configuration required for launching the remediation agent."""

    enabled: bool
    docker_image: str
    target_branch: str
    timeout_minutes: int
    log_dir: Path
    reports_root: Path
    repo_root: Path
    git_author_name: str
    git_author_email: str
    git_remote_url: Optional[str] = None
    env_passthrough: Optional[Dict[str, str]] = None


class BugReportDockerRunner:
    """
    Executes the remediation workflow inside the configured Docker container.
    """

    CONTEXT_DIR_NAME = "context"
    ARTIFACTS_DIR_NAME = "artifacts"

    def __init__(self, config: BugReportAgentConfig):
        self.config = config

    def run(self, report_id: str, report_payload: dict) -> BugReportAgentResult:
        log_dir = self.config.log_dir / report_id
        context_dir = log_dir / self.CONTEXT_DIR_NAME
        artifacts_dir = log_dir / self.ARTIFACTS_DIR_NAME

        log_dir.mkdir(parents=True, exist_ok=True)
        context_dir.mkdir(parents=True, exist_ok=True)
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        context_path = context_dir / "context.json"
        prompt_path = context_dir / "prompt.txt"
        session_summary = artifacts_dir / "session_summary.json"

        self._write_context(context_path, report_payload)
        self._write_prompt(prompt_path, report_payload)

        container_id = None
        try:
            container_id = self._create_container(
                report_id=report_id,
                log_dir=log_dir,
                context_dir=context_dir,
                artifacts_dir=artifacts_dir,
            )
            self._copy_workspace(container_id)
            self._start_container(container_id)
            summary = self._read_summary(session_summary)
            if not summary:
                return BugReportAgentResult(
                    status="failed",
                    log_dir=log_dir,
                    error="Session summary not produced by agent.",
                )
            if summary.get("status") == "success":
                return BugReportAgentResult(
                    status="success",
                    log_dir=log_dir,
                    summary=summary,
                )
            return BugReportAgentResult(
                status="failed",
                log_dir=log_dir,
                summary=summary,
                error=summary.get("failure_reason", "Agent reported failure."),
            )
        except subprocess.TimeoutExpired:
            self._append_failure_summary(
                session_summary,
                "Agent timed out after " f"{self.config.timeout_minutes} minutes.",
                report_id,
            )
            return BugReportAgentResult(
                status="failed",
                log_dir=log_dir,
                summary=self._read_summary(session_summary),
                error="Agent timed out.",
            )
        except Exception as exc:
            logger.exception("Bug report agent failed for %s: %s", report_id, exc)
            self._append_failure_summary(
                session_summary,
                f"Unhandled agent error: {exc}",
                report_id,
            )
            return BugReportAgentResult(
                status="failed",
                log_dir=log_dir,
                summary=self._read_summary(session_summary),
                error=str(exc),
            )
        finally:
            if container_id:
                self._remove_container(container_id)

    # --------------------------------------------------------------------- utils

    def _write_context(self, path: Path, payload: dict) -> None:
        serialized = json.dumps(payload, indent=2)
        path.write_text(
            serialized + ("\n" if not serialized.endswith("\n") else ""), encoding="utf-8"
        )

    def _write_prompt(self, path: Path, payload: dict) -> None:
        description = payload.get("description", "").strip()
        client_meta = payload.get("clientMeta", {})
        route = client_meta.get("locationHref") or payload.get("appState", {}).get("route", {}).get(
            "pathname"
        )
        prompt = textwrap.dedent(
            f"""
            You are a remediation agent working on the Imagineer repository.
            Address bug report {payload.get("report_id") or ''}.
            Description: {description or 'No description provided.'}
            Route / context: {route or 'Unknown'}

            Steps:
              1. Review the report data in {self.CONTEXT_DIR_NAME}/context.json.
              2. Identify the root cause and implement a fix inside /workspace/repo.
              3. Run the full verification suite (npm lint/tsc/test, black, flake8, pytest).
              4. Commit with a descriptive message referencing the report ID.
                 Push to {self.config.target_branch}.
              5. Summarise the work in the session summary.

            If you cannot complete the work, document why before exiting.
            """
        ).strip()
        path.write_text(prompt + "\n", encoding="utf-8")

    def _create_container(
        self,
        *,
        report_id: str,
        log_dir: Path,
        context_dir: Path,
        artifacts_dir: Path,
    ) -> str:
        env = {
            "REPORT_ID": report_id,
            "TARGET_BRANCH": self.config.target_branch,
            "WORKSPACE_DIR": "/workspace/repo",
            "CONTEXT_PATH": "/workspace/context/context.json",
            "PROMPT_PATH": "/workspace/context/prompt.txt",
            "SESSION_SUMMARY": "/workspace/artifacts/session_summary.json",
            "LOG_DIR": "/workspace/logs",
            "TIMEOUT_MINUTES": str(self.config.timeout_minutes),
            "GIT_AUTHOR_NAME": self.config.git_author_name,
            "GIT_AUTHOR_EMAIL": self.config.git_author_email,
        }

        if self.config.git_remote_url:
            env["GIT_REMOTE_URL"] = self.config.git_remote_url

        if self.config.env_passthrough:
            env.update(self.config.env_passthrough)

        env_args = list(self._iter_env_args(env))
        volume_args = list(
            self._iter_volume_args(
                log_dir=log_dir,
                context_dir=context_dir,
                artifacts_dir=artifacts_dir,
            )
        )

        container_name = f"imagineer-bug-{report_id}".replace("_", "-")
        cmd = [
            "docker",
            "create",
            "--rm",
            "--name",
            container_name,
            *env_args,
            *volume_args,
            self.config.docker_image,
        ]

        logger.info(
            "Creating bug report agent container: %s", " ".join(shlex.quote(part) for part in cmd)
        )
        container_id = subprocess.check_output(cmd, cwd=str(self.config.repo_root)).decode().strip()
        return container_id

    def _iter_env_args(self, env: Dict[str, str]) -> Iterable[str]:
        for key, value in env.items():
            if value is None:
                continue
            yield "-e"
            yield f"{key}={value}"

    def _iter_volume_args(
        self,
        *,
        log_dir: Path,
        context_dir: Path,
        artifacts_dir: Path,
    ) -> Iterable[str]:
        volumes = [
            (log_dir, "/workspace/logs", False),
            (context_dir, "/workspace/context", True),
            (artifacts_dir, "/workspace/artifacts", False),
        ]

        home = Path.home()
        optional_mounts = [
            (home / ".ssh", "/home/worker/.ssh", True),
            (home / ".claude", "/home/worker/.claude", True),
            (home / ".config" / "gcloud", "/home/worker/.config/gcloud", True),
            (home / ".firebase", "/home/worker/.firebase", True),
        ]

        for host_path, container_path, read_only in volumes + optional_mounts:
            if not host_path.exists():
                continue
            host_path.mkdir(parents=True, exist_ok=True)
            yield "-v"
            ro_suffix = ":ro" if read_only else ""
            yield f"{str(host_path.resolve())}:{container_path}{ro_suffix}"

    def _copy_workspace(self, container_id: str) -> None:
        exclusions = [
            "--exclude=.git",
            "--exclude=node_modules",
            "--exclude=venv",
            "--exclude=.venv",
            "--exclude=logs/bug_reports",
            "--exclude=outputs",
            "--exclude=checkpoints",
            "--exclude=__pycache__",
            "--exclude=.mypy_cache",
        ]

        tar_cmd = [
            "tar",
            *exclusions,
            "-C",
            str(self.config.repo_root),
            "-cf",
            "-",
            ".",
        ]
        cp_cmd = ["docker", "cp", "-", f"{container_id}:/workspace/repo"]

        logger.info("Copying workspace into container %s", container_id)
        with subprocess.Popen(  # type: ignore[arg-type]
            tar_cmd,
            stdout=subprocess.PIPE,
        ) as tar_proc:
            with subprocess.Popen(
                cp_cmd,
                stdin=tar_proc.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ) as cp_proc:
                tar_proc.stdout.close()  # type: ignore[union-attr]
                stdout, stderr = cp_proc.communicate()
                if cp_proc.returncode != 0:
                    raise RuntimeError(
                        f"docker cp failed: {stderr.decode().strip() or stdout.decode().strip()}"
                    )
            tar_exit = tar_proc.wait()
            if tar_exit != 0:
                raise RuntimeError("tar exited with status {}".format(tar_exit))

    def _start_container(self, container_id: str) -> None:
        cmd = ["docker", "start", "-a", container_id]
        logger.info("Starting bug report agent container %s", container_id)
        subprocess.run(
            cmd,
            cwd=str(self.config.repo_root),
            check=True,
            timeout=max(60, self.config.timeout_minutes * 60),
        )

    def _read_summary(self, path: Path) -> Optional[dict]:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to parse session summary %s: %s", path, exc)
            return None

    def _append_failure_summary(self, path: Path, reason: str, report_id: str) -> None:
        summary = {
            "report_id": report_id,
            "status": "failed",
            "failure_reason": reason,
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        except Exception as exc:
            logger.error("Unable to write failure summary for %s: %s", report_id, exc)

    def _remove_container(self, container_id: str) -> None:
        try:
            subprocess.run(
                ["docker", "rm", "-f", container_id],
                cwd=str(self.config.repo_root),
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            logger.warning("Failed to remove container %s", container_id, exc_info=True)
