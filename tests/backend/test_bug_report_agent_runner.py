import os
from pathlib import Path

import pytest

from server.bug_reports.agent_runner import (
    BugReportAgentConfig,
    BugReportDockerRunner,
)


def _build_config(tmp_path: Path) -> BugReportAgentConfig:
    return BugReportAgentConfig(
        enabled=True,
        docker_image="imagineer-bug-agent:test",
        target_branch="develop",
        timeout_minutes=30,
        log_dir=tmp_path / "logs",
        reports_root=tmp_path / "reports",
        repo_root=tmp_path / "repo",
        git_author_name="Test Agent",
        git_author_email="agent@example.com",
    )


def test_create_container_invokes_bootstrap_script(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config = _build_config(tmp_path)
    config.log_dir.mkdir(parents=True, exist_ok=True)

    bootstrap_path = config.repo_root / "scripts" / "bug_reports" / "agent_bootstrap.sh"
    bootstrap_path.parent.mkdir(parents=True, exist_ok=True)
    bootstrap_path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    os.chmod(bootstrap_path, 0o755)

    runner = BugReportDockerRunner(config)

    log_dir = config.log_dir / "bug_123"
    context_dir = log_dir / "context"
    artifacts_dir = log_dir / "artifacts"

    captured_cmd = {}

    def _fake_check_output(cmd, cwd=None):
        captured_cmd["value"] = cmd
        return b"container-abc123"

    monkeypatch.setattr("subprocess.check_output", _fake_check_output)

    container_id = runner._create_container(  # type: ignore[attr-defined]
        report_id="bug_123",
        log_dir=log_dir,
        context_dir=context_dir,
        artifacts_dir=artifacts_dir,
    )

    assert container_id == "container-abc123"
    assert captured_cmd["value"][-2:] == [
        "/bin/bash",
        "/workspace/repo/scripts/bug_reports/agent_bootstrap.sh",
    ]
