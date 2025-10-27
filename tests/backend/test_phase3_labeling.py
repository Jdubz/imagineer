"""
Tests for Phase 3: AI Labeling System
"""

import base64
import json
from io import BytesIO
from unittest.mock import MagicMock, mock_open, patch

import pytest
from PIL import Image as PILImage

from server.database import Album, AlbumImage, Image, Label, db
from server.services.labeling import (
    batch_label_images,
    encode_image,
    get_labeling_prompts,
    label_image_with_claude,
)


class TestImageEncoding:
    """Test image encoding for Claude API"""

    def test_encode_image_small(self, temp_output_dir):
        """Test encoding small image"""
        # Create test image
        test_img = PILImage.new("RGB", (100, 100), color="red")
        img_path = temp_output_dir / "test.jpg"
        test_img.save(img_path, "JPEG")

        encoded = encode_image(str(img_path))

        # Should be base64 encoded
        assert isinstance(encoded, str)
        # Decode and verify it's valid
        decoded = base64.b64decode(encoded)
        assert len(decoded) > 0

    def test_encode_image_large(self, temp_output_dir):
        """Test encoding large image (should be resized)"""
        # Create large test image
        test_img = PILImage.new("RGB", (2000, 2000), color="blue")
        img_path = temp_output_dir / "large.jpg"
        test_img.save(img_path, "JPEG")

        encoded = encode_image(str(img_path))

        # Should be resized and encoded
        assert isinstance(encoded, str)
        decoded = base64.b64decode(encoded)

        # Verify it was resized by checking the decoded image
        with BytesIO(decoded) as buffer:
            resized_img = PILImage.open(buffer)
            assert max(resized_img.size) <= 1568

    def test_encode_image_rgba_conversion(self, temp_output_dir):
        """Test RGBA to RGB conversion"""
        # Create RGBA image
        test_img = PILImage.new("RGBA", (100, 100), color=(255, 0, 0, 128))
        img_path = temp_output_dir / "rgba.png"
        test_img.save(img_path, "PNG")

        encoded = encode_image(str(img_path))

        # Should convert to RGB and encode
        assert isinstance(encoded, str)
        decoded = base64.b64decode(encoded)

        with BytesIO(decoded) as buffer:
            converted_img = PILImage.open(buffer)
            assert converted_img.mode == "RGB"


class TestLabelingPrompts:
    """Test labeling prompt templates"""

    def test_get_labeling_prompts(self):
        """Test getting labeling prompts"""
        prompts = get_labeling_prompts()

        assert "default" in prompts
        assert "sd_training" in prompts
        assert "detailed" in prompts

        # Check prompt structure
        for prompt_type, prompt_text in prompts.items():
            assert isinstance(prompt_text, str)
            assert len(prompt_text) > 0
            assert "NSFW" in prompt_text  # All prompts should include NSFW rating

    def test_prompt_types(self):
        """Test different prompt types have different content"""
        prompts = get_labeling_prompts()

        # Each prompt should be different
        assert prompts["default"] != prompts["sd_training"]
        assert prompts["default"] != prompts["detailed"]
        assert prompts["sd_training"] != prompts["detailed"]

        # SD training should mention Stable Diffusion
        assert "Stable Diffusion" in prompts["sd_training"]

        # Detailed should mention comprehensive analysis
        assert "detailed" in prompts["detailed"].lower()


