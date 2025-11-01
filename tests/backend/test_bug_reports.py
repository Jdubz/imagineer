import builtins
import json
from pathlib import Path
from typing import Any, Dict

import pytest
from jsonschema import Draft202012Validator

from server.routes import bug_reports

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "shared" / "schema"
with (SCHEMA_DIR / "bug_report_submission_request.json").open("r", encoding="utf-8") as fh:
    BUG_REPORT_REQUEST_SCHEMA = json.load(fh)
with (SCHEMA_DIR / "bug_report_submission_response.json").open("r", encoding="utf-8") as fh:
    BUG_REPORT_RESPONSE_SCHEMA = json.load(fh)

BUG_REPORT_REQUEST_VALIDATOR = Draft202012Validator(BUG_REPORT_REQUEST_SCHEMA)
BUG_REPORT_RESPONSE_VALIDATOR = Draft202012Validator(BUG_REPORT_RESPONSE_SCHEMA)
BUG_REPORT_REQUEST_KEYS = tuple(BUG_REPORT_REQUEST_SCHEMA["properties"].keys())


def _build_payload(**overrides: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "description": "Something went wrong when saving an image.",
        "environment": {"mode": "development", "appVersion": "1.0.0"},
        "clientMeta": {"locationHref": "http://localhost/generate", "userAgent": "TestUA"},
        "appState": {"route": {"pathname": "/generate"}},
        "recentLogs": [
            {
                "level": "error",
                "message": "Boom",
                "args": [],
                "timestamp": "2025-10-30T00:00:00Z",
                "serializedArgs": [],
            }
        ],
        "networkEvents": [
            {
                "id": "req-1",
                "method": "GET",
                "url": "/api/test",
                "started_at": "2025-10-30T00:00:00Z",
                "requestHeaders": [{"name": "Accept", "value": "application/json"}],
                "responseHeaders": [{"name": "Content-Type", "value": "application/json"}],
            }
        ],
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
    BUG_REPORT_RESPONSE_VALIDATOR.validate(body)

    stored_path = Path(body["stored_at"])
    assert stored_path.parent == storage_dir
    assert stored_path.exists()

    saved_report = json.loads(stored_path.read_text())
    request_section = {key: saved_report[key] for key in BUG_REPORT_REQUEST_KEYS}
    BUG_REPORT_REQUEST_VALIDATOR.validate(request_section)
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


# -----------------------------------------------------------------------------
# Admin maintenance endpoints
# -----------------------------------------------------------------------------


def _write_bug_report(tmp_path: Path, report_id: str, **overrides: Any) -> Path:
    payload = {
        "report_id": report_id,
        "status": "open",
        "submitted_at": "2025-10-31T12:00:00Z",
        "submitted_by": "admin@example.com",
        "trace_id": "trace-1234",
        "description": "Example report",
    }
    payload.update(overrides)
    path = tmp_path / f"{report_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_list_bug_reports_returns_reports(admin_client, monkeypatch, tmp_path):
    monkeypatch.setattr(bug_reports, "get_bug_reports_dir", lambda: str(tmp_path))
    _write_bug_report(tmp_path, "bug_20251031_a", submitted_at="2025-10-31T12:00:00Z")
    _write_bug_report(
        tmp_path,
        "bug_20251030_b",
        submitted_at="2025-10-30T08:15:00Z",
        status="resolved",
    )

    response = admin_client.get("/api/bug-reports")

    assert response.status_code == 200
    body = response.get_json()
    reports = body["reports"]
    assert len(reports) == 2
    assert reports[0]["report_id"] == "bug_20251031_a"

    # Filter by status
    response_filtered = admin_client.get("/api/bug-reports?status=resolved")
    assert response_filtered.status_code == 200
    filtered_reports = response_filtered.get_json()["reports"]
    assert len(filtered_reports) == 1
    assert filtered_reports[0]["status"] == "resolved"


def test_get_bug_report_detail_returns_payload(admin_client, monkeypatch, tmp_path):
    monkeypatch.setattr(bug_reports, "get_bug_reports_dir", lambda: str(tmp_path))
    _write_bug_report(tmp_path, "bug_20251031_c", description="Detail check")

    response = admin_client.get("/api/bug-reports/bug_20251031_c")

    assert response.status_code == 200
    payload = response.get_json()["report"]
    assert payload["report_id"] == "bug_20251031_c"
    assert payload["description"] == "Detail check"


def test_update_bug_report_status_changes_file(admin_client, monkeypatch, tmp_path):
    monkeypatch.setattr(bug_reports, "get_bug_reports_dir", lambda: str(tmp_path))
    report_path = _write_bug_report(tmp_path, "bug_20251031_d")

    response = admin_client.patch(
        "/api/bug-reports/bug_20251031_d",
        json={"status": "resolved", "resolution": {"note": "Fixed in commit"}},
    )

    assert response.status_code == 200
    payload = response.get_json()["report"]
    assert payload["status"] == "resolved"
    stored = json.loads(report_path.read_text())
    assert stored["status"] == "resolved"
    assert stored["resolution"]["note"] == "Fixed in commit"


def test_delete_bug_report_removes_file(admin_client, monkeypatch, tmp_path):
    monkeypatch.setattr(bug_reports, "get_bug_reports_dir", lambda: str(tmp_path))
    report_path = _write_bug_report(tmp_path, "bug_20251031_e")
    assert report_path.exists()

    response = admin_client.delete("/api/bug-reports/bug_20251031_e")

    assert response.status_code == 200
    assert not report_path.exists()


def test_purge_bug_reports_dry_run(admin_client, monkeypatch, tmp_path):
    monkeypatch.setattr(bug_reports, "get_bug_reports_dir", lambda: str(tmp_path))
    _write_bug_report(tmp_path, "bug_old", submitted_at="2025-09-01T00:00:00Z")
    _write_bug_report(tmp_path, "bug_recent", submitted_at="2025-10-31T00:00:00Z")

    response = admin_client.post(
        "/api/bug-reports/purge",
        json={"older_than_days": 30, "dry_run": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "dry_run"
    assert payload["results"]["matched"] == 1
    assert (tmp_path / "bug_old.json").exists()


def test_purge_bug_reports_deletes_old_files(admin_client, monkeypatch, tmp_path):
    monkeypatch.setattr(bug_reports, "get_bug_reports_dir", lambda: str(tmp_path))
    old_report = _write_bug_report(tmp_path, "bug_old", submitted_at="2025-09-01T00:00:00Z")
    recent_report = _write_bug_report(tmp_path, "bug_recent", submitted_at="2025-10-31T00:00:00Z")

    response = admin_client.post("/api/bug-reports/purge", json={"older_than_days": 30})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"
    assert payload["results"]["deleted"] == 1
    assert not old_report.exists()
    assert recent_report.exists()
