"""
Tests for Phase 3: AI Labeling System (Docker/CLI Implementation)
"""

from unittest.mock import MagicMock, patch

from PIL import Image as PILImage

from server.database import Album, AlbumImage, Image, Label, db
from server.services.labeling_cli import batch_label_images
from server.tasks.labeling import label_album_task, label_image_task


class TestBatchLabeling:
    """Test batch labeling functionality"""

    @patch("server.services.labeling_cli.label_image_with_claude")
    def test_batch_label_images_success(self, mock_label, temp_output_dir):
        """Test successful batch labeling"""
        # Create test images
        img_paths = []
        for i in range(3):
            test_img = PILImage.new("RGB", (100, 100), color="red")
            img_path = temp_output_dir / f"test{i}.jpg"
            test_img.save(img_path, "JPEG")
            img_paths.append(str(img_path))

        # Mock individual labeling results
        mock_label.side_effect = [
            {"status": "success", "description": "Image 1", "nsfw_rating": "SAFE", "tags": ["red"]},
            {
                "status": "success",
                "description": "Image 2",
                "nsfw_rating": "SAFE",
                "tags": ["blue"],
            },
            {"status": "error", "message": "Failed to process"},
        ]

        results = batch_label_images(img_paths)

        assert results["total"] == 3
        assert results["success"] == 2
        assert results["failed"] == 1
        assert len(results["results"]) == 3

    @patch("server.services.labeling_cli.label_image_with_claude")
    def test_batch_label_images_with_progress(self, mock_label, temp_output_dir):
        """Test batch labeling with progress callback"""
        # Create test images
        img_paths = []
        for i in range(2):
            test_img = PILImage.new("RGB", (100, 100), color="red")
            img_path = temp_output_dir / f"test{i}.jpg"
            test_img.save(img_path, "JPEG")
            img_paths.append(str(img_path))

        # Mock successful labeling
        mock_label.return_value = {
            "status": "success",
            "description": "Test image",
            "nsfw_rating": "SAFE",
            "tags": ["test"],
        }

        progress_calls = []

        def progress_callback(current, total):
            progress_calls.append((current, total))

        batch_label_images(img_paths, progress_callback=progress_callback)

        assert len(progress_calls) == 2
        assert progress_calls[0] == (1, 2)
        assert progress_calls[1] == (2, 2)


