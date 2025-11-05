"""
Tests for API endpoints
"""

import json
import queue
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from server.database import Album, AlbumImage, Image, db


class TestHealthEndpoint:
    """Tests for /api/health endpoint"""

    def test_health_check(self, client):
        """Test health check endpoint returns 200"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "ok"
        assert "queue_size" in data
        assert "current_job" in data
        assert "total_completed" in data


class TestConfigEndpoints:
    """Tests for configuration endpoints"""

    def test_get_config(self, client):
        """Test GET /api/config returns configuration"""
        response = client.get("/api/config")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "model" in data
        assert "generation" in data
        assert "output" in data

    def test_update_config_missing_data(self, client):
        """Test PUT /api/config with missing data returns 400"""
        response = client.put("/api/config", data=json.dumps({}), content_type="application/json")
        assert response.status_code == 400

    def test_update_config_missing_required_keys(self, client):
        """Test PUT /api/config with missing required keys returns 400"""
        response = client.put(
            "/api/config", data=json.dumps({"model": {}}), content_type="application/json"
        )
        assert response.status_code == 400

    def test_update_config_path_traversal(self, client):
        """Test PUT /api/config blocks path traversal attempts"""
        config = {
            "model": {"default": "test"},
            "generation": {"steps": 25},
            "output": {"directory": "../../../etc/passwd"},
        }
        response = client.put(
            "/api/config", data=json.dumps(config), content_type="application/json"
        )
        assert response.status_code == 400

    def test_update_generation_config(self, client):
        """Test PUT /api/config/generation updates generation settings"""
        updates = {"steps": 30, "guidance_scale": 8.0}
        response = client.put(
            "/api/config/generation", data=json.dumps(updates), content_type="application/json"
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True

    def test_update_generation_config_invalid_key(self, client):
        """Test PUT /api/config/generation rejects invalid keys"""
        updates = {"invalid_key": "value"}
        response = client.put(
            "/api/config/generation", data=json.dumps(updates), content_type="application/json"
        )
        assert response.status_code == 400


class TestAuthRoutes:
    """Tests for authentication-related endpoints."""

    def test_oauth_callback_recovers_from_anomalous_path(self, client, monkeypatch):
        """Ensure we process callbacks that arrive on double-encoded paths."""
        from server import api as api_module

        fake_token = {
            "userinfo": {
                "email": "user@example.com",
                "name": "Example User",
                "picture": "https://example.com/avatar.png",
            }
        }
        monkeypatch.setattr(api_module.google, "authorize_access_token", lambda: fake_token)

        response = client.get(
            "/api/auth/google/%2Fhttps://imagineer-api.joshwentworth.com/api/auth/google/%2F",
            query_string={"code": "dummy", "state": "%2F"},
        )

        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert "Login successful" in body

        with client.session_transaction() as session:
            user_session = session.get("user")
            assert user_session
            assert user_session["email"] == "user@example.com"

    def test_oauth_callback_anomalous_path_without_code_returns_400(self, client):
        """Unexpected paths without OAuth code should not be processed."""
        response = client.get(
            "/api/auth/google/%2Fhttps://imagineer-api.joshwentworth.com/api/auth/google/%2F",
            query_string={"state": "%2F"},
        )

        assert response.status_code == 400
        payload = json.loads(response.data)
        assert payload["error"] == "Invalid OAuth callback"


class TestGenerateEndpoint:
    """Tests for /api/generate endpoint"""

    @staticmethod
    def _reset_rate_history():
        from server.routes import generation as generation_module

        with generation_module._generation_rate_lock:
            generation_module._generation_request_times.clear()

    def test_generate_requires_admin(self, client, sample_job_data):
        """Unauthenticated requests should be rejected."""
        self._reset_rate_history()
        response = client.post(
            "/api/generate", data=json.dumps(sample_job_data), content_type="application/json"
        )
        assert response.status_code == 401

    def test_generate_missing_prompt(self, admin_client):
        """Test POST /api/generate without prompt returns 400"""
        self._reset_rate_history()
        response = admin_client.post(
            "/api/generate", data=json.dumps({}), content_type="application/json"
        )
        assert response.status_code == 400

    def test_generate_empty_prompt(self, admin_client):
        """Test POST /api/generate with empty prompt returns 400"""
        self._reset_rate_history()
        response = admin_client.post(
            "/api/generate", data=json.dumps({"prompt": "   "}), content_type="application/json"
        )
        assert response.status_code == 400

    def test_generate_prompt_too_long(self, admin_client):
        """Test POST /api/generate with overly long prompt returns 400"""
        self._reset_rate_history()
        long_prompt = "a" * 2001  # Max is 2000
        response = admin_client.post(
            "/api/generate",
            data=json.dumps({"prompt": long_prompt}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_generate_valid_prompt(self, admin_client, sample_job_data):
        """Test POST /api/generate with valid data returns 201 Created"""
        self._reset_rate_history()
        response = admin_client.post(
            "/api/generate", data=json.dumps(sample_job_data), content_type="application/json"
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert "id" in data
        assert data["status"] == "queued"
        assert data["prompt"] == sample_job_data["prompt"]
        assert "queue_position" in data
        assert "Location" in response.headers
        assert f"/api/jobs/{data['id']}" in response.headers["Location"]

    def test_generate_invalid_seed(self, admin_client):
        """Test POST /api/generate with invalid seed returns 400"""
        self._reset_rate_history()
        test_cases = [
            {"prompt": "test", "seed": -1},  # Negative
            {"prompt": "test", "seed": 2147483648},  # Too large
            {"prompt": "test", "seed": "invalid"},  # String
        ]
        for data in test_cases:
            response = admin_client.post(
                "/api/generate", data=json.dumps(data), content_type="application/json"
            )
            assert response.status_code == 400

    def test_generate_invalid_steps(self, admin_client):
        """Test POST /api/generate with invalid steps returns 400"""
        self._reset_rate_history()
        test_cases = [
            {"prompt": "test", "steps": 0},  # Too low
            {"prompt": "test", "steps": 151},  # Too high
            {"prompt": "test", "steps": "invalid"},  # String
        ]
        for data in test_cases:
            response = admin_client.post(
                "/api/generate", data=json.dumps(data), content_type="application/json"
            )
            assert response.status_code == 400

    def test_generate_invalid_dimensions(self, admin_client):
        """Test POST /api/generate with invalid width/height returns 400"""
        self._reset_rate_history()
        test_cases = [
            {"prompt": "test", "width": 63},  # Too small
            {"prompt": "test", "width": 2049},  # Too large
            {"prompt": "test", "width": 511},  # Not divisible by 8
            {"prompt": "test", "height": 63},  # Too small
            {"prompt": "test", "height": 2049},  # Too large
            {"prompt": "test", "height": 511},  # Not divisible by 8
        ]
        for data in test_cases:
            response = admin_client.post(
                "/api/generate", data=json.dumps(data), content_type="application/json"
            )
            assert response.status_code == 400

    def test_generate_invalid_guidance_scale(self, admin_client):
        """Test POST /api/generate with invalid guidance_scale returns 400"""
        self._reset_rate_history()
        test_cases = [
            {"prompt": "test", "guidance_scale": -1},  # Negative
            {"prompt": "test", "guidance_scale": 31},  # Too high
            {"prompt": "test", "guidance_scale": "invalid"},  # String
        ]
        for data in test_cases:
            response = admin_client.post(
                "/api/generate", data=json.dumps(data), content_type="application/json"
            )
            assert response.status_code == 400

    def test_generate_rate_limit(self, admin_client, monkeypatch):
        """Ensure rate limiting returns 429 once the threshold is exceeded."""
        from server.routes import generation as generation_module

        monkeypatch.setattr(generation_module, "GENERATION_RATE_LIMIT", 1)
        monkeypatch.setattr(generation_module, "GENERATION_RATE_WINDOW_SECONDS", 60)
        self._reset_rate_history()

        payload = {"prompt": "rate limit test"}

        first_response = admin_client.post(
            "/api/generate", data=json.dumps(payload), content_type="application/json"
        )
        assert first_response.status_code != 429

        second_response = admin_client.post(
            "/api/generate", data=json.dumps(payload), content_type="application/json"
        )
        assert second_response.status_code == 429


class TestJobsEndpoints:
    """Tests for job management endpoints"""

    def test_get_jobs(self, client):
        """Test GET /api/jobs returns job lists"""
        response = client.get("/api/jobs")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "current" in data
        assert "queue" in data
        assert "history" in data

    def test_get_nonexistent_job(self, client):
        """Test GET /api/jobs/{id} for nonexistent job returns 404"""
        response = client.get("/api/jobs/99999")
        assert response.status_code == 404


class TestImagesEndpoints:
    """Tests for image endpoints."""

    @staticmethod
    def _create_image(app, **overrides):
        with app.app_context():
            image = Image(
                filename=overrides.get("filename", "sample.png"),
                file_path=overrides.get("file_path", "/tmp/sample.png"),
                is_public=overrides.get("is_public", True),
                prompt=overrides.get("prompt"),
                negative_prompt=overrides.get("negative_prompt"),
                seed=overrides.get("seed"),
                steps=overrides.get("steps"),
                guidance_scale=overrides.get("guidance_scale"),
                width=overrides.get("width"),
                height=overrides.get("height"),
            )
            db.session.add(image)
            db.session.flush()
            image_id = image.id
            db.session.commit()
            return image_id

    def test_list_images_returns_public_entries(self, client):
        image_id = self._create_image(
            client.application,
            filename="one.png",
            file_path="/tmp/imagineer/one.png",
            prompt="sunrise over mountains",
            seed=123,
        )

        response = client.get("/api/images")
        assert response.status_code == 200
        payload = response.get_json()
        ids = [item["id"] for item in payload["images"]]
        assert image_id in ids

    def test_get_image_file_returns_bytes(self, client, tmp_path):
        file_path = tmp_path / "image.png"
        file_bytes = b"image-bytes"
        file_path.write_bytes(file_bytes)
        image_id = self._create_image(
            client.application, filename="image.png", file_path=str(file_path)
        )

        response = client.get(f"/api/images/{image_id}/file")
        assert response.status_code == 200
        assert response.data == file_bytes

    def test_get_image_file_missing_returns_404(self, client):
        image_id = self._create_image(
            client.application, filename="missing.png", file_path="/tmp/does/not/exist.png"
        )

        response = client.get(f"/api/images/{image_id}/file")
        assert response.status_code == 404

    def test_get_image_file_private_requires_admin(self, client, tmp_path):
        file_path = tmp_path / "private.png"
        file_path.write_bytes(b"secret")
        image_id = self._create_image(
            client.application,
            filename="private.png",
            file_path=str(file_path),
            is_public=False,
        )

        response = client.get(f"/api/images/{image_id}/file")
        assert response.status_code == 404

    def test_get_image_file_allows_admin_access(self, client, mock_admin_auth, tmp_path):
        file_path = tmp_path / "admin.png"
        contents = b"admin-bytes"
        file_path.write_bytes(contents)
        image_id = self._create_image(
            client.application,
            filename="admin.png",
            file_path=str(file_path),
            is_public=False,
        )

        response = client.get(f"/api/images/{image_id}/file")
        assert response.status_code == 200
        assert response.data == contents


class TestGenerationBlueprint:
    """Tests for generation blueprint endpoints that moved out of server/api.py."""

    @staticmethod
    def _create_album_with_image(app, *, name, slug, created_at, **image_fields):
        with app.app_context():
            image = Image(
                filename=image_fields.get("filename", f"{slug}.png"),
                file_path=image_fields.get("file_path", f"/tmp/{slug}.png"),
                prompt=image_fields.get("prompt"),
                negative_prompt=image_fields.get("negative_prompt"),
                seed=image_fields.get("seed"),
                steps=image_fields.get("steps"),
                guidance_scale=image_fields.get("guidance_scale"),
                width=image_fields.get("width"),
                height=image_fields.get("height"),
                is_public=image_fields.get("is_public", True),
            )
            album = Album(
                name=name,
                album_type=image_fields.get("album_type", "batch"),
                generation_config=json.dumps({"slug": slug}),
            )
            album.created_at = created_at
            album.updated_at = created_at
            db.session.add_all([album, image])
            db.session.flush()
            db.session.add(AlbumImage(album_id=album.id, image_id=image.id, sort_order=1))
            album_id = album.id
            album_slug = album.slug
            image_id = image.id
            filename = image.filename
            db.session.commit()
            return {
                "album_id": album_id,
                "album_slug": album_slug,
                "image_id": image_id,
                "filename": filename,
            }

    def test_list_batches_orders_by_recency(self, client):
        now = datetime.utcnow()
        recent = self._create_album_with_image(
            client.application,
            name="Recent Batch",
            slug="recent-batch",
            created_at=now,
            filename="recent.png",
        )
        older = self._create_album_with_image(
            client.application,
            name="Older Batch",
            slug="older-batch",
            created_at=now - timedelta(days=1),
            filename="older.png",
        )

        response = client.get("/api/batches")
        assert response.status_code == 200
        payload = response.get_json()
        slugs = [batch["batch_id"] for batch in payload["batches"]]
        assert slugs[:2] == [recent["album_slug"], older["album_slug"]]
        assert payload["batches"][0]["image_count"] == 1
        assert payload["batches"][0]["preview_url"] == f"/images/{recent['image_id']}/thumbnail"

    def test_get_batch_returns_image_metadata(self, client):
        record = self._create_album_with_image(
            client.application,
            name="Sunset Batch",
            slug="sunset-batch",
            created_at=datetime.utcnow(),
            filename="sunset.png",
            prompt="sunset over the ocean",
            seed=42,
            steps=30,
            guidance_scale=7.5,
            width=768,
            height=512,
        )

        response = client.get(f"/api/batches/{record['album_slug']}")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["batch_id"] == record["album_slug"]
        assert payload["image_count"] == 1
        image_payload = payload["images"][0]
        assert image_payload["filename"] == record["filename"]
        assert image_payload["download_url"] == f"/images/{record['image_id']}/file"
        assert image_payload["prompt"] == "sunset over the ocean"
        assert image_payload["seed"] == 42
        assert image_payload["width"] == 768
        assert image_payload["height"] == 512
        assert image_payload["labels"] == []

    def test_get_batch_rejects_path_traversal(self, client):
        response = client.get("/api/batches/..")
        assert response.status_code == 404

    def test_list_loras_reads_index(self, client, generation_paths):
        lora_dir: Path = generation_paths["lora_dir"]
        index = {
            "fantasy": {
                "filename": "fantasy.safetensors",
                "organized_at": "2025-10-29T12:00:00Z",
                "default_weight": 0.8,
            }
        }
        (lora_dir / "index.json").write_text(json.dumps(index))
        fantasy_folder = lora_dir / "fantasy"
        fantasy_folder.mkdir()
        (fantasy_folder / "preview.png").write_bytes(b"preview-bytes")

        response = client.get("/api/loras")
        assert response.status_code == 200
        payload = json.loads(response.data)
        assert payload["loras"][0]["folder"] == "fantasy"
        assert payload["loras"][0]["has_preview"] is True
        assert payload["loras"][0]["default_weight"] == 0.8

    def test_list_loras_returns_empty_when_index_missing(self, client, generation_paths):
        response = client.get("/api/loras")
        assert response.status_code == 200
        payload = json.loads(response.data)
        assert payload["loras"] == []

    def test_get_lora_details_merges_config_and_index(self, client, generation_paths):
        lora_dir: Path = generation_paths["lora_dir"]
        index = {
            "portrait": {
                "filename": "portrait.safetensors",
                "format": "sdxl",
                "organized_at": "2025-10-28T09:00:00Z",
            }
        }
        (lora_dir / "index.json").write_text(json.dumps(index))

        portrait_folder = lora_dir / "portrait"
        portrait_folder.mkdir()
        (portrait_folder / "config.yaml").write_text(
            yaml.safe_dump({"title": "Portrait Enhancer", "author": "Imagineer"})
        )

        response = client.get("/api/loras/portrait")
        assert response.status_code == 200
        payload = json.loads(response.data)
        assert payload["filename"] == "portrait.safetensors"
        assert payload["title"] == "Portrait Enhancer"
        assert payload["author"] == "Imagineer"
        assert payload["format"] == "sdxl"

    def test_get_lora_details_rejects_invalid_folder(self, client):
        response = client.get("/api/loras/..")
        assert response.status_code == 400

    def test_serve_lora_preview_fetches_file(self, client, generation_paths):
        lora_dir: Path = generation_paths["lora_dir"]
        folder = lora_dir / "weathered"
        folder.mkdir()
        preview_content = b"PNG"
        (folder / "preview.png").write_bytes(preview_content)

        response = client.get("/api/loras/weathered/preview")
        assert response.status_code == 200
        assert response.data == preview_content

    def test_serve_lora_preview_missing_returns_404(self, client, generation_paths):
        response = client.get("/api/loras/missing/preview")
        assert response.status_code == 404

    def test_generation_health_snapshot_reflects_queue_state(self, monkeypatch):
        from server.routes import generation as generation_module

        test_queue: queue.Queue[dict] = queue.Queue()
        test_queue.put({"id": 1})
        test_queue.put({"id": 2})

        monkeypatch.setattr(generation_module, "job_queue", test_queue)
        monkeypatch.setattr(generation_module, "job_history", [{"id": 7}])
        monkeypatch.setattr(generation_module, "current_job", {"id": 3})

        snapshot = generation_module.get_generation_health()
        assert snapshot["queue_size"] == 2
        assert snapshot["current_job"] is True
        assert snapshot["total_completed"] == 1


class TestAdminBlueprint:
    """Tests for admin blueprint endpoints extracted from server/api.py."""

    def test_get_config_cache_stats_success(self, admin_client, monkeypatch):
        from server.routes import admin as admin_module

        expected_stats = {"hits": 5, "misses": 1}
        monkeypatch.setattr(admin_module, "get_cache_stats", lambda: expected_stats)

        response = admin_client.get("/api/admin/config/cache")
        assert response.status_code == 200
        payload = json.loads(response.data)
        assert payload == expected_stats

    def test_get_config_cache_stats_failure(self, admin_client, monkeypatch):
        from server.routes import admin as admin_module

        def raise_error():
            raise RuntimeError("boom")

        monkeypatch.setattr(admin_module, "get_cache_stats", raise_error)

        response = admin_client.get("/api/admin/config/cache")
        assert response.status_code == 500
        payload = json.loads(response.data)
        assert payload["error"] == "Failed to get cache statistics"

    def test_reload_config_cache_invokes_hooks(self, admin_client, monkeypatch):
        from server.routes import admin as admin_module

        calls = {"cleared": False, "loaded": False}

        def fake_clear():
            calls["cleared"] = True

        def fake_load(*, force_reload=False):
            calls["loaded"] = force_reload

        monkeypatch.setattr(admin_module, "clear_config_cache", fake_clear)
        monkeypatch.setattr(admin_module, "load_config", fake_load)
        monkeypatch.setattr(admin_module, "get_cache_stats", lambda: {"hits": 1})

        response = admin_client.post("/api/admin/config/reload")
        assert response.status_code == 200
        payload = json.loads(response.data)
        assert payload["success"] is True
        assert payload["cache_stats"] == {"hits": 1}
        assert calls["cleared"] is True
        assert calls["loaded"] is True

    def test_reload_config_cache_handles_failure(self, admin_client, monkeypatch):
        from server.routes import admin as admin_module

        def fake_load(*, force_reload=False):
            raise RuntimeError("reload failed")

        monkeypatch.setattr(admin_module, "clear_config_cache", lambda: None)
        monkeypatch.setattr(admin_module, "load_config", fake_load)

        response = admin_client.post("/api/admin/config/reload")
        assert response.status_code == 500
        payload = json.loads(response.data)
        assert payload["error"] == "Failed to reload configuration"

    def test_get_disk_statistics_success(self, admin_client, monkeypatch):
        from server.routes import admin as admin_module

        stats = {"outputs": {"bytes": 1024, "files": 3}}
        monkeypatch.setattr(admin_module, "collect_disk_statistics", lambda: stats)

        response = admin_client.get("/api/admin/disk-stats")
        assert response.status_code == 200
        payload = json.loads(response.data)
        assert payload == stats

    def test_get_disk_statistics_missing_path(self, admin_client, monkeypatch):
        from server.routes import admin as admin_module

        def fake_collect():
            raise FileNotFoundError("missing dir")

        monkeypatch.setattr(admin_module, "collect_disk_statistics", fake_collect)

        response = admin_client.get("/api/admin/disk-stats")
        assert response.status_code == 404
        payload = json.loads(response.data)
        assert "missing dir" in payload["error"]


class TestAlbumSetTemplates:
    """Tests covering album endpoints with set-template metadata."""

    def test_create_set_template_album(self, admin_client):
        payload = {
            "name": "Tarot Deck",
            "description": "Major Arcana set template",
            "album_type": "set",
            "is_set_template": True,
            "csv_data": [{"name": "The Fool", "arcana": "major"}],
            "base_prompt": "Artistic tarot illustration",
            "prompt_template": "{name} tarot card",
            "style_suffix": "Mystic watercolor style",
            "example_theme": "Celestial",
            "generation_config": {"width": 768, "height": 1024},
            "lora_config": [{"path": "/models/lora/tarot.safetensors", "weight": 0.6}],
        }

        response = admin_client.post(
            "/api/albums", data=json.dumps(payload), content_type="application/json"
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["is_set_template"] is True
        assert data["album_type"] == "set"
        assert data["template_item_count"] == 1
        assert data["lora_count"] == 1
        assert json.loads(data["csv_data"])[0]["name"] == "The Fool"
        assert json.loads(data["generation_config"])["width"] == 768

    def test_list_albums_filters_set_templates(self, client):
        """Test filtering deprecated is_set_template and new source_type filters"""
        with client.application.app_context():
            # Create albums with new source tracking
            batch_generated_album = Album(
                name="Generated Zodiac",
                description="Generated from batch template",
                album_type="batch",
                is_set_template=False,
                source_type="batch_generation",
                source_id=1,
                created_by="admin@example.com",
            )
            manual_album = Album(
                name="Manual Collection",
                description="Hand curated",
                album_type="manual",
                is_set_template=False,
                source_type="manual",
                created_by="admin@example.com",
            )
            db.session.add_all([batch_generated_album, manual_album])
            db.session.commit()

        # DEPRECATED: is_set_template filter should return empty
        # (templates moved to batch_templates)
        response = client.get("/api/albums?is_set_template=1")
        assert response.status_code == 200
        payload = json.loads(response.data)
        assert len(payload["albums"]) == 0  # Templates are in batch_templates table now

        # NEW: source_type filter should work
        response = client.get("/api/albums?source_type=batch_generation")
        assert response.status_code == 200
        payload = json.loads(response.data)
        assert len(payload["albums"]) == 1
        assert payload["albums"][0]["name"] == "Generated Zodiac"
        assert payload["albums"][0]["source_type"] == "batch_generation"

        # album_type filter should still work
        response = client.get("/api/albums?album_type=manual")
        assert response.status_code == 200
        payload = json.loads(response.data)
        assert len(payload["albums"]) == 1
        assert payload["albums"][0]["name"] == "Manual Collection"

    def test_update_album_template_fields(self, admin_client):
        with admin_client.application.app_context():
            album = Album(
                name="Card Deck",
                description="Initial description",
                album_type="batch",
                created_by="admin@example.com",
            )
            db.session.add(album)
            db.session.commit()
            album_id = album.id

        update_payload = {
            "description": "Updated description",
            "album_type": "set",
            "is_set_template": True,
            "csv_data": [{"name": "Ace of Spades"}],
            "base_prompt": "Playing card illustration",
            "prompt_template": "{name} card",
            "style_suffix": "Vintage ink",
            "example_theme": "Neo-noir",
            "lora_config": [{"path": "/models/lora/cards.safetensors", "weight": 0.5}],
        }

        response = admin_client.put(
            f"/api/albums/{album_id}",
            data=json.dumps(update_payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["is_set_template"] is True
        assert data["album_type"] == "set"
        assert data["base_prompt"] == "Playing card illustration"
        assert json.loads(data["csv_data"])[0]["name"] == "Ace of Spades"

        with admin_client.application.app_context():
            refreshed = db.session.get(Album, album_id)
            assert refreshed.is_set_template is True
            assert refreshed.album_type == "set"
            assert json.loads(refreshed.csv_data)[0]["name"] == "Ace of Spades"
