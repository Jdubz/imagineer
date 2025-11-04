"""
Database models for Imagineer
SQLAlchemy models for image management, albums, and training data
"""

import json
import logging
import re
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

    # Set template metadata
    is_set_template = db.Column(db.Boolean, default=False)
    csv_data = db.Column(db.Text)  # JSON string containing template rows
    base_prompt = db.Column(db.Text)
    prompt_template = db.Column(db.Text)
    style_suffix = db.Column(db.Text)
    example_theme = db.Column(db.Text)
    lora_config = db.Column(db.Text)  # JSON array of LoRA configs

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
        try:
            template_items = json.loads(self.csv_data) if self.csv_data else []
        except json.JSONDecodeError:
            template_items = []

        try:
            lora_payload = json.loads(self.lora_config) if self.lora_config else []
        except json.JSONDecodeError:
            lora_payload = []

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
            "is_set_template": self.is_set_template,
            "csv_data": self.csv_data,
            "base_prompt": self.base_prompt,
            "prompt_template": self.prompt_template,
            "style_suffix": self.style_suffix,
            "example_theme": self.example_theme,
            "lora_config": self.lora_config,
            "template_item_count": len(template_items),
            "template_items_preview": template_items[:5] if template_items else [],
            "lora_count": len(lora_payload),
            "slug": self.slug,
        }

    @property
    def slug(self) -> str:
        """Stable identifier derived from generation config or album name."""

        def _sanitize(value: str) -> str:
            candidate = value.lower()
            candidate = re.sub(r"[^a-z0-9]+", "-", candidate).strip("-")
            return candidate or f"album-{self.id}"

        payload = None
        if self.generation_config:
            try:
                maybe_dict = json.loads(self.generation_config)
                if isinstance(maybe_dict, dict):
                    payload = maybe_dict
            except (TypeError, json.JSONDecodeError):
                payload = None

        if isinstance(payload, dict):
            for key in ("slug", "legacy_slug"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return _sanitize(value)

        if self.name:
            return _sanitize(self.name)

        return f"album-{self.id}"


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
    album_id = db.Column(db.Integer, db.ForeignKey("albums.id"), nullable=True)

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
            "album_id": self.album_id,
            "error_message": self.error_message,
            "error": self.error_message,  # Frontend expects 'error' field
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


class BugReport(db.Model):
    """Bug reports with automated remediation support"""

    __tablename__ = "bug_reports"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(100), nullable=False, unique=True, index=True)

    # Core fields
    title = db.Column(db.String(500))
    description = db.Column(db.Text, nullable=False)
    expected_behavior = db.Column(db.Text)
    actual_behavior = db.Column(db.Text)
    steps_to_reproduce = db.Column(db.Text)  # JSON array

    # Classification
    severity = db.Column(db.String(50))  # low, medium, high, critical
    category = db.Column(db.String(100))  # ui, api, performance, security, etc.
    status = db.Column(
        db.String(50), nullable=False, default="new", index=True
    )  # new, triaged, in_progress, awaiting_verification, resolved, closed

    # Source tracking
    source = db.Column(db.String(50), default="user")  # user, agent, system
    reporter_id = db.Column(db.String(255))  # email or user identifier
    assignee_id = db.Column(db.String(255))

    # Telemetry integration
    trace_id = db.Column(db.String(100), index=True)
    request_id = db.Column(db.String(100))
    release_sha = db.Column(db.String(100))

    # Build metadata
    app_version = db.Column(db.String(50))
    git_sha = db.Column(db.String(100))
    build_time = db.Column(db.DateTime)

    # Context metadata (JSON fields)
    suspected_components = db.Column(db.Text)  # JSON array
    related_files = db.Column(db.Text)  # JSON array
    navigation_history = db.Column(db.Text)  # JSON array

    # Full context data (from existing JSON reports)
    environment = db.Column(db.Text)  # JSON object
    client_meta = db.Column(db.Text)  # JSON object
    app_state = db.Column(db.Text)  # JSON object
    recent_logs = db.Column(db.Text)  # JSON array
    network_events = db.Column(db.Text)  # JSON array

    # Screenshot
    screenshot_path = db.Column(db.String(500))
    screenshot_error = db.Column(db.Text)

    # Resolution tracking
    resolution_notes = db.Column(db.Text)
    resolution_commit_sha = db.Column(db.String(100))

    # Deduplication
    duplicate_of_id = db.Column(db.Integer, db.ForeignKey("bug_reports.id"))
    dedup_hash = db.Column(db.String(64), index=True)  # Hash for grouping

    # Automation flags
    automation_enabled = db.Column(db.Boolean, default=True)
    automation_attempts = db.Column(db.Integer, default=0)
    last_automation_at = db.Column(db.DateTime)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    resolved_at = db.Column(db.DateTime)
    sla_due_at = db.Column(db.DateTime)

    # Relationships
    events = db.relationship(
        "BugReportEvent",
        backref="bug_report",
        lazy=True,
        cascade="all, delete-orphan",
    )
    duplicates = db.relationship(
        "BugReport",
        backref=db.backref("canonical_report", remote_side=[id]),
        foreign_keys=[duplicate_of_id],
    )

    def to_dict(self, include_context=False):
        """Convert to dictionary for API serialization."""
        data = {
            "id": self.id,
            "report_id": self.report_id,
            "title": self.title,
            "description": self.description,
            "expected_behavior": self.expected_behavior,
            "actual_behavior": self.actual_behavior,
            "severity": self.severity,
            "category": self.category,
            "status": self.status,
            "source": self.source,
            "reporter_id": self.reporter_id,
            "assignee_id": self.assignee_id,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "release_sha": self.release_sha,
            "app_version": self.app_version,
            "git_sha": self.git_sha,
            "build_time": self.build_time.isoformat() if self.build_time else None,
            "screenshot_path": self.screenshot_path,
            "screenshot_error": self.screenshot_error,
            "resolution_notes": self.resolution_notes,
            "resolution_commit_sha": self.resolution_commit_sha,
            "duplicate_of_id": self.duplicate_of_id,
            "dedup_hash": self.dedup_hash,
            "automation_enabled": self.automation_enabled,
            "automation_attempts": self.automation_attempts,
            "last_automation_at": (
                self.last_automation_at.isoformat() if self.last_automation_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "sla_due_at": self.sla_due_at.isoformat() if self.sla_due_at else None,
        }

        # Parse JSON fields
        for field in [
            "steps_to_reproduce",
            "suspected_components",
            "related_files",
            "navigation_history",
        ]:
            value = getattr(self, field)
            try:
                data[field] = json.loads(value) if value else None
            except (json.JSONDecodeError, TypeError):
                data[field] = None

        # Include full context if requested
        if include_context:
            for field in [
                "environment",
                "client_meta",
                "app_state",
                "recent_logs",
                "network_events",
            ]:
                value = getattr(self, field)
                try:
                    data[field] = json.loads(value) if value else None
                except (json.JSONDecodeError, TypeError):
                    data[field] = None

        return data


class BugReportEvent(db.Model):
    """Lifecycle events and agent actions for bug reports"""

    __tablename__ = "bug_report_events"

    id = db.Column(db.Integer, primary_key=True)
    bug_report_id = db.Column(
        db.Integer,
        db.ForeignKey("bug_reports.id"),
        nullable=False,
        index=True,
    )

    # Event type
    event_type = db.Column(
        db.String(50),
        nullable=False,
    )  # status_change, note, agent_run, assignment, etc.
    event_data = db.Column(db.Text)  # JSON payload with event-specific data

    # Tracking
    actor_id = db.Column(db.String(255))  # User or agent who triggered the event
    actor_type = db.Column(db.String(50))  # user, agent, system

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    def to_dict(self):
        """Convert to dictionary for API serialization."""
        try:
            event_data_parsed = json.loads(self.event_data) if self.event_data else None
        except (json.JSONDecodeError, TypeError):
            event_data_parsed = None

        return {
            "id": self.id,
            "bug_report_id": self.bug_report_id,
            "event_type": self.event_type,
            "event_data": event_data_parsed,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class BugReportDedup(db.Model):
    """Deduplication keys and occurrence counts for bug reports"""

    __tablename__ = "bug_report_dedup"

    id = db.Column(db.Integer, primary_key=True)

    # Deduplication key (hash of normalized error signature)
    dedup_key = db.Column(db.String(100), nullable=False, unique=True, index=True)

    # Canonical report for this dedup group
    canonical_report_id = db.Column(db.Integer, db.ForeignKey("bug_reports.id"), nullable=False)

    # Statistics
    occurrence_count = db.Column(db.Integer, default=1, nullable=False)
    first_seen_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    last_seen_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    # Metadata
    stack_trace_hash = db.Column(db.String(64))
    component_hash = db.Column(db.String(64))
    message_hash = db.Column(db.String(64))

    def to_dict(self):
        """Convert to dictionary for API serialization."""
        return {
            "id": self.id,
            "dedup_key": self.dedup_key,
            "canonical_report_id": self.canonical_report_id,
            "occurrence_count": self.occurrence_count,
            "first_seen_at": self.first_seen_at.isoformat() if self.first_seen_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "stack_trace_hash": self.stack_trace_hash,
            "component_hash": self.component_hash,
            "message_hash": self.message_hash,
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
