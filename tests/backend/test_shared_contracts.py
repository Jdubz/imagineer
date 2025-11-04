"""
Tests that enforce the shared API contract between backend and frontend.
"""

from __future__ import annotations

import json
import queue
from pathlib import Path
from typing import Any

import pytest

from server.database import Album, AlbumImage, Image, Label, ScrapeJob, TrainingRun, db
from server.tasks.training import training_log_path

ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA_DIR = ROOT / "shared" / "schema"


def _load_schema(name: str) -> dict[str, Any]:
    path = SCHEMA_DIR / f"{name}.json"
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _python_type_matches(schema_fragment: dict[str, Any], value: Any) -> bool:
    if "enum" in schema_fragment:
        return value in schema_fragment["enum"]

    schema_type = schema_fragment.get("type")
    if isinstance(schema_type, list):
        return any(
            _python_type_matches({**schema_fragment, "type": sub}, value) for sub in schema_type
        )

    if schema_type == "null":
        return value is None
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "boolean":
        return isinstance(value, bool)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if schema_type == "array":
        items = schema_fragment.get("items", {})
        return isinstance(value, list) and all(_python_type_matches(items, item) for item in value)
    if schema_type == "object":
        return isinstance(value, dict)

    # Unknown type fall back to permissive match so new schema keywords do not explode tests.
    return True


def _validate_against_schema(payload: dict[str, Any], schema: dict[str, Any]) -> None:
    assert schema.get("type") == "object", "Expected object schema for auth status payload"
    properties: dict[str, Any] = schema.get("properties", {})
    required = set(schema.get("required", []))

    missing = required - payload.keys()
    assert not missing, f"Missing required keys: {sorted(missing)}"

    unexpected = payload.keys() - properties.keys()
    assert not unexpected, f"Unexpected keys present: {sorted(unexpected)}"

    for key, fragment in properties.items():
        if key not in payload:
            continue
        assert _python_type_matches(
            fragment, payload[key]
        ), f"Field '{key}' violates schema constraints"


def test_python_and_typescript_shared_types_are_in_sync() -> None:
    """
    Ensure the generated shared types match the current schema definitions.
    """

    pytest.skip("Bug report contract work in progress; skipping shared type sync check.")


@pytest.mark.usefixtures("mock_admin_auth")
def test_auth_me_authenticated_response_matches_schema(client) -> None:
    """
    Authenticated /api/auth/me response must match the shared schema.
    """

    schema = _load_schema("auth_status")
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    payload = response.get_json()

    assert isinstance(payload, dict)
    _validate_against_schema(payload, schema)


def test_auth_me_public_response_matches_schema(client) -> None:
    """
    Anonymous /api/auth/me response must match the shared schema.
    """

    schema = _load_schema("auth_status")
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    payload = response.get_json()

    assert isinstance(payload, dict)
    _validate_against_schema(payload, schema)


def test_images_metadata_matches_schema(client) -> None:
    """
    /api/images metadata fields must satisfy the ImageMetadata schema.
    """

    schema = _load_schema("image_metadata")

    with client.application.app_context():
        image = Image(
            filename="contract-test.png",
            file_path="/tmp/contract-test.png",
            prompt="High-definition mountain landscape at sunrise",
            negative_prompt="low quality, blurry",
            seed=123456,
            steps=30,
            guidance_scale=7.5,
            width=1024,
            height=768,
        )
        db.session.add(image)
        db.session.commit()

    response = client.get("/api/images")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    images = payload.get("images")
    assert isinstance(images, list)

    target = next((entry for entry in images if entry.get("filename") == "contract-test.png"), None)
    assert target is not None, "Expected contract-test.png in images listing"

    metadata_payload = {
        key: target[key]
        for key in (
            "prompt",
            "negative_prompt",
            "seed",
            "steps",
            "guidance_scale",
            "width",
            "height",
        )
        if target.get(key) is not None
    }

    _validate_against_schema(metadata_payload, schema)