class TestClaudeLabeling:
    """Test Claude API integration"""

    @patch("server.services.labeling.ANTHROPIC_AVAILABLE", False)
    def test_label_image_anthropic_unavailable(self, temp_output_dir):
        """Test labeling when Anthropic library is unavailable"""
        test_img = PILImage.new("RGB", (100, 100), color="red")
        img_path = temp_output_dir / "test.jpg"
        test_img.save(img_path, "JPEG")

        result = label_image_with_claude(str(img_path))

        assert result["status"] == "error"
        assert "not available" in result["message"]

    @patch("server.services.labeling.ANTHROPIC_AVAILABLE", True)
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""})
    def test_label_image_no_api_key(self, temp_output_dir):
        """Test labeling when API key is not set"""
        test_img = PILImage.new("RGB", (100, 100), color="red")
        img_path = temp_output_dir / "test.jpg"
        test_img.save(img_path, "JPEG")

        result = label_image_with_claude(str(img_path))

        assert result["status"] == "error"
        assert "not set" in result["message"]

    @patch("server.services.labeling.ANTHROPIC_AVAILABLE", True)
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test_key"})
    @patch("server.services.labeling.Anthropic")
    def test_label_image_success(self, mock_anthropic, temp_output_dir):
        """Test successful image labeling"""
        # Create test image
        test_img = PILImage.new("RGB", (100, 100), color="red")
        img_path = temp_output_dir / "test.jpg"
        test_img.save(img_path, "JPEG")

        # Mock Claude response
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[
            0
        ].text = """
        DESCRIPTION: A beautiful red square image
        NSFW: SAFE
        TAGS: red, square, geometric, abstract, colorful
        """

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        result = label_image_with_claude(str(img_path))

        assert result["status"] == "success"
        assert result["description"] == "A beautiful red square image"
        assert result["nsfw_rating"] == "SAFE"
        assert "red" in result["tags"]
        assert "square" in result["tags"]

    @patch("server.services.labeling.ANTHROPIC_AVAILABLE", True)
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test_key"})
    @patch("server.services.labeling.Anthropic")
    def test_label_image_api_error(self, mock_anthropic, temp_output_dir):
        """Test handling Claude API errors"""
        test_img = PILImage.new("RGB", (100, 100), color="red")
        img_path = temp_output_dir / "test.jpg"
        test_img.save(img_path, "JPEG")

        # Mock API error
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API Error")
        mock_anthropic.return_value = mock_client

        result = label_image_with_claude(str(img_path))

        assert result["status"] == "error"
        assert "API Error" in result["message"]

    @patch("server.services.labeling.ANTHROPIC_AVAILABLE", True)
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test_key"})
    @patch("server.services.labeling.Anthropic")
    def test_label_image_different_prompts(self, mock_anthropic, temp_output_dir):
        """Test labeling with different prompt types"""
        test_img = PILImage.new("RGB", (100, 100), color="red")
        img_path = temp_output_dir / "test.jpg"
        test_img.save(img_path, "JPEG")

        # Mock Claude response
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[
            0
        ].text = """
        CAPTION: A detailed red square for training
        NSFW: SAFE
        TAGS: red, square, training, detailed
        """

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        result = label_image_with_claude(str(img_path), "sd_training")

        assert result["status"] == "success"
        assert result["description"] == "A detailed red square for training"


class TestBatchLabeling:
    """Test batch labeling functionality"""

    @patch("server.services.labeling.label_image_with_claude")
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

    @patch("server.services.labeling.label_image_with_claude")
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

        results = batch_label_images(img_paths, progress_callback=progress_callback)

        assert len(progress_calls) == 2
        assert progress_calls[0] == (1, 2)
        assert progress_calls[1] == (2, 2)


