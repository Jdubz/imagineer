import builtins
import json
from pathlib import Path
from typing import Any, Dict

import pytest

from server.routes import bug_reports


def _build_payload(**overrides: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "description": "Something went wrong when saving an image.",
        "environment": {"mode": "development", "appVersion": "1.0.0"},
        "clientMeta": {"locationHref": "http://localhost/generate", "userAgent": "TestUA"},
        "appState": {"route": {"pathname": "/generate"}},
        "recentLogs": [
            {"level": "error", "message": "Boom", "args": [], "timestamp": "2025-10-30T00:00:00Z"}
        ],
        "networkEvents": [{"id": "req-1", "method": "GET", "url": "/api/test"}],
    }
    payload.update(overrides)
    return payload


# -----------------------------------------------------------------------------
# Directory resolution helpers
# -----------------------------------------------------------------------------


def test_get_bug_reports_dir_prefers_environment(monkeypatch):
    monkeypatch.setenv("BUG_REPORTS_PATH", "/tmp/from_env")

    def _sentinel():
        raise AssertionError("load_config should not be called when env override is set")

    monkeypatch.setattr(bug_reports, "load_config", _sentinel)

    assert bug_reports.get_bug_reports_dir() == "/tmp/from_env"

    monkeypatch.delenv("BUG_REPORTS_PATH")


def test_get_bug_reports_dir_uses_config_value(monkeypatch):
    monkeypatch.delenv("BUG_REPORTS_PATH", raising=False)

    monkeypatch.setattr(
        bug_reports,
        "load_config",
        lambda: {"bug_reports": {"storage_path": "/tmp/from_config"}},
    )

    assert bug_reports.get_bug_reports_dir() == "/tmp/from_config"


def test_get_bug_reports_dir_falls_back_when_config_errors(monkeypatch):
    monkeypatch.delenv("BUG_REPORTS_PATH", raising=False)

    def _raise():
        raise RuntimeError("boom")

    monkeypatch.setattr(bug_reports, "load_config", _raise)

    assert bug_reports.get_bug_reports_dir() == "/mnt/storage/imagineer/bug_reports"


# -----------------------------------------------------------------------------
# Submission endpoint tests
# -----------------------------------------------------------------------------


def test_submit_bug_report_success(admin_client, monkeypatch, tmp_path):
    storage_dir = tmp_path / "bug_reports"
    monkeypatch.setattr(bug_reports, "get_bug_reports_dir", lambda: str(storage_dir))

    payload = _build_payload()
    headers = {"X-Trace-Id": "abc12345-trace"}

    response = admin_client.post("/api/bug-reports", json=payload, headers=headers)

    assert response.status_code == 201
    body = response.get_json()
    assert body["success"] is True
    assert body["trace_id"] == headers["X-Trace-Id"]

    stored_path = Path(body["stored_at"])
    assert stored_path.parent == storage_dir
    assert stored_path.exists()

    saved_report = json.loads(stored_path.read_text())
    assert saved_report["description"] == payload["description"]
    assert saved_report["environment"] == payload["environment"]
    assert saved_report["clientMeta"] == payload["clientMeta"]
    assert saved_report["appState"] == payload["appState"]
    assert saved_report["recentLogs"] == payload["recentLogs"]
    assert saved_report["networkEvents"] == payload["networkEvents"]
    assert saved_report["status"] == "open"
    assert saved_report["trace_id"] == headers["X-Trace-Id"]
    assert saved_report["report_id"].startswith("bug_")


def test_submit_bug_report_requires_authentication(client):
    response = client.post("/api/bug-reports", json=_build_payload())

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication required"


def test_submit_bug_report_requires_admin(client):
    with client.session_transaction() as session:
        session["_user_id"] = "viewer@example.com"
        session["_fresh"] = True
        session["user"] = {
            "email": "viewer@example.com",
            "name": "Viewer",
            "picture": "",
            "role": None,
        }

    response = client.post("/api/bug-reports", json=_build_payload())

    assert response.status_code == 403
    assert response.get_json()["error"] == "Admin role required"


@pytest.mark.parametrize(
    "payload,expected_error",
    [
        (None, "Request body is required"),
        (_build_payload(), "Description is required"),
    ],
)
def test_submit_bug_report_validation(admin_client, monkeypatch, tmp_path, payload, expected_error):
    monkeypatch.setattr(bug_reports, "get_bug_reports_dir", lambda: str(tmp_path / "reports"))

    if payload is None:
        response = admin_client.post(
            "/api/bug-reports",
            data="null",
            content_type="application/json",
        )
    else:
        json_payload = dict(payload)
        json_payload.pop("description", None)
        response = admin_client.post("/api/bug-reports", json=json_payload)

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == expected_error


def test_submit_bug_report_handles_directory_creation_failure(admin_client, monkeypatch, tmp_path):
    monkeypatch.setattr(bug_reports, "get_bug_reports_dir", lambda: str(tmp_path / "reports"))

    def _raise_makedirs(path, exist_ok=False):
        raise OSError("no permission")

    monkeypatch.setattr(bug_reports.os, "makedirs", _raise_makedirs)

    response = admin_client.post("/api/bug-reports", json=_build_payload())

    assert response.status_code == 500
    body = response.get_json()
    assert body["error"] == "Failed to create bug reports directory"


def test_submit_bug_report_handles_write_failure(admin_client, monkeypatch, tmp_path):
    monkeypatch.setattr(bug_reports, "get_bug_reports_dir", lambda: str(tmp_path / "reports"))

    class _OpenFailure(Exception):
        pass

    def _raise_open(*args, **kwargs):
        raise _OpenFailure("disk full")

    monkeypatch.setattr(builtins, "open", _raise_open)

    response = admin_client.post("/api/bug-reports", json=_build_payload())

    assert response.status_code == 500
    body = response.get_json()
    assert body["error"] == "Failed to save bug report"
