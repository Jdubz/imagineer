"""
Utility functions for image processing and model management.
"""

import torch
from PIL import Image
import numpy as np
from pathlib import Path
from typing import Union, List, Optional
import json
from datetime import datetime


def save_image_with_metadata(
    image: Image.Image,
    output_path: Union[str, Path],
    metadata: Optional[dict] = None
) -> None:
    """
    Save an image with optional metadata in JSON sidecar file.

    Args:
        image: PIL Image to save
        output_path: Path to save the image
        metadata: Optional dictionary with generation parameters
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save image
    image.save(output_path)

    # Save metadata if provided
    if metadata:
        metadata_path = output_path.with_suffix('.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)


def create_image_grid(images: List[Image.Image], rows: int, cols: int) -> Image.Image:
    """
    Create a grid of images.

    Args:
        images: List of PIL Images
        rows: Number of rows in grid
        cols: Number of columns in grid

    Returns:
        PIL Image containing the grid
    """
    if len(images) != rows * cols:
        raise ValueError(f"Number of images ({len(images)}) must match grid size ({rows}x{cols})")

    w, h = images[0].size
    grid = Image.new('RGB', size=(cols * w, rows * h))

    for i, img in enumerate(images):
        grid.paste(img, box=((i % cols) * w, (i // cols) * h))

    return grid


def get_device() -> str:
    """
    Automatically detect the best available device.

    Returns:
        Device string: "cuda", "mps", or "cpu"
    """
    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():
        return "mps"
    else:
        return "cpu"


def get_optimal_dtype(device: str) -> torch.dtype:
    """
    Get the optimal dtype for the given device.

    Args:
        device: Device string

    Returns:
        torch.dtype for model inference
    """
    if device == "cuda":
        return torch.float16
    else:
        return torch.float32


def preprocess_image(
    image: Union[str, Path, Image.Image],
    size: tuple = (512, 512),
    center_crop: bool = True
) -> Image.Image:
    """
    Preprocess an image for model input.

    Args:
        image: Path to image or PIL Image
        size: Target size (width, height)
        center_crop: Whether to center crop the image

    Returns:
        Preprocessed PIL Image
    """
    if isinstance(image, (str, Path)):
        image = Image.open(image)

    image = image.convert('RGB')

    # Resize while maintaining aspect ratio
    if center_crop:
        # Calculate crop box for center crop
        w, h = image.size
        aspect = size[0] / size[1]
        if w / h > aspect:
            new_w = int(h * aspect)
            left = (w - new_w) // 2
            image = image.crop((left, 0, left + new_w, h))
        else:
            new_h = int(w / aspect)
            top = (h - new_h) // 2
            image = image.crop((0, top, w, top + new_h))

    image = image.resize(size, Image.Resampling.LANCZOS)
    return image


def calculate_vram_usage() -> dict:
    """
    Calculate current VRAM usage (CUDA only).

    Returns:
        Dictionary with VRAM statistics
    """
    if not torch.cuda.is_available():
        return {"error": "CUDA not available"}

    allocated = torch.cuda.memory_allocated() / 1024**3
    reserved = torch.cuda.memory_reserved() / 1024**3
    total = torch.cuda.get_device_properties(0).total_memory / 1024**3

    return {
        "allocated_gb": round(allocated, 2),
        "reserved_gb": round(reserved, 2),
        "total_gb": round(total, 2),
        "free_gb": round(total - allocated, 2)
    }


def generate_filename(prompt: str, extension: str = "png") -> str:
    """
    Generate a filename from prompt and timestamp.

    Args:
        prompt: Text prompt
        extension: File extension

    Returns:
        Filename string
    """
    # Clean prompt for filename
    clean_prompt = "".join(c if c.isalnum() or c == " " else "" for c in prompt)
    clean_prompt = "_".join(clean_prompt.split()[:5])  # First 5 words

    # Add timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    return f"{timestamp}_{clean_prompt}.{extension}"


def load_prompt_list(file_path: Union[str, Path]) -> List[str]:
    """
    Load a list of prompts from a text file (one per line).

    Args:
        file_path: Path to text file

    Returns:
        List of prompts
    """
    with open(file_path, 'r') as f:
        prompts = [line.strip() for line in f if line.strip()]

    return prompts
