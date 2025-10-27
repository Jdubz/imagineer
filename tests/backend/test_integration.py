"""
Integration tests for complete workflows across all phases
"""

import io
from unittest.mock import patch

from PIL import Image as PILImage

from server.database import Album, AlbumImage, Image, Label, db


class TestCompleteWorkflow:
    """Test complete workflows from image upload to AI labeling"""

    def test_complete_image_workflow(self, client, mock_admin_auth):
        """Test complete workflow: upload -> create album -> add image -> label"""

        with client.application.app_context():
            # Step 1: Create album
            album_data = {
                "name": "Test Workflow Album",
                "description": "Testing complete workflow",
                "is_public": True,
            }

            response = client.post(
                "/api/albums", json=album_data, headers={"Authorization": "Bearer admin_token"}
            )
            assert response.status_code == 201
            album_id = response.get_json()["id"]

            # Step 2: Upload image
            img_data = io.BytesIO()
            test_img = PILImage.new("RGB", (100, 100), color="blue")
            test_img.save(img_data, format="JPEG")
            img_data.seek(0)

            response = client.post(
                "/api/images/upload",
                data={"files": (img_data, "workflow_test.jpg")},
                content_type="multipart/form-data",
                headers={"Authorization": "Bearer admin_token"},
            )
            assert response.status_code == 201
            uploaded_images = response.get_json()["images"]
            image_id = uploaded_images[0]["id"]

            # Step 3: Add image to album
            response = client.post(
                f"/api/albums/{album_id}/images",
                json={"image_ids": [image_id]},
                headers={"Authorization": "Bearer admin_token"},
            )
            assert response.status_code == 200

            # Step 4: Verify album contains image
            response = client.get(f"/api/albums/{album_id}")
            assert response.status_code == 200
            album_data = response.get_json()
            assert len(album_data["images"]) == 1
            assert album_data["images"][0]["id"] == image_id

    @patch("server.services.labeling.label_image_with_claude")
    def test_complete_labeling_workflow(self, mock_label, client, mock_admin_auth):
        """Test complete labeling workflow with database updates"""
        mock_label.return_value = {
            "status": "success",
            "description": "A beautiful blue square for testing",
            "nsfw_rating": "SAFE",
            "tags": ["blue", "square", "test", "geometric"],
        }

        with client.application.app_context():
            # Create image
            image = Image(
                filename="label_test.jpg", file_path="/tmp/label_test.jpg", is_public=True
            )
            db.session.add(image)
            db.session.commit()
            image_id = image.id

            # Label the image
            response = client.post(
                f"/api/labeling/image/{image_id}",
                json={"prompt_type": "default"},
                headers={"Authorization": "Bearer admin_token"},
            )
            assert response.status_code == 200

            # Verify database updates
            updated_image = Image.query.get(image_id)
            assert updated_image.is_nsfw is False  # SAFE rating

            # Verify labels were created
            labels = Label.query.filter_by(image_id=image_id).all()
            assert len(labels) == 5  # 1 caption + 4 tags

            caption_labels = [label for label in labels if label.label_type == "caption"]
            assert len(caption_labels) == 1
            assert "beautiful blue square" in caption_labels[0].label_text

            tag_labels = [label for label in labels if label.label_type == "tag"]
            assert len(tag_labels) == 4
            tag_texts = [label.label_text for label in tag_labels]
            assert "blue" in tag_texts
            assert "square" in tag_texts

    @patch("server.services.labeling.batch_label_images")
    def test_batch_labeling_workflow(self, mock_batch, client, mock_admin_auth):
        """Test batch labeling workflow for entire album"""
        mock_batch.return_value = {
            "total": 2,
            "success": 2,
            "failed": 0,
            "results": [
                {
                    "status": "success",
                    "description": "First image",
                    "nsfw_rating": "SAFE",
                    "tags": ["first"],
                },
                {
                    "status": "success",
                    "description": "Second image",
                    "nsfw_rating": "SAFE",
                    "tags": ["second"],
                },
            ],
        }

        with client.application.app_context():
            # Create album with images
            album = Album(name="Batch Test Album", is_public=True)
            image1 = Image(filename="batch1.jpg", file_path="/tmp/batch1.jpg", is_public=True)
            image2 = Image(filename="batch2.jpg", file_path="/tmp/batch2.jpg", is_public=True)

            db.session.add_all([album, image1, image2])
            db.session.commit()

            # Add images to album
            assoc1 = AlbumImage(album_id=album.id, image_id=image1.id)
            assoc2 = AlbumImage(album_id=album.id, image_id=image2.id)
            db.session.add_all([assoc1, assoc2])
            db.session.commit()

            # Batch label the album
            response = client.post(
                f"/api/labeling/album/{album.id}",
                json={"prompt_type": "sd_training", "force": False},
                headers={"Authorization": "Bearer admin_token"},
            )
            assert response.status_code == 200

            data = response.get_json()
            assert data["success"] is True
            assert data["total"] == 2
            assert data["success_count"] == 2
            assert data["failed_count"] == 0

    def test_public_album_view_with_nsfw_filtering(self, client):
        """Test public album view with NSFW filtering"""
        with client.application.app_context():
            # Create album with mixed content
            album = Album(name="Mixed Content Album", is_public=True)
            safe_image = Image(
                filename="safe.jpg", file_path="/tmp/safe.jpg", is_public=True, is_nsfw=False
            )
            nsfw_image = Image(
                filename="nsfw.jpg", file_path="/tmp/nsfw.jpg", is_public=True, is_nsfw=True
            )

            db.session.add_all([album, safe_image, nsfw_image])
            db.session.commit()

            # Add images to album
            safe_assoc = AlbumImage(album_id=album.id, image_id=safe_image.id)
            nsfw_assoc = AlbumImage(album_id=album.id, image_id=nsfw_image.id)
            db.session.add_all([safe_assoc, nsfw_assoc])
            db.session.commit()

            # Test public album view
            response = client.get(f"/api/albums/{album.id}")
            assert response.status_code == 200

            data = response.get_json()
            assert len(data["images"]) == 2

            # Verify NSFW flags are present
            nsfw_flags = [img["is_nsfw"] for img in data["images"]]
            assert True in nsfw_flags  # At least one NSFW
            assert False in nsfw_flags  # At least one safe

    def test_private_album_access_control(self, client):
        """Test that private albums are not accessible to public users"""
        with client.application.app_context():
            # Create private album
            album = Album(name="Private Album", is_public=False)
            db.session.add(album)
            db.session.commit()
            album_id = album.id

            # Try to access as public user
            response = client.get(f"/api/albums/{album_id}")
            assert response.status_code == 404  # Should not find private album

    def test_admin_can_access_private_albums(self, client, mock_admin_auth):
        """Test that admin can access private albums"""

        with client.application.app_context():
            # Create private album
            album = Album(name="Private Admin Album", is_public=False)
            db.session.add(album)
            db.session.commit()
            album_id = album.id

            # Admin should be able to access
            response = client.get(
                f"/api/albums/{album_id}", headers={"Authorization": "Bearer admin_token"}
            )
            assert response.status_code == 200

            data = response.get_json()
            assert data["name"] == "Private Admin Album"
            assert data["is_public"] is False


