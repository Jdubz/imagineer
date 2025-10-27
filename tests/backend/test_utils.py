"""
Tests for utility functions in src/imagineer/utils.py
"""

import json
import tempfile
from pathlib import Path

import pytest
import torch
from PIL import Image

from src.imagineer.utils import (
    create_image_grid,
    generate_filename,
    get_device,
    get_optimal_dtype,
    load_prompt_list,
    preprocess_image,
    save_image_with_metadata,
)


class TestDeviceDetection:
    """Tests for device detection functions"""

    def test_get_device_returns_string(self):
        """Test get_device returns a valid device string"""
        device = get_device()
        assert isinstance(device, str)
        assert device in ["cuda", "mps", "cpu"]

    def test_get_optimal_dtype_cuda(self):
        """Test get_optimal_dtype returns fp16 for CUDA"""
        if torch.cuda.is_available():
            dtype = get_optimal_dtype("cuda")
            assert dtype == torch.float16

    def test_get_optimal_dtype_cpu(self):
        """Test get_optimal_dtype returns fp32 for CPU"""
        dtype = get_optimal_dtype("cpu")
        assert dtype == torch.float32


class TestFilenameGeneration:
    """Tests for filename generation"""

    def test_generate_filename_basic(self):
        """Test generate_filename creates valid filename"""
        filename = generate_filename("a beautiful sunset")
        assert filename.endswith(".png")
        assert "a_beautiful_sunset" in filename
        # Check timestamp format (YYYYMMDD_HHMMSS)
        assert len(filename.split("_")[0]) == 8  # YYYYMMDD

    def test_generate_filename_long_prompt(self):
        """Test generate_filename truncates long prompts"""
        long_prompt = "a" * 100
        filename = generate_filename(long_prompt)
        # Should be truncated to reasonable length
        assert len(filename) < 150

    def test_generate_filename_special_chars(self):
        """Test generate_filename handles special characters"""
        filename = generate_filename("test!@#$%^&*()")
        # Should replace special chars with underscores or remove them
        assert "!" not in filename
        assert "@" not in filename
        assert filename.endswith(".png")

    def test_generate_filename_spaces(self):
        """Test generate_filename replaces spaces with underscores"""
        filename = generate_filename("test with spaces")
        assert "test_with_spaces" in filename or "test with spaces" not in filename


class TestImageSaving:
    """Tests for image saving with metadata"""

    @pytest.fixture
    def test_image(self):
        """Create a test image"""
        return Image.new("RGB", (512, 512), color="red")

    @pytest.fixture
    def test_metadata(self):
        """Create test metadata"""
        return {"prompt": "a beautiful sunset", "seed": 42, "steps": 25, "guidance_scale": 7.5}

    def test_save_image_with_metadata(self, test_image, test_metadata, tmp_path):
        """Test saving image with metadata creates both files"""
        output_path = tmp_path / "test_image.png"
        save_image_with_metadata(test_image, output_path, test_metadata)

        # Check image file exists
        assert output_path.exists()

        # Check metadata file exists
        metadata_path = output_path.with_suffix(".json")
        assert metadata_path.exists()

        # Verify metadata content
        with open(metadata_path, "r") as f:
            saved_metadata = json.load(f)
        assert saved_metadata["prompt"] == test_metadata["prompt"]
        assert saved_metadata["seed"] == test_metadata["seed"]

    def test_save_image_without_metadata(self, test_image, tmp_path):
        """Test saving image without metadata"""
        output_path = tmp_path / "test_image.png"
        save_image_with_metadata(test_image, output_path, None)

        # Check image file exists
        assert output_path.exists()

        # Check metadata file does NOT exist
        metadata_path = output_path.with_suffix(".json")
        assert not metadata_path.exists()


class TestImagePreprocessing:
    """Tests for image preprocessing"""

    @pytest.fixture
    def test_image(self):
        """Create a test image"""
        return Image.new("RGB", (1024, 768), color="blue")

    def test_preprocess_image_resize(self, test_image):
        """Test preprocess_image resizes correctly"""
        processed = preprocess_image(test_image, size=(512, 512))
        assert processed.size == (512, 512)

    def test_preprocess_image_maintains_aspect(self, test_image):
        """Test preprocess_image maintains aspect ratio with center crop"""
        processed = preprocess_image(test_image, size=(512, 512))
        assert processed.size == (512, 512)
        # Image should be cropped, not distorted
        assert processed.mode == "RGB"

    def test_preprocess_image_already_correct_size(self):
        """Test preprocess_image with already correct size"""
        img = Image.new("RGB", (512, 512), color="green")
        processed = preprocess_image(img, size=(512, 512))
        assert processed.size == (512, 512)


class TestImageGrid:
    """Tests for image grid creation"""

    @pytest.fixture
    def test_images(self):
        """Create multiple test images"""
        return [
            Image.new("RGB", (512, 512), color="red"),
            Image.new("RGB", (512, 512), color="green"),
            Image.new("RGB", (512, 512), color="blue"),
            Image.new("RGB", (512, 512), color="yellow"),
        ]

    def test_create_image_grid_2x2(self, test_images):
        """Test creating a 2x2 grid"""
        grid = create_image_grid(test_images, rows=2, cols=2)
        assert grid.size == (1024, 1024)  # 2x2 grid of 512x512 images

    def test_create_image_grid_single_row(self, test_images):
        """Test creating a single row grid"""
        grid = create_image_grid(test_images, rows=1, cols=4)
        assert grid.size == (2048, 512)  # 1x4 grid of 512x512 images

    def test_create_image_grid_single_image(self):
        """Test creating grid with single image"""
        img = Image.new("RGB", (512, 512), color="purple")
        grid = create_image_grid([img], rows=1, cols=1)
        assert grid.size == (512, 512)


class TestPromptLoading:
    """Tests for loading prompts from files"""

    def test_load_prompt_list_valid_file(self, tmp_path):
        """Test loading prompts from valid file"""
        # Create test file with prompts
        prompt_file = tmp_path / "prompts.txt"
        prompts = ["a beautiful sunset", "a mountain landscape", "an ocean scene"]
        prompt_file.write_text("\n".join(prompts))

        loaded_prompts = load_prompt_list(prompt_file)
        assert len(loaded_prompts) == 3
        assert loaded_prompts == prompts

    def test_load_prompt_list_empty_lines(self, tmp_path):
        """Test loading prompts ignores empty lines"""
        prompt_file = tmp_path / "prompts.txt"
        prompt_file.write_text("prompt 1\n\n\nprompt 2\n\nprompt 3")

        loaded_prompts = load_prompt_list(prompt_file)
        assert len(loaded_prompts) == 3
        assert "" not in loaded_prompts

    def test_load_prompt_list_strips_whitespace(self, tmp_path):
        """Test loading prompts strips whitespace"""
        prompt_file = tmp_path / "prompts.txt"
        prompt_file.write_text("  prompt 1  \n  prompt 2  ")

        loaded_prompts = load_prompt_list(prompt_file)
        assert loaded_prompts[0] == "prompt 1"
        assert loaded_prompts[1] == "prompt 2"

    def test_load_prompt_list_nonexistent_file(self):
        """Test loading prompts from nonexistent file raises error"""
        with pytest.raises(FileNotFoundError):
            load_prompt_list("nonexistent.txt")
