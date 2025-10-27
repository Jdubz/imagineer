"""
Pytest configuration and fixtures for backend tests
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from server.api import app as flask_app  # noqa: E402


@pytest.fixture
def app():
    """Create and configure a test Flask app instance"""
    # Use a temporary database for tests
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        test_db_path = tmp_db.name

    flask_app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{test_db_path}",
        }
    )

    # Recreate database with current schema
    from server.database import db

    with flask_app.app_context():
        db.drop_all()
        db.create_all()

    yield flask_app

    # Cleanup
    try:
        os.unlink(test_db_path)
    except OSError:
        pass


@pytest.fixture
def client(app):
    """A test client for the app"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands"""
    return app.test_cli_runner()


@pytest.fixture
def temp_config():
    """Create a temporary config file for testing"""
    config_data = {
        "model": {"default": "runwayml/stable-diffusion-v1-5", "cache_dir": "models/"},
        "generation": {
            "width": 512,
            "height": 512,
            "steps": 25,
            "guidance_scale": 7.5,
            "negative_prompt": "test negative prompt",
            "batch_size": 1,
            "num_images": 1,
        },
        "output": {"directory": "outputs/", "format": "png", "save_metadata": True},
        "training": {
            "learning_rate": 0.0001,
            "lora_rank": 4,
            "lora_alpha": 4,
            "lora_dropout": 0.1,
            "batch_size": 1,
            "gradient_accumulation_steps": 4,
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_job_data():
    """Sample job data for testing"""
    return {
        "prompt": "a beautiful landscape",
        "seed": 42,
        "steps": 25,
        "width": 512,
        "height": 512,
        "guidance_scale": 7.5,
        "negative_prompt": "blurry, low quality",
    }


@pytest.fixture
def mock_admin_auth():
    """Mock admin authentication"""
    from unittest.mock import MagicMock, patch

    # Create a mock admin user
    admin_user = MagicMock()
    admin_user.email = "admin@test.com"
    admin_user.name = "Admin User"
    admin_user.picture = ""
    admin_user.role = "admin"
    admin_user.is_authenticated = True
    admin_user.is_admin.return_value = True

    with patch("server.auth.current_user", admin_user):
        yield admin_user


@pytest.fixture
def mock_public_auth():
    """Mock public user authentication"""
    from unittest.mock import MagicMock, patch

    # Create a mock public user
    public_user = MagicMock()
    public_user.email = "public@test.com"
    public_user.name = "Public User"
    public_user.picture = ""
    public_user.role = None
    public_user.is_authenticated = True
    public_user.is_admin.return_value = False

    with patch("server.auth.current_user", public_user):
        yield public_user