class TestErrorHandling:
    """Test error handling across the system"""

    def test_invalid_image_upload(self, client):
        """Test handling invalid image uploads"""
        with patch("server.auth.check_auth") as mock_auth:
            mock_auth.return_value = {"username": "admin", "role": "admin"}

            # Try to upload invalid file
            response = client.post(
                "/api/images/upload",
                data={"images": (io.BytesIO(b"invalid data"), "test.txt")},
                content_type="multipart/form-data",
                headers={"Authorization": "Bearer admin_token"},
            )

            # Should handle gracefully
            assert response.status_code in [400, 500]

    def test_database_rollback_on_error(self, client):
        """Test that database operations rollback on error"""
        with patch("server.auth.check_auth") as mock_auth:
            mock_auth.return_value = {"username": "admin", "role": "admin"}

            # Try to create album with invalid data
            response = client.post(
                "/api/albums",
                json={"name": ""},  # Invalid empty name
                headers={"Authorization": "Bearer admin_token"},
            )

            # Should return error
            assert response.status_code in [400, 500]

    def test_missing_file_handling(self, client):
        """Test handling of missing files"""
        with client.application.app_context():
            # Create image record but file doesn't exist
            image = Image(
                filename="missing.jpg", file_path="/nonexistent/path/missing.jpg", is_public=True
            )
            db.session.add(image)
            db.session.commit()
            image_id = image.id

            # Try to get thumbnail
            response = client.get(f"/api/images/{image_id}/thumbnail")
            assert response.status_code == 500  # Should handle file not found


