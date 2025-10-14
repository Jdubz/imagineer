"""
Pytest configuration and fixtures for backend tests
"""
import pytest
import tempfile
import yaml
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from server.api import app as flask_app


@pytest.fixture
def app():
    """Create and configure a test Flask app instance"""
    flask_app.config.update({
        "TESTING": True,
    })
    yield flask_app


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
        'model': {
            'default': 'runwayml/stable-diffusion-v1-5',
            'cache_dir': 'models/'
        },
        'generation': {
            'width': 512,
            'height': 512,
            'steps': 25,
            'guidance_scale': 7.5,
            'negative_prompt': 'test negative prompt',
            'batch_size': 1,
            'num_images': 1
        },
        'output': {
            'directory': 'outputs/',
            'format': 'png',
            'save_metadata': True
        },
        'training': {
            'learning_rate': 0.0001,
            'lora_rank': 4,
            'lora_alpha': 4,
            'lora_dropout': 0.1,
            'batch_size': 1,
            'gradient_accumulation_steps': 4
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
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
        'prompt': 'a beautiful landscape',
        'seed': 42,
        'steps': 25,
        'width': 512,
        'height': 512,
        'guidance_scale': 7.5,
        'negative_prompt': 'blurry, low quality'
    }
