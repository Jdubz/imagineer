"""
Additional pytest configuration for phase tests
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from server.database import db, Album, Image, AlbumImage, Label


@pytest.fixture
def temp_image_file():
    """Create a temporary image file for testing"""
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        # Create a simple test image
        from PIL import Image as PILImage
        test_img = PILImage.new('RGB', (100, 100), color='red')
        test_img.save(tmp.name, 'JPEG')
        yield tmp.name
    
    # Cleanup
    Path(tmp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_album(client):
    """Create a sample album for testing"""
    with client.application.app_context():
        album = Album(
            name="Test Album",
            description="Test Description",
            is_public=True
        )
        db.session.add(album)
        db.session.commit()
        yield album


@pytest.fixture
def sample_image(client):
    """Create a sample image for testing"""
    with client.application.app_context():
        image = Image(
            filename="test.jpg",
            file_path="/tmp/test.jpg",
            is_public=True,
            is_nsfw=False
        )
        db.session.add(image)
        db.session.commit()
        yield image


@pytest.fixture
def sample_album_with_images(client):
    """Create a sample album with images for testing"""
    with client.application.app_context():
        # Create album
        album = Album(name="Test Album with Images", is_public=True)
        db.session.add(album)
        db.session.commit()
        
        # Create images
        images = []
        for i in range(3):
            image = Image(
                filename=f"test_{i}.jpg",
                file_path=f"/tmp/test_{i}.jpg",
                is_public=True,
                is_nsfw=(i == 2)  # Last image is NSFW
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
        
        yield album, images


@pytest.fixture
def mock_claude_response():
    """Mock Claude API response for testing"""
    return {
        'status': 'success',
        'description': 'A beautiful test image with vibrant colors',
        'nsfw_rating': 'SAFE',
        'tags': ['beautiful', 'vibrant', 'colors', 'test', 'image'],
        'raw_response': 'DESCRIPTION: A beautiful test image with vibrant colors\nNSFW: SAFE\nTAGS: beautiful, vibrant, colors, test, image'
    }


@pytest.fixture
def mock_claude_error():
    """Mock Claude API error response for testing"""
    return {
        'status': 'error',
        'message': 'Claude API failed: Rate limit exceeded'
    }


@pytest.fixture
def admin_headers():
    """Mock admin authentication headers"""
    return {'Authorization': 'Bearer admin_token'}


@pytest.fixture
def mock_admin_auth():
    """Mock admin authentication"""
    with patch('server.auth.check_auth') as mock_auth:
        mock_auth.return_value = {'username': 'admin', 'role': 'admin'}
        yield mock_auth


@pytest.fixture
def mock_public_auth():
    """Mock public user authentication"""
    with patch('server.auth.check_auth') as mock_auth:
        mock_auth.return_value = None  # No authentication
        yield mock_auth


@pytest.fixture
def temp_upload_dir():
    """Create temporary upload directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_image_data():
    """Create sample image data for upload testing"""
    from PIL import Image as PILImage
    import io
    
    img_data = io.BytesIO()
    test_img = PILImage.new('RGB', (200, 200), color='blue')
    test_img.save(img_data, format='JPEG')
    img_data.seek(0)
    
    return img_data


@pytest.fixture(autouse=True)
def clean_database(client):
    """Clean database before each test"""
    with client.application.app_context():
        # Clear all tables
        db.session.query(Label).delete()
        db.session.query(AlbumImage).delete()
        db.session.query(Image).delete()
        db.session.query(Album).delete()
        db.session.commit()
        yield
        # Cleanup after test
        db.session.query(Label).delete()
        db.session.query(AlbumImage).delete()
        db.session.query(Image).delete()
        db.session.query(Album).delete()
        db.session.commit()


@pytest.fixture
def mock_file_operations():
    """Mock file operations for testing"""
    with patch('pathlib.Path.exists', return_value=True), \
         patch('pathlib.Path.unlink'), \
         patch('pathlib.Path.mkdir'), \
         patch('flask.send_file') as mock_send:
        mock_send.return_value = "file_data"
        yield mock_send


@pytest.fixture
def mock_pil_operations():
    """Mock PIL operations for testing"""
    with patch('PIL.Image.open') as mock_open, \
         patch('PIL.Image.new') as mock_new:
        
        # Create mock image
        mock_img = MagicMock()
        mock_img.size = (100, 100)
        mock_img.mode = 'RGB'
        mock_img.save = MagicMock()
        mock_img.thumbnail = MagicMock()
        mock_img.convert = MagicMock(return_value=mock_img)
        mock_img.resize = MagicMock(return_value=mock_img)
        
        mock_open.return_value.__enter__.return_value = mock_img
        mock_new.return_value = mock_img
        
        yield mock_img