class TestLabelingAPI:
    """Test labeling API endpoints"""

    def test_label_image_endpoint_unauthorized(self, client):
        """Test labeling endpoint without admin auth"""
        response = client.post("/api/labeling/image/1")
        assert response.status_code == 401

    @patch("server.api.label_image_task.delay")
    def test_label_image_endpoint_success(self, mock_delay, client, mock_admin_auth):
        """Test queuing image labeling task"""
        with client.application.app_context():
            image = Image(filename="test.jpg", file_path="/tmp/test.jpg", is_public=True)
            db.session.add(image)
            db.session.commit()
            image_id = image.id

        mock_delay.return_value = MagicMock(id="task-123")

        response = client.post(
            f"/api/labeling/image/{image_id}",
            json={"prompt_type": "sd_training"},
            headers={"Authorization": "Bearer admin_token"},
        )

        assert response.status_code == 202
        data = response.get_json()
        assert data == {"status": "queued", "task_id": "task-123"}
        mock_delay.assert_called_once_with(image_id=image_id, prompt_type="sd_training")

    def test_label_image_endpoint_not_found(self, client, mock_admin_auth):
        """Labeling a nonexistent image should return 404"""
        response = client.post(
            "/api/labeling/image/9999",
            json={"prompt_type": "default"},
            headers={"Authorization": "Bearer admin_token"},
        )

        assert response.status_code == 404

    def test_label_album_endpoint_unauthorized(self, client):
        """Test album labeling endpoint without admin auth"""
        response = client.post("/api/labeling/album/1")
        assert response.status_code == 401

    @patch("server.api.label_album_task.delay")
    def test_label_album_endpoint_success(self, mock_delay, client, mock_admin_auth):
        """Test queuing album labeling task"""
        with client.application.app_context():
            album = Album(name="Test Album")
            image = Image(filename="test.jpg", file_path="/tmp/test.jpg", is_public=True)
            db.session.add_all([album, image])
            db.session.commit()
            db.session.add(AlbumImage(album_id=album.id, image_id=image.id))
            db.session.commit()
            album_id = album.id

        mock_delay.return_value = MagicMock(id="album-task-1")

        response = client.post(
            f"/api/labeling/album/{album_id}",
            json={"prompt_type": "sd_training"},
            headers={"Authorization": "Bearer admin_token"},
        )

        assert response.status_code == 202
        data = response.get_json()
        assert data == {"status": "queued", "task_id": "album-task-1"}
        mock_delay.assert_called_once_with(
            album_id=album.id, prompt_type="sd_training", force=False
        )

    @patch("server.api.celery.AsyncResult")
    def test_labeling_task_status_progress(self, mock_async, client):
        """Task status endpoint returns progress details."""
        async_result = MagicMock()
        async_result.state = "PROGRESS"
        async_result.info = {"current": 3, "total": 10, "message": "Working"}
        mock_async.return_value = async_result

        response = client.get("/api/labeling/tasks/task-xyz")

        assert response.status_code == 200
        data = response.get_json()
        assert data["state"] == "PROGRESS"
        assert data["progress"] == {"current": 3, "total": 10, "message": "Working"}

    @patch("server.api.celery.AsyncResult")
    def test_labeling_task_status_success(self, mock_async, client):
        """Task status endpoint surfaces success payload."""
        async_result = MagicMock()
        async_result.state = "SUCCESS"
        async_result.info = {"status": "success", "image_id": 1}
        mock_async.return_value = async_result

        response = client.get("/api/labeling/tasks/task-success")

        assert response.status_code == 200
        data = response.get_json()
        assert data["state"] == "SUCCESS"
        assert data["result"] == {"status": "success", "image_id": 1}

    @patch("server.api.celery.AsyncResult")
    def test_labeling_task_status_failure(self, mock_async, client):
        """Task status endpoint returns failure info."""
        async_result = MagicMock()
        async_result.state = "FAILURE"
        async_result.info = RuntimeError("boom")
        mock_async.return_value = async_result

        response = client.get("/api/labeling/tasks/task-failure")

        assert response.status_code == 200
        data = response.get_json()
        assert data["state"] == "FAILURE"
        assert "boom" in data["error"]

    def test_label_album_empty(self, client, mock_admin_auth):
        """Album with no images should be rejected"""
        with client.application.app_context():
            album = Album(name="Empty Album")
            db.session.add(album)
            db.session.commit()
            album_id = album.id

        response = client.post(
            f"/api/labeling/album/{album_id}",
            headers={"Authorization": "Bearer admin_token"},
        )

        assert response.status_code == 400
        assert "empty" in response.get_json()["error"].lower()

    def test_label_album_already_labeled(self, client, mock_admin_auth):
        """Album with all images labeled should be rejected unless force=True"""
        with client.application.app_context():
            album = Album(name="Labeled Album")
            image = Image(filename="test.jpg", file_path="/tmp/test.jpg", is_public=True)
            db.session.add_all([album, image])
            db.session.commit()
            db.session.add(AlbumImage(album_id=album.id, image_id=image.id))
            db.session.add(
                Label(
                    image_id=image.id,
                    label_text="Existing label",
                    label_type="tag",
                    source_model="unit-test",
                )
            )
            db.session.commit()
            album_id = album.id

        response = client.post(
            f"/api/labeling/album/{album_id}",
            headers={"Authorization": "Bearer admin_token"},
        )

        assert response.status_code == 400
        assert "already" in response.get_json()["error"].lower()


