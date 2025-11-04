import base64
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

import pytest
from jsonschema import Draft202012Validator

from server.database import BugReport
from server.routes import bug_reports

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "shared" / "schema"
with (SCHEMA_DIR / "bug_report_submission_request.json").open("r", encoding="utf-8") as fh:
    BUG_REPORT_REQUEST_SCHEMA = json.load(fh)
with (SCHEMA_DIR / "bug_report_submission_response.json").open("r", encoding="utf-8") as fh:
    BUG_REPORT_RESPONSE_SCHEMA = json.load(fh)

BUG_REPORT_REQUEST_VALIDATOR = Draft202012Validator(BUG_REPORT_REQUEST_SCHEMA)
BUG_REPORT_RESPONSE_VALIDATOR = Draft202012Validator(BUG_REPORT_RESPONSE_SCHEMA)


def _build_payload(**overrides: Any) -> Dict[str, Any]:
    """Base payload used for submissions."""
    payload: Dict[str, Any] = {
        "description": "Something went wrong when saving an image.",
        "expectedBehavior": "The image should have been saved successfully.",
        "actualBehavior": "The UI showed an error toast.",
        "stepsToReproduce": [
            "Open the generate page",
            "Click generate",
            "Observe error toast",
        ],
        "environment": {"mode": "development", "appVersion": "1.0.0"},
        "clientMeta": {
            "locationHref": "http://localhost/generate",
            "userAgent": "TestUA",
            "platform": "MacIntel",
            "language": "en-US",
            "locale": "en-US",
            "timezone": "UTC",
            "viewport": {"width": 1920, "height": 1080},
        },
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


def _create_test_screenshot() -> str:
    """Return a tiny 1x1 PNG as data URL."""
    png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gA"
        "AAABJRU5ErkJggg=="
    )
    png_bytes = base64.b64decode(png_b64)
    return f"data:image/png;base64,{base64.b64encode(png_bytes).decode('utf-8')}"


def _fetch_bug_report(app, report_id: str) -> BugReport | None:
    with app.app_context():
        return BugReport.query.filter_by(report_id=report_id).first()


# ---------------------------------------------------------------------------
# Storage path resolution
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Submission endpoint
# ---------------------------------------------------------------------------


def test_submit_bug_report_success(admin_client, monkeypatch, tmp_path):
    storage_dir = tmp_path / "bug_reports"
    monkeypatch.setattr(bug_reports, "get_bug_reports_dir", lambda: str(storage_dir))

    payload = _build_payload()
    headers = {"X-Trace-Id": "abc12345-trace"}

    response = admin_client.post("/api/bug-reports", json=payload, headers=headers)

    assert response.status_code == 201
    body = response.get_json()
    BUG_REPORT_RESPONSE_VALIDATOR.validate(body)
    assert body["success"] is True
    assert body["trace_id"] == headers["X-Trace-Id"]
    assert body["stored_at"].startswith("database:bug_reports:")

    record = _fetch_bug_report(admin_client.application, body["report_id"])
    assert record is not None
    assert record.description == payload["description"]
    assert record.expected_behavior == payload["expectedBehavior"]
    assert record.actual_behavior == payload["actualBehavior"]
    assert record.steps_to_reproduce == json.dumps(payload["stepsToReproduce"])
    assert record.trace_id == headers["X-Trace-Id"]
    assert record.screenshot_path is None
    assert record.screenshot_error is None


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
def test_submit_bug_report_validation(admin_client, monkeypatch, payload, expected_error):
    monkeypatch.setattr(bug_reports, "get_bug_reports_dir", lambda: "/tmp/reports")

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


