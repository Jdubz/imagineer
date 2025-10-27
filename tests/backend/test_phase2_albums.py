"""
Tests for Phase 2: Album System & Image Management
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from PIL import Image as PILImage
import io

from server.database import db, Album, Image, AlbumImage, Label


class TestAlbumAPI:
    """Test album API endpoints"""

    def test_get_albums_public(self, client):
        """Test getting albums as public user"""
        response = client.get('/api/albums')
        assert response.status_code == 200
        data = response.get_json()
        assert 'albums' in data
        assert 'total' in data
        assert 'page' in data
        assert 'per_page' in data

    def test_get_album_public(self, client):
        """Test getting single album as public user"""
        # Create a test album
        with client.application.app_context():
            album = Album(name="Test Album", description="Test Description", is_public=True)
            db.session.add(album)
            db.session.commit()
            album_id = album.id

        response = client.get(f'/api/albums/{album_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['name'] == "Test Album"
        assert data['description'] == "Test Description"

    def test_get_album_not_found(self, client):
        """Test getting non-existent album"""
        response = client.get('/api/albums/99999')
        assert response.status_code == 404

    def test_create_album_admin(self, client):
        """Test creating album as admin"""
        # Mock admin authentication
        with patch('server.auth.check_auth') as mock_auth:
            mock_auth.return_value = {'username': 'admin', 'role': 'admin'}
            
            album_data = {
                'name': 'New Album',
                'description': 'Album Description',
                'is_public': True
            }
            
            response = client.post('/api/albums', 
                                 json=album_data,
                                 headers={'Authorization': 'Bearer admin_token'})
            
            assert response.status_code == 201
            data = response.get_json()
            assert data['name'] == 'New Album'
            assert data['description'] == 'Album Description'

    def test_create_album_unauthorized(self, client):
        """Test creating album without admin auth"""
        album_data = {
            'name': 'New Album',
            'description': 'Album Description'
        }
        
        response = client.post('/api/albums', json=album_data)
        assert response.status_code == 401

    def test_update_album_admin(self, client):
        """Test updating album as admin"""
        with client.application.app_context():
            # Create test album
            album = Album(name="Original Name", description="Original Description")
            db.session.add(album)
            db.session.commit()
            album_id = album.id

        with patch('server.auth.check_auth') as mock_auth:
            mock_auth.return_value = {'username': 'admin', 'role': 'admin'}
            
            update_data = {
                'name': 'Updated Name',
                'description': 'Updated Description'
            }
            
            response = client.put(f'/api/albums/{album_id}',
                                json=update_data,
                                headers={'Authorization': 'Bearer admin_token'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['name'] == 'Updated Name'
            assert data['description'] == 'Updated Description'

    def test_delete_album_admin(self, client):
        """Test deleting album as admin"""
        with client.application.app_context():
            # Create test album
            album = Album(name="To Delete", description="Will be deleted")
            db.session.add(album)
            db.session.commit()
            album_id = album.id

        with patch('server.auth.check_auth') as mock_auth:
            mock_auth.return_value = {'username': 'admin', 'role': 'admin'}
            
            response = client.delete(f'/api/albums/{album_id}',
                                   headers={'Authorization': 'Bearer admin_token'})
            
            assert response.status_code == 200
            
            # Verify album is deleted
            deleted_album = Album.query.get(album_id)
            assert deleted_album is None

    def test_add_images_to_album_admin(self, client):
        """Test adding images to album as admin"""
        with client.application.app_context():
            # Create test album and images
            album = Album(name="Test Album")
            db.session.add(album)
            
            image1 = Image(filename="test1.jpg", file_path="/tmp/test1.jpg", is_public=True)
            image2 = Image(filename="test2.jpg", file_path="/tmp/test2.jpg", is_public=True)
            db.session.add_all([image1, image2])
            db.session.commit()
            
            album_id = album.id
            image_ids = [image1.id, image2.id]

        with patch('server.auth.check_auth') as mock_auth:
            mock_auth.return_value = {'username': 'admin', 'role': 'admin'}
            
            response = client.post(f'/api/albums/{album_id}/images',
                                 json={'image_ids': image_ids},
                                 headers={'Authorization': 'Bearer admin_token'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['added_count'] == 2

    def test_remove_image_from_album_admin(self, client):
        """Test removing image from album as admin"""
        with client.application.app_context():
            # Create test album and image
            album = Album(name="Test Album")
            image = Image(filename="test.jpg", file_path="/tmp/test.jpg", is_public=True)
            db.session.add_all([album, image])
            db.session.commit()
            
            # Add image to album
            album_image = AlbumImage(album_id=album.id, image_id=image.id)
            db.session.add(album_image)
            db.session.commit()
            
            album_id = album.id
            image_id = image.id

        with patch('server.auth.check_auth') as mock_auth:
            mock_auth.return_value = {'username': 'admin', 'role': 'admin'}
            
            response = client.delete(f'/api/albums/{album_id}/images/{image_id}',
                                   headers={'Authorization': 'Bearer admin_token'})
            
            assert response.status_code == 200
            
            # Verify association is removed
            association = AlbumImage.query.filter_by(
                album_id=album_id, image_id=image_id
            ).first()
            assert association is None


class TestImageAPI:
    """Test image API endpoints"""

    def test_upload_images_admin(self, client):
        """Test uploading images as admin"""
        with patch('server.auth.check_auth') as mock_auth:
            mock_auth.return_value = {'username': 'admin', 'role': 'admin'}
            
            # Create test image data
            img_data = io.BytesIO()
            test_img = PILImage.new('RGB', (100, 100), color='red')
            test_img.save(img_data, format='JPEG')
            img_data.seek(0)
            
            response = client.post('/api/images/upload',
                                 data={'images': (img_data, 'test.jpg')},
                                 content_type='multipart/form-data',
                                 headers={'Authorization': 'Bearer admin_token'})
            
            assert response.status_code == 201
            data = response.get_json()
            assert 'uploaded_count' in data
            assert data['uploaded_count'] == 1

    def test_upload_images_unauthorized(self, client):
        """Test uploading images without admin auth"""
        response = client.post('/api/images/upload')
        assert response.status_code == 401

    def test_delete_image_admin(self, client):
        """Test deleting image as admin"""
        with client.application.app_context():
            # Create test image
            image = Image(filename="test.jpg", file_path="/tmp/test.jpg", is_public=True)
            db.session.add(image)
            db.session.commit()
            image_id = image.id

        with patch('server.auth.check_auth') as mock_auth:
            mock_auth.return_value = {'username': 'admin', 'role': 'admin'}
            
            # Mock file deletion
            with patch('pathlib.Path.unlink'):
                response = client.delete(f'/api/images/{image_id}',
                                       headers={'Authorization': 'Bearer admin_token'})
                
                assert response.status_code == 200
                
                # Verify image is deleted from database
                deleted_image = Image.query.get(image_id)
                assert deleted_image is None

    def test_get_thumbnail_public(self, client):
        """Test getting image thumbnail as public user"""
        with client.application.app_context():
            # Create test image
            image = Image(filename="test.jpg", file_path="/tmp/test.jpg", is_public=True)
            db.session.add(image)
            db.session.commit()
            image_id = image.id

        # Mock thumbnail generation
        with patch('pathlib.Path.exists', return_value=True):
            with patch('flask.send_file') as mock_send:
                mock_send.return_value = "thumbnail_data"
                
                response = client.get(f'/api/images/{image_id}/thumbnail')
                assert response.status_code == 200

    def test_get_thumbnail_private_image(self, client):
        """Test getting thumbnail of private image"""
        with client.application.app_context():
            # Create private image
            image = Image(filename="private.jpg", file_path="/tmp/private.jpg", is_public=False)
            db.session.add(image)
            db.session.commit()
            image_id = image.id

        response = client.get(f'/api/images/{image_id}/thumbnail')
        assert response.status_code == 404


class TestNSFWFiltering:
    """Test NSFW filtering functionality"""

    def test_nsfw_image_creation(self, client):
        """Test creating NSFW image"""
        with client.application.app_context():
            image = Image(
                filename="nsfw.jpg", 
                file_path="/tmp/nsfw.jpg", 
                is_public=True,
                is_nsfw=True
            )
            db.session.add(image)
            db.session.commit()
            
            assert image.is_nsfw is True

    def test_safe_image_creation(self, client):
        """Test creating safe image"""
        with client.application.app_context():
            image = Image(
                filename="safe.jpg", 
                file_path="/tmp/safe.jpg", 
                is_public=True,
                is_nsfw=False
            )
            db.session.add(image)
            db.session.commit()
            
            assert image.is_nsfw is False

    def test_nsfw_filtering_in_album(self, client):
        """Test NSFW filtering in album view"""
        with client.application.app_context():
            # Create album with mixed content
            album = Album(name="Mixed Album", is_public=True)
            safe_image = Image(filename="safe.jpg", file_path="/tmp/safe.jpg", 
                             is_public=True, is_nsfw=False)
            nsfw_image = Image(filename="nsfw.jpg", file_path="/tmp/nsfw.jpg", 
                             is_public=True, is_nsfw=True)
            
            db.session.add_all([album, safe_image, nsfw_image])
            db.session.commit()
            
            # Add images to album
            safe_assoc = AlbumImage(album_id=album.id, image_id=safe_image.id)
            nsfw_assoc = AlbumImage(album_id=album.id, image_id=nsfw_image.id)
            db.session.add_all([safe_assoc, nsfw_assoc])
            db.session.commit()
            
            album_id = album.id

        response = client.get(f'/api/albums/{album_id}')
        assert response.status_code == 200
        data = response.get_json()
        
        # Should include both images with NSFW flag
        assert len(data['images']) == 2
        nsfw_flags = [img['is_nsfw'] for img in data['images']]
        assert True in nsfw_flags  # At least one NSFW image
        assert False in nsfw_flags  # At least one safe image


class TestDatabaseModels:
    """Test database models and relationships"""

    def test_album_creation(self, client):
        """Test album model creation"""
        with client.application.app_context():
            album = Album(
                name="Test Album",
                description="Test Description",
                is_public=True
            )
            db.session.add(album)
            db.session.commit()
            
            assert album.id is not None
            assert album.name == "Test Album"
            assert album.description == "Test Description"
            assert album.is_public is True

    def test_image_creation(self, client):
        """Test image model creation"""
        with client.application.app_context():
            image = Image(
                filename="test.jpg",
                file_path="/tmp/test.jpg",
                is_public=True,
                is_nsfw=False
            )
            db.session.add(image)
            db.session.commit()
            
            assert image.id is not None
            assert image.filename == "test.jpg"
            assert image.file_path == "/tmp/test.jpg"
            assert image.is_public is True
            assert image.is_nsfw is False

    def test_album_image_association(self, client):
        """Test album-image association"""
        with client.application.app_context():
            # Create album and image
            album = Album(name="Test Album")
            image = Image(filename="test.jpg", file_path="/tmp/test.jpg", is_public=True)
            db.session.add_all([album, image])
            db.session.commit()
            
            # Create association
            association = AlbumImage(album_id=album.id, image_id=image.id)
            db.session.add(association)
            db.session.commit()
            
            # Test relationships
            assert len(album.images) == 1
            assert album.images[0].id == image.id
            assert len(image.albums) == 1
            assert image.albums[0].id == album.id

    def test_label_creation(self, client):
        """Test label model creation"""
        with client.application.app_context():
            # Create image first
            image = Image(filename="test.jpg", file_path="/tmp/test.jpg", is_public=True)
            db.session.add(image)
            db.session.commit()
            
            # Create labels
            caption_label = Label(
                image_id=image.id,
                label_text="A beautiful landscape",
                label_type="caption",
                source_model="claude-3-5-sonnet"
            )
            tag_label = Label(
                image_id=image.id,
                label_text="landscape",
                label_type="tag",
                source_model="claude-3-5-sonnet"
            )
            
            db.session.add_all([caption_label, tag_label])
            db.session.commit()
            
            # Test relationships
            assert len(image.labels) == 2
            label_types = [label.label_type for label in image.labels]
            assert "caption" in label_types
            assert "tag" in label_types