class TestNSFWClassification:
    """Test NSFW classification and database updates"""

    @patch("server.services.labeling_cli.label_image_with_claude")
    def test_nsfw_classification_safe(self, mock_label, client):
        """Task marks SAFE classification correctly"""
        with client.application.app_context():
            image = Image(filename="safe.jpg", file_path="/tmp/safe.jpg", is_public=True)
            db.session.add(image)
            db.session.commit()
            image_id = image.id

        mock_label.return_value = {
            "status": "success",
            "description": "A safe image",
            "nsfw_rating": "SAFE",
            "tags": ["safe", "family-friendly"],
        }

        result = label_image_task.run(image_id=image_id, prompt_type="default")

        assert result["status"] == "success"

        with client.application.app_context():
            updated_image = Image.query.get(image_id)
            assert updated_image.is_nsfw is False

    @patch("server.services.labeling_cli.label_image_with_claude")
    def test_nsfw_classification_explicit(self, mock_label, client):
        """Task marks EXPLICIT classification correctly"""
        with client.application.app_context():
            image = Image(filename="explicit.jpg", file_path="/tmp/explicit.jpg", is_public=True)
            db.session.add(image)
            db.session.commit()
            image_id = image.id

        mock_label.return_value = {
            "status": "success",
            "description": "An explicit image",
            "nsfw_rating": "EXPLICIT",
            "tags": ["explicit", "adult"],
        }

        result = label_image_task.run(image_id=image_id, prompt_type="default")

        assert result["status"] == "success"

        with client.application.app_context():
            updated_image = Image.query.get(image_id)
            assert updated_image.is_nsfw is True

    @patch("server.services.labeling_cli.label_image_with_claude")
    def test_label_storage(self, mock_label, client):
        """Task stores caption and tags"""
        with client.application.app_context():
            image = Image(filename="test.jpg", file_path="/tmp/test.jpg", is_public=True)
            db.session.add(image)
            db.session.commit()
            image_id = image.id

        mock_label.return_value = {
            "status": "success",
            "description": "A beautiful landscape with mountains",
            "nsfw_rating": "SAFE",
            "tags": ["landscape", "mountains", "nature", "beautiful"],
        }

        result = label_image_task.run(image_id=image_id, prompt_type="default")

        assert result["status"] == "success"

        with client.application.app_context():
            labels = Label.query.filter_by(image_id=image_id).all()
            assert len(labels) == 5  # 1 caption + 4 tags

            caption_labels = [label for label in labels if label.label_type == "caption"]
            assert len(caption_labels) == 1
            assert "landscape" in caption_labels[0].label_text

            tag_labels = [label for label in labels if label.label_type == "tag"]
            assert len(tag_labels) == 4
            tag_texts = [label.label_text for label in tag_labels]
            assert "landscape" in tag_texts
            assert "mountains" in tag_texts
            assert "nature" in tag_texts
            assert "beautiful" in tag_texts

            for label in labels:
                assert label.source_model == "claude-3-5-sonnet"


class TestLabelAlbumTask:
    """Test album labeling Celery task"""

    @patch("server.services.labeling_cli.label_image_with_claude")
    def test_album_task_labels_unlabeled_images(self, mock_label, client):
        with client.application.app_context():
            album = Album(name="Task Album")
            image_one = Image(filename="one.jpg", file_path="/tmp/one.jpg", is_public=True)
            image_two = Image(filename="two.jpg", file_path="/tmp/two.jpg", is_public=True)
            db.session.add_all([album, image_one, image_two])
            db.session.commit()
            db.session.add_all(
                [
                    AlbumImage(album_id=album.id, image_id=image_one.id),
                    AlbumImage(album_id=album.id, image_id=image_two.id),
                ]
            )
            db.session.add(
                Label(
                    image_id=image_two.id,
                    label_text="prelabeled",
                    label_type="tag",
                    source_model="unit-test",
                )
            )
            db.session.commit()
            album_id = album.id
            image_one_id = image_one.id

        mock_label.return_value = {
            "status": "success",
            "description": "fresh label",
            "nsfw_rating": "SAFE",
            "tags": ["tagged"],
        }

        result = label_album_task.run(album_id=album_id, prompt_type="sd_training", force=False)

        assert result["status"] == "success"
        assert result["total"] == 1
        assert result["success"] == 1
        assert result["failed"] == 0
        assert image_one_id in result["results"]

        with client.application.app_context():
            labels = Label.query.filter_by(image_id=image_one_id).all()
            assert labels, "Expected labels to be created for unlabeled image"
