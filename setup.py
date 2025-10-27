"""
Setup configuration for Imagineer package.
"""

from pathlib import Path

from setuptools import find_packages, setup

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="imagineer",
    version="0.1.0",
    author="Jdubz",
    description="AI Image Generation Toolkit built on Stable Diffusion",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Jdubz/imagineer",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        "torch>=2.0.0",
        "torchvision>=0.15.0",
        "diffusers>=0.27.0",
        "transformers>=4.35.0",
        "accelerate>=0.25.0",
        "safetensors>=0.4.0",
        "omegaconf>=2.3.0",
        "Pillow>=10.0.0",
        "numpy>=1.24.0",
        "scipy>=1.11.0",
        "huggingface-hub>=0.20.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "isort>=5.12.0",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