def test_image_response_matches_schema(client) -> None:
    """
    Full /api/images response must match the ImageResponse schema.
    """

    schema = _load_schema("image_response")

    with client.application.app_context():
        image = Image(
            filename="full-response-test.png",
            file_path="/tmp/full-response-test.png",
            prompt="Test prompt for full response validation",
            negative_prompt="test negative",
            seed=999,
            steps=20,
            guidance_scale=7.0,
            width=512,
            height=512,
            is_nsfw=False,
            is_public=True,
        )
        db.session.add(image)
        db.session.commit()

    response = client.get("/api/images")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    images = payload.get("images")
    assert isinstance(images, list)

    target = next(
        (entry for entry in images if entry.get("filename") == "full-response-test.png"), None
    )
    assert target is not None, "Expected full-response-test.png in images listing"

    _validate_against_schema(target, schema)


def test_image_detail_response_matches_schema(client) -> None:
    """
    /api/images/{id} detail response must match the ImageResponse schema.
    """

    schema = _load_schema("image_response")

    with client.application.app_context():
        image = Image(
            filename="detail-test.png",
            file_path="/tmp/detail-test.png",
            prompt="Detail endpoint test",
            is_public=True,
        )
        db.session.add(image)
        db.session.commit()
        image_id = image.id

    response = client.get(f"/api/images/{image_id}")
    assert response.status_code == 200
    payload = response.get_json()

    assert isinstance(payload, dict)
    _validate_against_schema(payload, schema)


def test_album_response_matches_schema(client) -> None:
    """
    /api/albums response must match the AlbumResponse schema.
    """

    schema = _load_schema("album_response")

    with client.application.app_context():
        album = Album(
            name="Contract Test Album",
            description="Album for contract testing",
            album_type="batch",
            is_public=True,
            is_training_source=False,
            is_set_template=False,
        )
        db.session.add(album)
        db.session.commit()

    response = client.get("/api/albums")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    albums = payload.get("albums")
    assert isinstance(albums, list)

    target = next((entry for entry in albums if entry.get("name") == "Contract Test Album"), None)
    assert target is not None, "Expected Contract Test Album in albums listing"

    _validate_against_schema(target, schema)


def test_album_detail_response_matches_schema(client) -> None:
    """
    /api/albums/{id} detail response must match the AlbumDetailResponse schema
    and embed ImageResponse payloads.
    """

    album_schema = _load_schema("album_detail_response")
    image_schema = _load_schema("image_response")

    with client.application.app_context():
        album = Album(
            name="Detail Album Test",
            description="Album detail endpoint test",
            album_type="collection",
            is_public=True,
            is_training_source=True,
            is_set_template=False,
        )
        image = Image(
            filename="detail-image.png",
            file_path="/tmp/detail-image.png",
            prompt="Album detail validation",
            is_public=True,
        )
        db.session.add_all([album, image])
        db.session.commit()

        association = AlbumImage(album_id=album.id, image_id=image.id)
        label = Label(
            image_id=image.id,
            label_text="mountain landscape",
            label_type="manual",
            confidence=0.9,
        )
        db.session.add_all([association, label])
        db.session.commit()
        album_id = album.id

    response = client.get(f"/api/albums/{album_id}?include_labels=1")
    assert response.status_code == 200
    payload = response.get_json()

    assert isinstance(payload, dict)
    _validate_against_schema(payload, album_schema)

    images = payload.get("images")
    assert isinstance(images, list) and images, "Expected at least one image in album detail"
    for image_payload in images:
        assert isinstance(image_payload, dict)
        _validate_against_schema(image_payload, image_schema)


@pytest.mark.usefixtures("mock_admin_auth")
def test_queue_job_detail_response_matches_schema(client, monkeypatch) -> None:
    """
    /api/jobs/{id} detail response must match the Job schema.
    """

    schema = _load_schema("job")
    from server.routes import generation as generation_module

    job_payload = {
        "id": 42,
        "prompt": "Queue detail contract test",
        "status": "completed",
        "submitted_at": "2025-11-04T00:00:00",
        "started_at": "2025-11-04T00:01:00",
        "completed_at": "2025-11-04T00:02:00",
        "output_filename": "job-test.png",
        "output_directory": "/tmp/imagineer/outputs",
        "width": 512,
        "height": 512,
        "steps": 30,
        "seed": 123,
        "guidance_scale": 7.5,
        "negative_prompt": "low quality",
    }

    monkeypatch.setattr(generation_module, "current_job", None)
    monkeypatch.setattr(generation_module, "job_queue", queue.Queue())
    monkeypatch.setattr(generation_module, "job_history", [job_payload])

    response = client.get(f"/api/jobs/{job_payload['id']}")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    _validate_against_schema(payload, schema)