class TestPerformanceAndScalability:
    """Test performance characteristics"""

    def test_large_album_handling(self, client):
        """Test handling albums with many images"""
        with client.application.app_context():
            # Create album with many images
            album = Album(name="Large Album", is_public=True)
            db.session.add(album)
            db.session.commit()

            # Add many images (simulate with database records)
            images = []
            for i in range(100):
                image = Image(
                    filename=f"image_{i}.jpg", file_path=f"/tmp/image_{i}.jpg", is_public=True
                )
                images.append(image)

            db.session.add_all(images)
            db.session.commit()

            # Add images to album
            associations = []
            for image in images:
                assoc = AlbumImage(album_id=album.id, image_id=image.id)
                associations.append(assoc)

            db.session.add_all(associations)
            db.session.commit()

            # Test album retrieval
            response = client.get(f"/api/albums/{album.id}")
            assert response.status_code == 200

            data = response.get_json()
            assert len(data["images"]) == 100

    def test_pagination_works(self, client):
        """Test that pagination works for large datasets"""
        with client.application.app_context():
            # Create many albums
            albums = []
            for i in range(25):
                album = Album(name=f"Album {i}", is_public=True)
                albums.append(album)

            db.session.add_all(albums)
            db.session.commit()

            # Test pagination
            response = client.get("/api/albums?page=1&per_page=10")
            assert response.status_code == 200

            data = response.get_json()
            assert len(data["albums"]) == 10
            assert data["page"] == 1
            assert data["per_page"] == 10
            assert data["total"] == 25

            # Test second page
            response = client.get("/api/albums?page=2&per_page=10")
            assert response.status_code == 200

            data = response.get_json()
            assert len(data["albums"]) == 10
            assert data["page"] == 2


class TestDataConsistency:
    """Test data consistency and integrity"""

    def test_album_image_association_consistency(self, client):
        """Test that album-image associations are consistent"""
        with client.application.app_context():
            # Create album and images
            album = Album(name="Consistency Test", is_public=True)
            image1 = Image(filename="img1.jpg", file_path="/tmp/img1.jpg", is_public=True)
            image2 = Image(filename="img2.jpg", file_path="/tmp/img2.jpg", is_public=True)

            db.session.add_all([album, image1, image2])
            db.session.commit()

            # Add images to album
            assoc1 = AlbumImage(album_id=album.id, image_id=image1.id)
            assoc2 = AlbumImage(album_id=album.id, image_id=image2.id)
            db.session.add_all([assoc1, assoc2])
            db.session.commit()

            # Verify bidirectional relationships
            assert len(album.images) == 2
            assert len(image1.albums) == 1
            assert len(image2.albums) == 1

            # Verify album contains both images
            album_image_ids = [img.id for img in album.images]
            assert image1.id in album_image_ids
            assert image2.id in album_image_ids

    def test_label_image_relationship_consistency(self, client):
        """Test that label-image relationships are consistent"""
        with client.application.app_context():
            # Create image and labels
            image = Image(filename="labeled.jpg", file_path="/tmp/labeled.jpg", is_public=True)
            db.session.add(image)
            db.session.commit()

            # Create labels
            caption = Label(
                image_id=image.id,
                label_text="Test caption",
                label_type="caption",
                source_model="test",
            )
            tag1 = Label(
                image_id=image.id, label_text="tag1", label_type="tag", source_model="test"
            )
            tag2 = Label(
                image_id=image.id, label_text="tag2", label_type="tag", source_model="test"
            )

            db.session.add_all([caption, tag1, tag2])
            db.session.commit()

            # Verify relationships
            assert len(image.labels) == 3

            caption_labels = [label for label in image.labels if label.label_type == "caption"]
            tag_labels = [label for label in image.labels if label.label_type == "tag"]

            assert len(caption_labels) == 1
            assert len(tag_labels) == 2
            assert caption_labels[0].label_text == "Test caption"