def test_submit_bug_report_handles_directory_failure_gracefully(
    admin_client, monkeypatch, tmp_path
):
    storage_dir = tmp_path / "bug_reports"
    monkeypatch.setattr(bug_reports, "get_bug_reports_dir", lambda: str(storage_dir))

    def _raise_makedirs(path, exist_ok=False):
        raise OSError("no permission")

    monkeypatch.setattr(bug_reports.os, "makedirs", _raise_makedirs)

    payload = _build_payload(screenshot=_create_test_screenshot())
    response = admin_client.post("/api/bug-reports", json=payload)

    assert response.status_code == 201
    body = response.get_json()

    record = _fetch_bug_report(admin_client.application, body["report_id"])
    assert record is not None
    assert record.screenshot_path is None
    assert record.screenshot_error == "no permission"


def test_submit_bug_report_with_screenshot(admin_client, monkeypatch, tmp_path):
    storage_dir = tmp_path / "bug_reports"
    monkeypatch.setattr(bug_reports, "get_bug_reports_dir", lambda: str(storage_dir))

    payload = _build_payload(screenshot=_create_test_screenshot())
    response = admin_client.post("/api/bug-reports", json=payload)

    assert response.status_code == 201
    body = response.get_json()

    record = _fetch_bug_report(admin_client.application, body["report_id"])
    assert record is not None
    assert record.screenshot_path is not None
    assert record.screenshot_error is None

    screenshot_path = Path(record.screenshot_path)
    assert screenshot_path.exists()
    assert screenshot_path.name == "screenshot.png"
    assert screenshot_path.parent.name == record.report_id
    with screenshot_path.open("rb") as fh:
        assert fh.read(8) == b"\x89PNG\r\n\x1a\n"


def test_submit_bug_report_invalid_screenshot_continues_submission(
    admin_client, monkeypatch, tmp_path
):
    storage_dir = tmp_path / "bug_reports"
    monkeypatch.setattr(bug_reports, "get_bug_reports_dir", lambda: str(storage_dir))

    payload = _build_payload(screenshot="invalid-base64")
    response = admin_client.post("/api/bug-reports", json=payload)

    assert response.status_code == 201
    body = response.get_json()

    record = _fetch_bug_report(admin_client.application, body["report_id"])
    assert record is not None
    assert record.screenshot_path is None
    assert record.screenshot_error is not None


def test_submit_bug_report_records_client_screenshot_error(admin_client, monkeypatch, tmp_path):
    storage_dir = tmp_path / "bug_reports"
    monkeypatch.setattr(bug_reports, "get_bug_reports_dir", lambda: str(storage_dir))

    payload = _build_payload(screenshot=None, screenshotError="User denied permission")
    response = admin_client.post("/api/bug-reports", json=payload)

    assert response.status_code == 201
    body = response.get_json()

    record = _fetch_bug_report(admin_client.application, body["report_id"])
    assert record is not None
    assert record.screenshot_path is None
    assert record.screenshot_error == "User denied permission"


# ---------------------------------------------------------------------------
# Admin maintenance endpoints
# ---------------------------------------------------------------------------


def test_list_bug_reports_returns_reports(admin_client):
    payload_a = _build_payload(description="Test bug A")
    admin_client.post("/api/bug-reports", json=payload_a)

    payload_b = _build_payload(description="Test bug B")
    response_b = admin_client.post("/api/bug-reports", json=payload_b)
    report_id_b = response_b.get_json()["report_id"]

    admin_client.patch(f"/api/bug-reports/{report_id_b}", json={"status": "resolved"})

    response = admin_client.get("/api/bug-reports")

    assert response.status_code == 200
    body = response.get_json()
    reports = body["reports"]
    assert len(reports) == 2
    assert all("report_id" in report for report in reports)

    response_filtered = admin_client.get("/api/bug-reports?status=resolved")
    assert response_filtered.status_code == 200
    filtered_reports = response_filtered.get_json()["reports"]
    assert len(filtered_reports) == 1
    assert filtered_reports[0]["status"] == "resolved"