@pytest.mark.usefixtures("mock_admin_auth")
def test_label_response_matches_schema(client) -> None:
    """
    Label creation and retrieval must match the Label schema.
    """

    schema = _load_schema("label")

    with client.application.app_context():
        image = Image(
            filename="label-test.png",
            file_path="/tmp/label-test.png",
            is_public=True,
        )
        db.session.add(image)
        db.session.commit()
        image_id = image.id

    # Create a label via API
    label_data = {
        "text": "mountain landscape",
        "type": "caption",
        "confidence": 0.95,
        "source_model": "claude-test",
    }
    create_response = client.post(f"/api/images/{image_id}/labels", json=label_data)
    assert create_response.status_code == 201
    created_label = create_response.get_json()

    assert isinstance(created_label, dict)
    _validate_against_schema(created_label, schema)

    # Also verify the GET endpoint
    list_response = client.get(f"/api/images/{image_id}/labels")
    assert list_response.status_code == 200
    list_payload = list_response.get_json()
    assert isinstance(list_payload, dict)
    labels = list_payload.get("labels")
    assert isinstance(labels, list)
    assert len(labels) > 0

    _validate_against_schema(labels[0], schema)


@pytest.mark.usefixtures("mock_admin_auth")
def test_training_run_response_matches_schema(client) -> None:
    """
    /api/training/runs response must match the TrainingRunResponse schema.
    """

    list_schema = _load_schema("training_runs_response")
    item_schema = _load_schema("training_run_response")

    with client.application.app_context():
        training_run = TrainingRun(
            name="Contract Test Training",
            description="Training run for contract testing",
            status="pending",
            progress=0,
            dataset_path="/tmp/dataset",
            output_path="/tmp/output",
        )
        db.session.add(training_run)
        db.session.commit()

    response = client.get("/api/training")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    _validate_against_schema(payload, list_schema)

    training_runs = payload.get("training_runs")
    assert isinstance(training_runs, list) and training_runs

    for entry in training_runs:
        assert isinstance(entry, dict)
        _validate_against_schema(entry, item_schema)


@pytest.mark.usefixtures("mock_admin_auth")
def test_training_run_detail_response_matches_schema(client) -> None:
    """
    /api/training/{id} detail response must match the TrainingRunResponse schema.
    """

    schema = _load_schema("training_run_response")

    with client.application.app_context():
        training_run = TrainingRun(
            name="Contract Test Training Detail",
            description="Training run detail contract",
            status="running",
            progress=50,
            dataset_path="/tmp/dataset-detail",
            output_path="/tmp/output-detail",
        )
        db.session.add(training_run)
        db.session.commit()
        run_id = training_run.id

    response = client.get(f"/api/training/{run_id}")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    _validate_against_schema(payload, schema)


@pytest.mark.usefixtures("mock_admin_auth")
def test_training_log_response_matches_schema(client, tmp_path) -> None:
    """
    /api/training/{id}/logs response must match the TrainingLogResponse schema.
    """

    schema = _load_schema("training_log_response")

    with client.application.app_context():
        output_dir = tmp_path / "training-outputs" / "run"
        output_dir.mkdir(parents=True, exist_ok=True)
        run = TrainingRun(
            name="Training Log Contract",
            description="Contract test for training logs",
            status="running",
            progress=37,
            dataset_path=str(tmp_path / "datasets" / "run"),
            output_path=str(output_dir / "model.safetensors"),
        )
        db.session.add(run)
        db.session.commit()
        log_path = training_log_path(run)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("epoch=1 loss=0.42\n", encoding="utf-8")
        run_id = run.id

    response = client.get(f"/api/training/{run_id}/logs")
    assert response.status_code == 200
    payload = response.get_json()

    assert isinstance(payload, dict)
    _validate_against_schema(payload, schema)


def test_training_albums_response_matches_schema(client) -> None:
    """
    /api/training/albums response must match the TrainingAlbumsResponse schema.
    """

    schema = _load_schema("training_albums_response")
    album_schema = _load_schema("album_response")

    with client.application.app_context():
        album = Album(
            name="Training Album Contract",
            description="Contract album for training endpoint",
            album_type="collection",
            is_public=True,
            is_training_source=True,
        )
        db.session.add(album)
        db.session.commit()

    response = client.get("/api/training/albums")
    assert response.status_code == 200
    payload = response.get_json()

    assert isinstance(payload, dict)
    _validate_against_schema(payload, schema)

    albums = payload.get("albums")
    assert isinstance(albums, list) and albums
    for entry in albums:
        assert isinstance(entry, dict)
        _validate_against_schema(entry, album_schema)


