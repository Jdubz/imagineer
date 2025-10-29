"""
Database models for Imagineer
SQLAlchemy models for image management, albums, and training data
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
logger = logging.getLogger(__name__)


def utcnow():
    """Timezone-aware UTC timestamp helper for SQLAlchemy defaults."""
    return datetime.now(timezone.utc)


class Image(db.Model):
    """Generated images with metadata"""

    __tablename__ = "images"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False, unique=True)
    file_path = db.Column(db.String(500), nullable=False)
    thumbnail_path = db.Column(db.String(500))

    # Generation metadata
    prompt = db.Column(db.Text)
    negative_prompt = db.Column(db.Text)
    seed = db.Column(db.Integer)
    steps = db.Column(db.Integer)
    guidance_scale = db.Column(db.Float)
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)

    # LoRA information (JSON string)
    lora_config = db.Column(db.Text)  # JSON: [{"path": "...", "weight": 0.6}]

    # Content metadata
    is_nsfw = db.Column(db.Boolean, default=False)
    is_public = db.Column(db.Boolean, default=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    labels = db.relationship("Label", backref="image", lazy=True, cascade="all, delete-orphan")
    album_images = db.relationship(
        "AlbumImage", backref="image", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def albums(self):
        """Get albums containing this image"""
        return [ai.album for ai in self.album_images if ai.album]

    def to_dict(self, include_sensitive: bool = False):
        """Convert to dictionary for API serialization."""
        storage_path = None
        if self.file_path:
            try:
                storage_path = str(Path(self.file_path).name)
            except ValueError:
                storage_path = None

        data = {
            "id": self.id,
            "filename": self.filename,
            "storage_name": storage_path,
            "download_url": f"/api/images/{self.id}/file",
            "thumbnail_url": f"/api/images/{self.id}/thumbnail",
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "seed": self.seed,
            "steps": self.steps,
            "guidance_scale": self.guidance_scale,
            "width": self.width,
            "height": self.height,
            "lora_config": self.lora_config,
            "is_nsfw": self.is_nsfw,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_sensitive:
            data["file_path"] = self.file_path
            data["thumbnail_path"] = self.thumbnail_path
        else:
            data["file_path"] = None
            data["thumbnail_path"] = None

        return data


class Label(db.Model):
    """AI-generated labels for images"""

    __tablename__ = "labels"

    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.Integer, db.ForeignKey("images.id"), nullable=False)

    # Label content
    label_text = db.Column(db.Text, nullable=False)
    confidence = db.Column(db.Float)  # 0.0 to 1.0
    label_type = db.Column(db.String(50), default="ai_generated")  # ai_generated, manual, user

    # Source information
    source_model = db.Column(db.String(100))  # e.g., "claude-3-sonnet"
    source_prompt = db.Column(db.Text)  # The prompt used to generate the label
    created_by = db.Column(db.String(255), nullable=True)  # User who created the label

    # Timestamps
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "image_id": self.image_id,
            "label_text": self.label_text,
            "confidence": self.confidence,
            "label_type": self.label_type,
            "source_model": self.source_model,
            "source_prompt": self.source_prompt,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Album(db.Model):
    """Collections of images (batches, sets, etc.)"""

    __tablename__ = "albums"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)

    # Album metadata
    album_type = db.Column(db.String(50), default="batch")  # batch, set, collection, manual
    is_public = db.Column(db.Boolean, default=True)
    is_training_source = db.Column(db.Boolean, default=False)  # Can be used for training
    created_by = db.Column(db.String(255), nullable=True)  # User who created the album

    # Generation context (for batch albums)
    generation_prompt = db.Column(db.Text)
    generation_config = db.Column(db.Text)  # JSON: generation settings

    # Timestamps
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    album_images = db.relationship(
        "AlbumImage", backref="album", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def images(self):
        """Get images in this album"""
        return [ai.image for ai in self.album_images if ai.image]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "album_type": self.album_type,
            "is_public": self.is_public,
            "is_training_source": self.is_training_source,
            "generation_prompt": self.generation_prompt,
            "generation_config": self.generation_config,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "image_count": len(self.album_images) if self.album_images else 0,
        }


class AlbumImage(db.Model):
    """Many-to-many relationship between albums and images"""

    __tablename__ = "album_images"

    id = db.Column(db.Integer, primary_key=True)
    album_id = db.Column(db.Integer, db.ForeignKey("albums.id"), nullable=False)
    image_id = db.Column(db.Integer, db.ForeignKey("images.id"), nullable=False)

    # Ordering within album
    sort_order = db.Column(db.Integer, default=0)
    added_by = db.Column(db.String(255), nullable=True)  # User who added the image to the album

    # Timestamps
    created_at = db.Column(db.DateTime, default=utcnow)

    # Unique constraint
    __table_args__ = (db.UniqueConstraint("album_id", "image_id", name="unique_album_image"),)

    def to_dict(self):
        return {
            "id": self.id,
            "album_id": self.album_id,
            "image_id": self.image_id,
            "sort_order": self.sort_order,
            "added_by": self.added_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ScrapeJob(db.Model):
    """Web scraping jobs for training data collection"""

    __tablename__ = "scrape_jobs"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)

    # Scraping configuration
    source_url = db.Column(db.String(500))
    scrape_config = db.Column(db.Text)  # JSON: scraping parameters

    # Job status
    status = db.Column(db.String(50), default="pending")  # pending, running, completed, failed
    progress = db.Column(db.Integer, default=0)  # 0-100

    # Results
    images_scraped = db.Column(db.Integer, default=0)
    output_directory = db.Column(db.String(500))

    # Error handling
    error_message = db.Column(db.Text)
    last_error_at = db.Column(db.DateTime)

    # Timestamps
    created_at = db.Column(db.DateTime, default=utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    def to_dict(self, include_sensitive: bool = False):
        config_data = {}
        runtime_data = {}
        if self.scrape_config:
            try:
                loaded = json.loads(self.scrape_config)
                config_data = loaded if isinstance(loaded, dict) else {}
                runtime_candidate = config_data.get("runtime", {})
                runtime_data = runtime_candidate if isinstance(runtime_candidate, dict) else {}
            except (ValueError, TypeError):
                config_data = {}
                runtime_data = {}

        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "source_url": self.source_url,
            "url": self.source_url,
            "scrape_config": self.scrape_config,
            "config": config_data,
            "runtime": runtime_data,
            "status": self.status,
            "progress": self.progress,
            "progress_message": self.description,
            "images_scraped": self.images_scraped,
            "error_message": self.error_message,
            "last_error_at": self.last_error_at.isoformat() if self.last_error_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

        if include_sensitive:
            data["output_directory"] = self.output_directory
            data["output_dir"] = self.output_directory
        else:
            data["output_directory"] = None
            data["output_dir"] = None

        return data


class TrainingRun(db.Model):
    """LoRA training runs"""

    __tablename__ = "training_runs"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)

    # Training configuration
    dataset_path = db.Column(db.String(500), nullable=False)
    output_path = db.Column(db.String(500), nullable=False)
    training_config = db.Column(db.Text)  # JSON: training parameters

    # Training status
    status = db.Column(db.String(50), default="pending")  # pending, running, completed, failed
    progress = db.Column(db.Integer, default=0)  # 0-100

    # Results
    final_checkpoint = db.Column(db.String(500))
    training_loss = db.Column(db.Float)
    validation_loss = db.Column(db.Float)

    # Error handling
    error_message = db.Column(db.Text)
    last_error_at = db.Column(db.DateTime)

    # Timestamps
    created_at = db.Column(db.DateTime, default=utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    def to_dict(self, include_sensitive: bool = False):
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "training_config": self.training_config,
            "status": self.status,
            "progress": self.progress,
            "final_checkpoint": self.final_checkpoint,
            "training_loss": self.training_loss,
            "validation_loss": self.validation_loss,
            "error_message": self.error_message,
            "last_error_at": self.last_error_at.isoformat() if self.last_error_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

        if include_sensitive:
            data["dataset_path"] = self.dataset_path
            data["output_path"] = self.output_path
        else:
            data["dataset_path"] = None
            data["output_path"] = None

        return data


class MigrationHistory(db.Model):
    """Record of one-off migration or import scripts that have been executed."""

    __tablename__ = "migration_history"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    applied_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    last_run_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    details = db.Column(db.Text)

    @classmethod
    def has_run(cls, name: str) -> bool:
        """Return True when a migration with the supplied name has been recorded."""
        return cls.query.filter_by(name=name).first() is not None

    @classmethod
    def ensure_record(
        cls,
        name: str,
        *,
        details: str | None = None,
        refresh_timestamp: bool = False,
    ) -> "MigrationHistory":
        """
        Retrieve or create the execution record for a named migration.

        Args:
            name: Stable identifier for the migration/import script.
            details: Optional JSON/text payload describing the run outcome.
            refresh_timestamp: When True, update ``last_run_at`` to the current time
                so repeated executions are visible.
        """
        entry = cls.query.filter_by(name=name).first()
        if entry:
            if refresh_timestamp:
                entry.last_run_at = utcnow()
            if details is not None and entry.details != details:
                entry.details = details
            return entry

        entry = cls(name=name, details=details)
        db.session.add(entry)
        return entry

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "details": self.details,
        }


def init_database(app):
    """Initialize database with Flask app"""
    db.init_app(app)

    with app.app_context():
        # Ensure instance directory exists for SQLite databases
        db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        if db_uri.startswith("sqlite:///"):
            db_path = db_uri.replace("sqlite:///", "")
            db_file = Path(db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured database directory exists: {db_file.parent}")

        # Create all tables
        db.create_all()
        logger.info("Database tables created successfully")

    return db