class TestLabelingAPI:
    """Test labeling API endpoints"""

    def test_label_image_endpoint_unauthorized(self, client):
        """Test labeling endpoint without admin auth"""
        response = client.post("/api/labeling/image/1")
        assert response.status_code == 401

    @patch("server.services.labeling.label_image_with_claude")
    def test_label_image_endpoint_success(self, mock_label, client):
        """Test successful image labeling via API"""
        with client.application.app_context():
            # Create test image
            image = Image(filename="test.jpg", file_path="/tmp/test.jpg", is_public=True)
            db.session.add(image)
            db.session.commit()
            image_id = image.id

        # Mock successful labeling
        mock_label.return_value = {
            "status": "success",
            "description": "A beautiful test image",
            "nsfw_rating": "SAFE",
            "tags": ["test", "beautiful"],
        }

        with patch("server.auth.check_auth") as mock_auth:
            mock_auth.return_value = {"username": "admin", "role": "admin"}

            response = client.post(
                f"/api/labeling/image/{image_id}",
                json={"prompt_type": "default"},
                headers={"Authorization": "Bearer admin_token"},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert data["description"] == "A beautiful test image"
            assert data["nsfw_rating"] == "SAFE"
            assert "test" in data["tags"]

    @patch("server.services.labeling.label_image_with_claude")
    def test_label_image_endpoint_error(self, mock_label, client):
        """Test image labeling API error handling"""
        with client.application.app_context():
            # Create test image
            image = Image(filename="test.jpg", file_path="/tmp/test.jpg", is_public=True)
            db.session.add(image)
            db.session.commit()
            image_id = image.id

        # Mock labeling error
        mock_label.return_value = {"status": "error", "message": "Claude API failed"}

        with patch("server.auth.check_auth") as mock_auth:
            mock_auth.return_value = {"username": "admin", "role": "admin"}

            response = client.post(
                f"/api/labeling/image/{image_id}",
                json={"prompt_type": "default"},
                headers={"Authorization": "Bearer admin_token"},
            )

            assert response.status_code == 500
            data = response.get_json()
            assert "error" in data

    def test_label_album_endpoint_unauthorized(self, client):
        """Test album labeling endpoint without admin auth"""
        response = client.post("/api/labeling/album/1")
        assert response.status_code == 401

    @patch("server.services.labeling.batch_label_images")
    def test_label_album_endpoint_success(self, mock_batch, client):
        """Test successful album labeling via API"""
        with client.application.app_context():
            # Create test album and images
            album = Album(name="Test Album")
            image1 = Image(filename="test1.jpg", file_path="/tmp/test1.jpg", is_public=True)
            image2 = Image(filename="test2.jpg", file_path="/tmp/test2.jpg", is_public=True)

            db.session.add_all([album, image1, image2])
            db.session.commit()

            # Add images to album
            assoc1 = AlbumImage(album_id=album.id, image_id=image1.id)
            assoc2 = AlbumImage(album_id=album.id, image_id=image2.id)
            db.session.add_all([assoc1, assoc2])
            db.session.commit()

            album_id = album.id

        # Mock successful batch labeling
        mock_batch.return_value = {
            "total": 2,
            "success": 2,
            "failed": 0,
            "results": [
                {
                    "status": "success",
                    "description": "Image 1",
                    "nsfw_rating": "SAFE",
                    "tags": ["test"],
                },
                {
                    "status": "success",
                    "description": "Image 2",
                    "nsfw_rating": "SAFE",
                    "tags": ["test"],
                },
            ],
        }

        with patch("server.auth.check_auth") as mock_auth:
            mock_auth.return_value = {"username": "admin", "role": "admin"}

            response = client.post(
                f"/api/labeling/album/{album_id}",
                json={"prompt_type": "sd_training", "force": False},
                headers={"Authorization": "Bearer admin_token"},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert data["total"] == 2
            assert data["success_count"] == 2
            assert data["failed_count"] == 0

    def test_label_album_empty(self, client):
        """Test labeling empty album"""
        with client.application.app_context():
            # Create empty album
            album = Album(name="Empty Album")
            db.session.add(album)
            db.session.commit()
            album_id = album.id

        with patch("server.auth.check_auth") as mock_auth:
            mock_auth.return_value = {"username": "admin", "role": "admin"}

            response = client.post(
                f"/api/labeling/album/{album_id}",
                json={"prompt_type": "default"},
                headers={"Authorization": "Bearer admin_token"},
            )

            assert response.status_code == 400
            data = response.get_json()
            assert "empty" in data["error"].lower()


class TestNSFWClassification:
    """Test NSFW classification and database updates"""

    @patch("server.services.labeling.label_image_with_claude")
    def test_nsfw_classification_safe(self, mock_label, client):
        """Test SAFE classification updates database correctly"""
        with client.application.app_context():
            # Create test image
            image = Image(filename="safe.jpg", file_path="/tmp/safe.jpg", is_public=True)
            db.session.add(image)
            db.session.commit()
            image_id = image.id

        # Mock SAFE classification
        mock_label.return_value = {
            "status": "success",
            "description": "A safe image",
            "nsfw_rating": "SAFE",
            "tags": ["safe", "family-friendly"],
        }

        with patch("server.auth.check_auth") as mock_auth:
            mock_auth.return_value = {"username": "admin", "role": "admin"}

            response = client.post(
                f"/api/labeling/image/{image_id}",
                json={"prompt_type": "default"},
                headers={"Authorization": "Bearer admin_token"},
            )

            assert response.status_code == 200

            # Verify database update
            updated_image = Image.query.get(image_id)
            assert updated_image.is_nsfw is False

    @patch("server.services.labeling.label_image_with_claude")
    def test_nsfw_classification_explicit(self, mock_label, client):
        """Test EXPLICIT classification updates database correctly"""
        with client.application.app_context():
            # Create test image
            image = Image(filename="explicit.jpg", file_path="/tmp/explicit.jpg", is_public=True)
            db.session.add(image)
            db.session.commit()
            image_id = image.id

        # Mock EXPLICIT classification
        mock_label.return_value = {
            "status": "success",
            "description": "An explicit image",
            "nsfw_rating": "EXPLICIT",
            "tags": ["explicit", "adult"],
        }

        with patch("server.auth.check_auth") as mock_auth:
            mock_auth.return_value = {"username": "admin", "role": "admin"}

            response = client.post(
                f"/api/labeling/image/{image_id}",
                json={"prompt_type": "default"},
                headers={"Authorization": "Bearer admin_token"},
            )

            assert response.status_code == 200

            # Verify database update
            updated_image = Image.query.get(image_id)
            assert updated_image.is_nsfw is True

    @patch("server.services.labeling.label_image_with_claude")
    def test_label_storage(self, mock_label, client):
        """Test that labels are properly stored in database"""
        with client.application.app_context():
            # Create test image
            image = Image(filename="test.jpg", file_path="/tmp/test.jpg", is_public=True)
            db.session.add(image)
            db.session.commit()
            image_id = image.id

        # Mock labeling with caption and tags
        mock_label.return_value = {
            "status": "success",
            "description": "A beautiful landscape with mountains",
            "nsfw_rating": "SAFE",
            "tags": ["landscape", "mountains", "nature", "beautiful"],
        }

        with patch("server.auth.check_auth") as mock_auth:
            mock_auth.return_value = {"username": "admin", "role": "admin"}

            response = client.post(
                f"/api/labeling/image/{image_id}",
                json={"prompt_type": "default"},
                headers={"Authorization": "Bearer admin_token"},
            )

            assert response.status_code == 200

            # Verify labels are stored
            labels = Label.query.filter_by(image_id=image_id).all()
            assert len(labels) == 5  # 1 caption + 4 tags

            # Check caption label
            caption_labels = [label for label in labels if label.label_type == "caption"]
            assert len(caption_labels) == 1
            assert "landscape" in caption_labels[0].label_text

            # Check tag labels
            tag_labels = [label for label in labels if label.label_type == "tag"]
            assert len(tag_labels) == 4
            tag_texts = [label.label_text for label in tag_labels]
            assert "landscape" in tag_texts
            assert "mountains" in tag_texts
            assert "nature" in tag_texts
            assert "beautiful" in tag_texts

            # Check source model
            for label in labels:
                assert label.source_model == "claude-3-5-sonnet"