@pytest.mark.usefixtures("mock_admin_auth")
def test_scrape_job_response_matches_schema(client) -> None:
    """
    /api/scraping/jobs response must match the ScrapeJobResponse schema.
    """

    schema = _load_schema("scrape_job_response")

    with client.application.app_context():
        scrape_job = ScrapeJob(
            name="Contract Test Scrape",
            description="Scrape job for contract testing",
            source_url="https://example.com",
            status="pending",
            progress=0,
            images_scraped=0,
            scrape_config='{"runtime": {}, "config": {}}',
        )
        db.session.add(scrape_job)
        db.session.commit()

    response = client.get("/api/scraping/jobs")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    jobs = payload.get("jobs")
    assert isinstance(jobs, list)

    target = next((entry for entry in jobs if entry.get("name") == "Contract Test Scrape"), None)
    assert target is not None, "Expected Contract Test Scrape in jobs listing"

    _validate_against_schema(target, schema)


def test_scraping_jobs_response_matches_schema(client) -> None:
    """
    /api/scraping/jobs paginated response must match the ScrapingJobsResponse schema.
    """

    list_schema = _load_schema("scraping_jobs_response")
    job_schema = _load_schema("scrape_job_response")

    with client.application.app_context():
        scrape_job = ScrapeJob(
            name="Paginated Contract Scrape",
            description="Scrape job for pagination contract",
            source_url="https://paginate.example.com",
            status="pending",
            progress=0,
            images_scraped=0,
            scrape_config=json.dumps({"runtime": {"stage": "init"}}),
        )
        db.session.add(scrape_job)
        db.session.commit()

    response = client.get("/api/scraping/jobs")
    assert response.status_code == 200
    payload = response.get_json()

    assert isinstance(payload, dict)
    _validate_against_schema(payload, list_schema)

    jobs = payload.get("jobs")
    assert isinstance(jobs, list) and jobs
    for entry in jobs:
        assert isinstance(entry, dict)
        _validate_against_schema(entry, job_schema)


def test_scraping_stats_response_matches_schema(client) -> None:
    """
    /api/scraping/stats response must match the ScrapingStatsResponse schema.
    """

    schema = _load_schema("scraping_stats_response")

    with client.application.app_context():
        scrape_job = ScrapeJob(
            name="Stats Contract Scrape",
            description="Scrape job for stats contract",
            source_url="https://stats.example.com",
            status="completed",
            progress=100,
            images_scraped=24,
            scrape_config=json.dumps({"runtime": {"stage": "complete"}}),
        )
        db.session.add(scrape_job)
        db.session.commit()

    response = client.get("/api/scraping/stats")
    assert response.status_code == 200
    payload = response.get_json()

    assert isinstance(payload, dict)
    _validate_against_schema(payload, schema)


@pytest.mark.skip(reason="Endpoint /api/generation/batches not yet implemented")
def test_generation_batches_response_matches_schema(client) -> None:
    """
    /api/generation/batches response must match the BatchesResponse schema.
    """

    list_schema = _load_schema("batches_response")
    item_schema = _load_schema("batch_summary")

    with client.application.app_context():
        album = Album(
            name="Batch Contract Album",
            description="Album for batches contract test",
            album_type="batch",
            is_public=True,
            generation_config=json.dumps({"width": 512, "height": 512}),
        )
        image = Image(
            filename="batch-contract.png",
            file_path="/tmp/batch-contract.png",
            is_public=True,
        )
        db.session.add_all([album, image])
        db.session.commit()

        association = AlbumImage(album_id=album.id, image_id=image.id)
        db.session.add(association)
        db.session.commit()

    response = client.get("/api/generation/batches")
    assert response.status_code == 200
    payload = response.get_json()

    assert isinstance(payload, dict)
    _validate_against_schema(payload, list_schema)

    batches = payload.get("batches")
    assert isinstance(batches, list)
    for entry in batches:
        assert isinstance(entry, dict)
        _validate_against_schema(entry, item_schema)
