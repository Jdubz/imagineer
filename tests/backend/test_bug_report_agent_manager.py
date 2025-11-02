import json
from pathlib import Path
from typing import Optional

import pytest

from server.bug_reports.agent_manager import BugReportAgentManager
from server.bug_reports.agent_runner import BugReportAgentConfig, BugReportAgentResult


class _FakeRunner:
    def __init__(
        self, config: BugReportAgentConfig, *, status: str, summary: Optional[dict] = None
    ):
        self.config = config
        self.status = status
        self.summary = summary

    def run(self, report_id: str, payload: dict) -> BugReportAgentResult:
        log_dir = self.config.log_dir / report_id
        log_dir.mkdir(parents=True, exist_ok=True)
        if self.summary:
            summary_path = log_dir / "artifacts" / "session_summary.json"
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.write_text(json.dumps(self.summary), encoding="utf-8")
        return BugReportAgentResult(
            status=self.status,
            log_dir=log_dir,
            summary=self.summary,
            error=None if self.status == "success" else "failure",
        )


def _build_config(tmp_path: Path, enabled: bool = True) -> BugReportAgentConfig:
    return BugReportAgentConfig(
        enabled=enabled,
        docker_image="imagineer-bug-agent:test",
        target_branch="develop",
        timeout_minutes=1,
        log_dir=tmp_path / "logs",
        reports_root=tmp_path / "reports",
        repo_root=tmp_path / "repo",
        git_author_name="Test Agent",
        git_author_email="agent@example.com",
    )


@pytest.fixture(autouse=True)
def _seed_repo(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    config.log_dir.mkdir(parents=True, exist_ok=True)
    config.reports_root.mkdir(parents=True, exist_ok=True)
    config.repo_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("server.bug_reports.agent_manager._resolve_agent_config", lambda: config)
    return config


def _write_report(tmp_path: Path, report_id: str) -> None:
    report_path = tmp_path / "reports" / f"{report_id}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "report_id": report_id,
        "status": "open",
        "description": "Example bug report",
    }
    report_path.write_text(json.dumps(report), encoding="utf-8")


def test_manager_enqueues_and_marks_resolved(tmp_path, monkeypatch):
    report_id = "bug_20251101_abc123"
    _write_report(tmp_path, report_id)

    monkeypatch.setattr(
        "server.bug_reports.agent_manager.load_report",
        lambda report_id, root: {"report_id": report_id, "description": "Example bug report"},
    )
    monkeypatch.setattr(
        "server.bug_reports.agent_manager.list_reports",
        lambda root, status=None: [],
    )

    updated = {}

    def _fake_update(report_id, root, *, status=None, resolution=None):
        updated["status"] = status
        updated["resolution"] = resolution

    monkeypatch.setattr("server.bug_reports.agent_manager.update_report", _fake_update)

    def _runner_factory(config):
        return _FakeRunner(
            config,
            status="success",
            summary={
                "status": "success",
                "commit": "abc123",
            },
        )

    manager = BugReportAgentManager(runner_factory=_runner_factory)
    manager.enqueue(report_id)
    manager._thread.join(timeout=5)

    assert updated["status"] == "resolved"
    assert updated["resolution"]["agent"]["status"] == "success"
    assert updated["resolution"]["agent"]["commit"] == "abc123"


def test_manager_records_failure(tmp_path, monkeypatch):
    report_id = "bug_failure"
    _write_report(tmp_path, report_id)

    monkeypatch.setattr(
        "server.bug_reports.agent_manager.load_report",
        lambda report_id, root: {"report_id": report_id, "description": "Failing report"},
    )
    monkeypatch.setattr(
        "server.bug_reports.agent_manager.list_reports",
        lambda root, status=None: [],
    )

    updates = []

    def _fake_update(report_id, root, *, status=None, resolution=None):
        updates.append((status, resolution))

    monkeypatch.setattr("server.bug_reports.agent_manager.update_report", _fake_update)

    def _runner_factory(config):
        return _FakeRunner(
            config,
            status="failed",
            summary={"status": "failed", "failure_reason": "boom"},
        )

    manager = BugReportAgentManager(runner_factory=_runner_factory)
    manager.enqueue(report_id)
    manager._thread.join(timeout=5)

    assert updates[-1][0] == "open"
    assert updates[-1][1]["agent"]["status"] == "failed"


def test_manager_no_worker_when_disabled(tmp_path, monkeypatch):
    config = _build_config(tmp_path, enabled=False)
    monkeypatch.setattr("server.bug_reports.agent_manager._resolve_agent_config", lambda: config)
    manager = BugReportAgentManager()
    manager.enqueue("bug_disabled")
    assert manager._thread is None