def test_get_bug_report_detail_returns_payload(admin_client):
    create_payload = _build_payload(description="Detail check")
    response_create = admin_client.post("/api/bug-reports", json=create_payload)
    report_id = response_create.get_json()["report_id"]

    response = admin_client.get(f"/api/bug-reports/{report_id}")

    assert response.status_code == 200
    payload = response.get_json()["report"]
    assert payload["report_id"] == report_id
    assert payload["description"] == "Detail check"
    assert payload["environment"]["mode"] == "development"
    assert isinstance(payload["recent_logs"], list)
    assert isinstance(payload["network_events"], list)


def test_update_bug_report_status_changes_record(admin_client):
    create_payload = _build_payload(description="Test update")
    response_create = admin_client.post("/api/bug-reports", json=create_payload)
    report_id = response_create.get_json()["report_id"]

    response = admin_client.patch(
        f"/api/bug-reports/{report_id}",
        json={"status": "resolved", "resolution": {"notes": "Fixed in commit"}},
    )

    assert response.status_code == 200
    payload = response.get_json()["report"]
    assert payload["status"] == "resolved"
    assert payload["resolution_notes"] == "Fixed in commit"

    record = _fetch_bug_report(admin_client.application, report_id)
    assert record is not None
    assert record.status == "resolved"
    assert record.resolution_notes == "Fixed in commit"


def test_delete_bug_report_removes_record_and_screenshot(admin_client, monkeypatch, tmp_path):
    storage_dir = tmp_path / "bug_reports"
    monkeypatch.setattr(bug_reports, "get_bug_reports_dir", lambda: str(storage_dir))

    payload = _build_payload(screenshot=_create_test_screenshot())
    response_create = admin_client.post("/api/bug-reports", json=payload)
    report_id = response_create.get_json()["report_id"]

    record = _fetch_bug_report(admin_client.application, report_id)
    assert record and record.screenshot_path
    screenshot_path = Path(record.screenshot_path)
    assert screenshot_path.exists()

    response = admin_client.delete(f"/api/bug-reports/{report_id}")
    assert response.status_code == 200

    record_after = _fetch_bug_report(admin_client.application, report_id)
    assert record_after is None
    assert not screenshot_path.exists()


def test_purge_bug_reports_dry_run(admin_client):
    payload_old = _build_payload(description="Old bug")
    response_old = admin_client.post("/api/bug-reports", json=payload_old)
    report_id_old = response_old.get_json()["report_id"]

    payload_recent = _build_payload(description="Recent bug")
    admin_client.post("/api/bug-reports", json=payload_recent)

    with admin_client.application.app_context():
        old_record = BugReport.query.filter_by(report_id=report_id_old).first()
        assert old_record is not None
        old_record.submitted_at = datetime.now(timezone.utc) - timedelta(days=45)
        old_record.created_at = old_record.submitted_at
        BugReport.query.session.commit()

    response = admin_client.post(
        "/api/bug-reports/purge",
        json={"older_than_days": 30, "dry_run": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "dry_run"
    assert payload["results"]["matched"] == 1


def test_purge_bug_reports_deletes_old_records(admin_client):
    payload_old = _build_payload(description="Old bug")
    response_old = admin_client.post("/api/bug-reports", json=payload_old)
    report_id_old = response_old.get_json()["report_id"]

    payload_recent = _build_payload(description="Recent bug")
    admin_client.post("/api/bug-reports", json=payload_recent)

    with admin_client.application.app_context():
        old_record = BugReport.query.filter_by(report_id=report_id_old).first()
        assert old_record is not None
        old_record.submitted_at = datetime.now(timezone.utc) - timedelta(days=60)
        old_record.created_at = old_record.submitted_at
        BugReport.query.session.commit()

    response = admin_client.post("/api/bug-reports/purge", json={"older_than_days": 30})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"
    assert payload["results"]["deleted"] == 1

    record_after = _fetch_bug_report(admin_client.application, report_id_old)
    assert record_after is None
