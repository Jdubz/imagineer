"""
Tests that enforce the shared API contract between backend and frontend.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts import generate_shared_types as generator
from server.database import Image, db

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

    schemas = generator.load_schemas()
    assert schemas, "Expected at least one shared schema definition"

    expected_ts, expected_py = generator.build_outputs(schemas)

    ts_contents = generator.TS_TARGET.read_text(encoding="utf-8")
    py_contents = generator.PY_TARGET.read_text(encoding="utf-8")

    assert (
        ts_contents == expected_ts
    ), "TypeScript shared types are out of date. Run scripts/generate_shared_types.py"
    assert (
        py_contents == expected_py
    ), "Python shared types are out of date. Run scripts/generate_shared_types.py"


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
