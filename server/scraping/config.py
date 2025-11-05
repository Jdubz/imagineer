"""Configuration management for web scraping in Imagineer."""

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class CrawlerConfig(BaseModel):
    """Web crawler configuration."""

    max_depth: int = Field(default=3, description="Maximum crawl depth")
    max_images: int = Field(default=1000, description="Maximum number of images to discover")
    user_agent: str = Field(
        default="Mozilla/5.0 (compatible; ImagineerBot/1.0)",
        description="User agent string",
    )
    respect_robots_txt: bool = Field(default=True, description="Respect robots.txt")
    timeout: int = Field(default=30, description="Request timeout in seconds")


class DownloaderConfig(BaseModel):
    """Image downloader configuration."""

    concurrent_downloads: int = Field(default=20, description="Number of concurrent downloads")
    max_retries: int = Field(default=3, description="Maximum number of retries")
    timeout: int = Field(default=30, description="Download timeout in seconds")
    user_agent: str = Field(
        default="Mozilla/5.0 (compatible; ImagineerBot/1.0)",
        description="User agent string",
    )


class ValidatorConfig(BaseModel):
    """Image validator configuration."""

    min_width: int = Field(default=100, description="Minimum image width in pixels")
    min_height: int = Field(default=100, description="Minimum image height in pixels")
    min_megapixels: float = Field(default=0.01, description="Minimum megapixels")
    max_aspect_ratio: float = Field(default=20.0, description="Maximum aspect ratio")
    allowed_formats: list[str] = Field(
        default_factory=lambda: ["jpg", "jpeg", "png", "webp", "bmp", "gif", "jfif"],
        description="Allowed image formats",
    )

    @field_validator("allowed_formats")
    @classmethod
    def lowercase_formats(cls, v: list[str]) -> list[str]:
        """Ensure formats are lowercase."""
        return [fmt.lower() for fmt in v]


class DeduplicatorConfig(BaseModel):
    """Image deduplicator configuration."""

    enabled: bool = Field(default=True, description="Enable duplicate detection")
    duplicate_threshold: int = Field(
        default=10, description="Perceptual hash hamming distance threshold for duplicates"
    )


class ScrapingConfig(BaseModel):
    """Main scraping configuration."""

    crawler: CrawlerConfig = Field(default_factory=CrawlerConfig)
    downloader: DownloaderConfig = Field(default_factory=DownloaderConfig)
    validator: ValidatorConfig = Field(default_factory=ValidatorConfig)
    deduplicator: DeduplicatorConfig = Field(default_factory=DeduplicatorConfig)

    # Output paths
    output_base_dir: Path = Field(
        default=Path("/mnt/storage/imagineer/scraped"),
        description="Base directory for scraped images",
    )

    # Captioning (optional, uses Claude CLI Docker)
    caption_on_scrape: bool = Field(
        default=False, description="Caption images during scraping (vs later)"
    )

    @classmethod
    def from_imagineer_config(cls, config_dict: dict[str, Any]) -> "ScrapingConfig":
        """
        Load scraping configuration from Imagineer's config.yaml structure.

        Expected structure in config.yaml:
        scraping:
          max_depth: 3
          max_images: 1000
          concurrent_downloads: 20
          timeout: 30
          min_width: 100
          min_height: 100
          duplicate_threshold: 10
          output_base_dir: /mnt/storage/imagineer/scraped
          caption_on_scrape: false
        """
        scraping_config = config_dict.get("scraping", {})

        # Map flat config to nested structure
        crawler_config = CrawlerConfig(
            max_depth=scraping_config.get("max_depth", 3),
            max_images=scraping_config.get("max_images", 1000),
            timeout=scraping_config.get("timeout", 30),
            user_agent=scraping_config.get(
                "user_agent", "Mozilla/5.0 (compatible; ImagineerBot/1.0)"
            ),
            respect_robots_txt=scraping_config.get("respect_robots_txt", True),
        )

        downloader_config = DownloaderConfig(
            concurrent_downloads=scraping_config.get("concurrent_downloads", 20),
            max_retries=scraping_config.get("max_retries", 3),
            timeout=scraping_config.get("timeout", 30),
            user_agent=scraping_config.get(
                "user_agent", "Mozilla/5.0 (compatible; ImagineerBot/1.0)"
            ),
        )

        validator_config = ValidatorConfig(
            min_width=scraping_config.get("min_width", 100),
            min_height=scraping_config.get("min_height", 100),
            min_megapixels=scraping_config.get("min_megapixels", 0.01),
            max_aspect_ratio=scraping_config.get("max_aspect_ratio", 20.0),
            allowed_formats=scraping_config.get(
                "allowed_formats", ["jpg", "jpeg", "png", "webp", "gif", "bmp"]
            ),
        )

        deduplicator_config = DeduplicatorConfig(
            enabled=scraping_config.get("remove_duplicates", True),
            duplicate_threshold=scraping_config.get("duplicate_threshold", 10),
        )

        # Get output base dir from outputs section or scraping section
        outputs_config = config_dict.get("outputs", {})
        output_base_dir = Path(
            scraping_config.get(
                "output_base_dir",
                outputs_config.get("scraped_dir", "/mnt/storage/imagineer/scraped"),
            )
        )

        caption_on_scrape = scraping_config.get("caption_on_scrape", False)

        return cls(
            crawler=crawler_config,
            downloader=downloader_config,
            validator=validator_config,
            deduplicator=deduplicator_config,
            output_base_dir=output_base_dir,
            caption_on_scrape=caption_on_scrape,
        )

    @classmethod
    def from_yaml_file(cls, yaml_path: Optional[Path] = None) -> "ScrapingConfig":
        """
        Load scraping configuration from Imagineer's config.yaml.

        Args:
            yaml_path: Path to config.yaml (defaults to project config.yaml)

        Returns:
            ScrapingConfig instance
        """
        if yaml_path is None:
            # Try to find config.yaml in project root
            config_env_path = os.environ.get("IMAGINEER_CONFIG_PATH")
            if config_env_path:
                yaml_path = Path(config_env_path)
            else:
                # Default to config.yaml in project root
                project_root = Path(__file__).parent.parent.parent
                yaml_path = project_root / "config.yaml"

                # Check for development config
                dev_config = project_root / "config.development.yaml"
                if os.environ.get("FLASK_ENV") == "development" and dev_config.exists():
                    yaml_path = dev_config

        if not yaml_path or not yaml_path.exists():
            # Return defaults if no config file found
            return cls()

        with open(yaml_path, "r") as f:
            config_dict = yaml.safe_load(f) or {}

        return cls.from_imagineer_config(config_dict)


def get_scraping_config(yaml_path: Optional[Path] = None) -> ScrapingConfig:
    """
    Get scraping configuration from Imagineer's config.yaml.

    This is the main entry point for loading scraping configuration.

    Args:
        yaml_path: Optional path to config.yaml (auto-detects if not provided)

    Returns:
        ScrapingConfig instance
    """
    return ScrapingConfig.from_yaml_file(yaml_path)
