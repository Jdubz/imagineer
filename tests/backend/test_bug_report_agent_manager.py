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


def test_manager_enqueues_and_marks_resolved(tmp_path, monkeypatch, app):
    """Test agent manager with database - Note: currently skipped due to threading/app context issues"""
    pytest.skip(
        "Agent manager threading with app context requires refactoring - tracked for future work"
    )


def test_manager_records_failure(tmp_path, monkeypatch, app):
    """Test agent manager failure handling - Note: currently skipped due to threading/app context issues"""
    pytest.skip(
        "Agent manager threading with app context requires refactoring - tracked for future work"
    )


def test_manager_no_worker_when_disabled(tmp_path, monkeypatch):
    config = _build_config(tmp_path, enabled=False)
    monkeypatch.setattr("server.bug_reports.agent_manager._resolve_agent_config", lambda: config)
    manager = BugReportAgentManager()
    manager.enqueue("bug_disabled")
    assert manager._thread is None
