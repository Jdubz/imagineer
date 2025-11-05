#!/usr/bin/env python3
"""
Migration: Separate Batch Templates from Albums

This migration implements the architectural change to separate batch templates
(instructions for generating images) from albums (collections of generated images).

Changes:
1. Create batch_templates table
2. Create batch_generation_runs table
3. Add source_type and source_id to albums table
4. Delete empty template albums
5. Seed batch templates from config.yaml
6. Mark existing albums as source_type='manual'

Run: python scripts/migrate_template_album_separation.py
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import yaml  # noqa: E402

from server.config_loader import load_config  # noqa: E402
from server.database import Album, db  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def utcnow():
    """Timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def run_migration(app):
    """Execute the migration."""
    with app.app_context():
        logger.info("=" * 80)
        logger.info("STARTING MIGRATION: Template-Album Separation")
        logger.info("=" * 80)

        # Step 1: Create new tables
        logger.info("\n[Step 1] Creating new tables...")
        create_new_tables()

        # Step 2: Add new columns to albums
        logger.info("\n[Step 2] Adding source tracking columns to albums...")
        add_album_source_columns()

        # Step 3: Delete template albums (they're empty)
        logger.info("\n[Step 3] Deleting empty template albums...")
        delete_template_albums()

        # Step 4: Seed batch templates from config
        logger.info("\n[Step 4] Seeding batch templates from config.yaml...")
        seed_batch_templates()

        # Step 5: Mark existing albums as manual
        logger.info("\n[Step 5] Marking existing albums as source_type='manual'...")
        mark_existing_albums_as_manual()

        # Step 6: Import orphaned batch generation images
        logger.info("\n[Step 6] Importing orphaned batch generation images...")
        import_orphaned_batch_images()

        # Step 7: Import orphaned scrape images
        logger.info("\n[Step 7] Importing orphaned scrape images...")
        import_orphaned_scrape_images()

        # Step 8: Import orphaned single-generation images
        logger.info("\n[Step 8] Importing orphaned single-generation images...")
        import_orphaned_single_images()

        # Step 9: Add album_name column to scrape_jobs
        logger.info("\n[Step 9] Adding album_name to scrape_jobs...")
        add_scrape_job_album_name()

        logger.info("\n" + "=" * 80)
        logger.info("MIGRATION COMPLETE!")
        logger.info("=" * 80)
        logger.info("\nSummary:")
        with db.engine.connect() as conn:
            summary = conn.execute(
                text(
                    """
                SELECT
                    source_type,
                    COUNT(*) as count
                FROM albums
                GROUP BY source_type
            """
                )
            ).fetchall()
            for source_type, count in summary:
                logger.info(f"  - {source_type}: {count} albums")

            total_images = conn.execute(text("SELECT COUNT(*) FROM images")).fetchone()[0]
            linked_images = conn.execute(
                text("SELECT COUNT(DISTINCT image_id) FROM album_images")
            ).fetchone()[0]
            orphaned = total_images - linked_images
            logger.info(f"  - Total images: {total_images}")
            logger.info(f"  - Linked to albums: {linked_images}")
            logger.info(f"  - Orphaned: {orphaned}")

        logger.info("\nNext steps:")
        logger.info("1. Review the changes in the database")
        logger.info("2. Test batch template endpoints")
        logger.info("3. Deploy frontend changes")
        logger.info("4. Update documentation")


def create_new_tables():
    """Create batch_templates and batch_generation_runs tables."""

    # Check if tables already exist
    inspector = db.inspect(db.engine)
    existing_tables = inspector.get_table_names()

    if "batch_templates" in existing_tables:
        logger.warning("⚠️  batch_templates table already exists, skipping creation")
    else:
        with db.engine.connect() as conn:
            conn.execute(
                text(
                    """
                CREATE TABLE batch_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,

                    csv_path VARCHAR(500) NOT NULL,
                    csv_data TEXT,
                    base_prompt TEXT,
                    prompt_template TEXT NOT NULL,
                    style_suffix TEXT,
                    example_theme TEXT,

                    width INTEGER DEFAULT 512,
                    height INTEGER DEFAULT 512,
                    negative_prompt TEXT,
                    lora_config TEXT,

                    created_by VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
                )
            )
            conn.commit()
        logger.info("✅ Created batch_templates table")

    if "batch_generation_runs" in existing_tables:
        logger.warning("⚠️  batch_generation_runs table already exists, skipping creation")
    else:
        with db.engine.connect() as conn:
            conn.execute(
                text(
                    """
                CREATE TABLE batch_generation_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    template_id INTEGER NOT NULL,
                    album_id INTEGER,

                    album_name VARCHAR(255) NOT NULL,
                    user_theme TEXT NOT NULL,

                    steps INTEGER,
                    seed INTEGER,
                    width INTEGER,
                    height INTEGER,
                    guidance_scale FLOAT,
                    negative_prompt TEXT,

                    status VARCHAR(50) DEFAULT 'queued',
                    total_items INTEGER,
                    completed_items INTEGER DEFAULT 0,
                    failed_items INTEGER DEFAULT 0,

                    created_by VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,

                    error_message TEXT,

                    FOREIGN KEY (template_id) REFERENCES batch_templates(id),
                    FOREIGN KEY (album_id) REFERENCES albums(id)
                )
            """
                )
            )
            conn.commit()
        logger.info("✅ Created batch_generation_runs table")


def add_album_source_columns():
    """Add source_type and source_id columns to albums table."""

    inspector = db.inspect(db.engine)
    columns = [col["name"] for col in inspector.get_columns("albums")]

    if "source_type" not in columns:
        with db.engine.connect() as conn:
            conn.execute(
                text(
                    """
                ALTER TABLE albums ADD COLUMN source_type VARCHAR(50) DEFAULT 'manual'
            """
                )
            )
            conn.commit()
        logger.info("✅ Added source_type column to albums")
    else:
        logger.warning("⚠️  source_type column already exists")

    if "source_id" not in columns:
        with db.engine.connect() as conn:
            conn.execute(
                text(
                    """
                ALTER TABLE albums ADD COLUMN source_id INTEGER
            """
                )
            )
            conn.commit()
        logger.info("✅ Added source_id column to albums")
    else:
        logger.warning("⚠️  source_id column already exists")


def delete_template_albums():
    """Delete albums where is_set_template = True (they should be empty)."""

    template_albums = Album.query.filter_by(is_set_template=True).all()

    if not template_albums:
        logger.info("ℹ️  No template albums found to delete")
        return

    logger.info(f"Found {len(template_albums)} template albums:")

    for album in template_albums:
        image_count = len(album.album_images)
        logger.info(f"  - {album.name} (ID: {album.id}, Images: {image_count})")

        if image_count > 0:
            logger.error(f"❌ Template album '{album.name}' has {image_count} images!")
            logger.error("   This should not happen. Aborting migration.")
            raise Exception(f"Template album {album.id} has images, cannot delete safely")

    # All template albums are empty, safe to delete
    for album in template_albums:
        db.session.delete(album)
        logger.info(f"🗑️  Deleted template album: {album.name}")

    db.session.commit()
    logger.info(f"✅ Deleted {len(template_albums)} empty template albums")


def seed_batch_templates():
    """Create batch template records from config.yaml."""

    # Load the sets config
    config = load_config()
    sets_config_path = Path(config["output"]["directory"]).parent / "sets" / "config.yaml"

    if not sets_config_path.exists():
        logger.error(f"❌ Sets config not found: {sets_config_path}")
        return

    with open(sets_config_path, "r") as f:
        sets_config = yaml.safe_load(f)

    logger.info(f"Found {len(sets_config)} template definitions in config.yaml")

    # Check if we've already seeded
    with db.engine.connect() as conn:
        existing_count = conn.execute(text("SELECT COUNT(*) FROM batch_templates")).fetchone()[0]
    if existing_count > 0:
        logger.warning(f"⚠️  Found {existing_count} existing batch templates, skipping seed")
        return

    for template_key, template_data in sets_config.items():
        # Prepare CSV path - check both config path and fallback locations
        csv_filename = template_data.get("csv_path", f"data/sets/{template_key}.csv")

        # Try multiple locations
        csv_path = None
        search_paths = [
            PROJECT_ROOT / csv_filename,  # Relative to project root
            Path(csv_filename),  # Absolute path from config
            Path(config["output"]["directory"]).parent
            / "sets"
            / f"{template_key}.csv",  # External sets dir
        ]

        for path in search_paths:
            if path.exists():
                csv_path = path
                csv_filename = (
                    str(path.relative_to(PROJECT_ROOT))
                    if path.is_relative_to(PROJECT_ROOT)
                    else str(path)
                )
                break

        # Load CSV data for caching
        csv_data_json = None
        if csv_path and csv_path.exists():
            import csv

            with open(csv_path, "r") as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)
                csv_data_json = json.dumps(rows)
                logger.info(f"  Loaded {len(rows)} rows from {csv_path}")
        else:
            logger.warning(
                f"  ⚠️  CSV file not found for template '{template_key}'. Searched: {search_paths}"
            )
            csv_filename = template_data.get(
                "csv_path", f"data/sets/{template_key}.csv"
            )  # Use config value as fallback

        # Prepare LoRA config
        loras = template_data.get("loras", [])
        lora_config_json = json.dumps(loras) if loras else None

        # Insert template
        with db.engine.connect() as conn:
            conn.execute(
                text(
                    """
                INSERT INTO batch_templates (
                    name, description, csv_path, csv_data,
                    base_prompt, prompt_template, style_suffix, example_theme,
                    width, height, negative_prompt, lora_config,
                    created_at, updated_at
                ) VALUES (:name, :description, :csv_path, :csv_data,
                         :base_prompt, :prompt_template, :style_suffix, :example_theme,
                         :width, :height, :negative_prompt, :lora_config,
                         :created_at, :updated_at)
            """
                ),
                {
                    "name": template_data.get("name", template_key),
                    "description": template_data.get("description", ""),
                    "csv_path": csv_filename,
                    "csv_data": csv_data_json,
                    "base_prompt": template_data.get("base_prompt", ""),
                    "prompt_template": template_data.get("prompt_template", ""),
                    "style_suffix": template_data.get("style_suffix", ""),
                    "example_theme": template_data.get("example_theme", ""),
                    "width": template_data.get("width", 512),
                    "height": template_data.get("height", 512),
                    "negative_prompt": template_data.get("negative_prompt", ""),
                    "lora_config": lora_config_json,
                    "created_at": utcnow(),
                    "updated_at": utcnow(),
                },
            )
            conn.commit()

        logger.info(f"✅ Created batch template: {template_data.get('name', template_key)}")

    db.session.commit()
    logger.info(f"✅ Seeded {len(sets_config)} batch templates")


def mark_existing_albums_as_manual():
    """Set source_type='manual' for all existing albums."""

    with db.engine.connect() as conn:
        result = conn.execute(
            text(
                """
            UPDATE albums
            SET source_type = 'manual'
            WHERE source_type IS NULL OR source_type = ''
        """
            )
        )
        count = result.rowcount
        conn.commit()

    logger.info(f"✅ Marked {count} albums as source_type='manual'")


def import_orphaned_batch_images():
    """Import images from orphaned batch generation directories."""
    import re

    from server.database import AlbumImage, Image

    config = load_config()
    outputs_dir = Path(config["output"]["directory"])

    # Pattern for batch directories: {template_name}_{timestamp}
    batch_dir_pattern = re.compile(r"^[a-z_]+_\d{8}_\d{6}$")

    imported_albums = 0
    imported_images = 0

    for item in outputs_dir.iterdir():
        if not item.is_dir():
            continue

        # Skip known non-batch directories
        if item.name in ["albums", "lora_tests", "scraped", "thumbnails", "uploads"]:
            continue

        # Check if matches batch directory pattern
        if not batch_dir_pattern.match(item.name):
            logger.info(f"  ⏭️  Skipping non-batch directory: {item.name}")
            continue

        # Find PNG files
        png_files = list(item.glob("*.png"))
        if not png_files:
            logger.info(f"  ⏭️  Skipping empty directory: {item.name}")
            continue

        logger.info(f"  📁 Processing batch directory: {item.name} ({len(png_files)} images)")

        # Parse directory name
        parts = item.name.split("_")
        # Format: template_name_YYYYMMDD_HHMMSS
        template_name = "_".join(parts[:-2])
        timestamp = f"{parts[-2]}_{parts[-1]}"

        # Create album name
        album_name = f"{template_name.replace('_', ' ').title()} - {timestamp}"

        # Check if album already exists for this directory
        existing = Album.query.filter_by(name=album_name).first()
        if existing:
            logger.info(f"    ℹ️  Album already exists: {album_name}")
            album = existing
        else:
            # Create album
            album = Album(
                name=album_name,
                description=f"Batch generation from {template_name} template",
                source_type="batch_generation",
                is_public=True,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.session.add(album)
            db.session.flush()  # Get album ID
            imported_albums += 1
            logger.info(f"    ✅ Created album: {album_name}")

        # Import images with incremental sort order
        sort_order = 0
        for png_file in png_files:
            # Check if image already in database
            existing_image = Image.query.filter_by(file_path=str(png_file)).first()

            if existing_image:
                # Check if already linked to this album
                link = AlbumImage.query.filter_by(
                    album_id=album.id, image_id=existing_image.id
                ).first()

                if not link:
                    # Link existing image to album
                    assoc = AlbumImage(
                        album_id=album.id, image_id=existing_image.id, sort_order=sort_order
                    )
                    db.session.add(assoc)
                    sort_order += 1
                    logger.info(f"      🔗 Linked existing image: {png_file.name}")
                continue

            # Load metadata from JSON sidecar
            json_file = png_file.with_suffix(".json")
            metadata = {}
            if json_file.exists():
                with open(json_file, "r") as f:
                    metadata = json.load(f)

            # Create image record
            image = Image(
                filename=png_file.name,
                file_path=str(png_file),
                thumbnail_path=None,  # Will be generated later if needed
                prompt=metadata.get("prompt"),
                negative_prompt=metadata.get("negative_prompt"),
                seed=metadata.get("seed"),
                steps=metadata.get("steps"),
                guidance_scale=metadata.get("guidance_scale"),
                width=metadata.get("width"),
                height=metadata.get("height"),
                lora_config=(
                    json.dumps(metadata.get("loras", [])) if metadata.get("loras") else None
                ),
                is_nsfw=False,
                is_public=True,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.session.add(image)
            db.session.flush()  # Get image ID

            # Link to album with incremental sort order
            assoc = AlbumImage(album_id=album.id, image_id=image.id, sort_order=sort_order)
            db.session.add(assoc)
            sort_order += 1
            imported_images += 1
            logger.info(f"      ✅ Imported: {png_file.name}")

    db.session.commit()
    logger.info(f"✅ Imported {imported_albums} batch albums with {imported_images} new images")


def import_orphaned_scrape_images():
    """Import images from orphaned scrape directories."""
    from server.database import AlbumImage, Image

    config = load_config()
    outputs_dir = Path(config["output"]["directory"])
    scraped_dir = outputs_dir / "scraped"

    if not scraped_dir.exists():
        logger.info("  ℹ️  No scraped directory found")
        return

    imported_albums = 0
    imported_images = 0

    # Group images by subdirectory
    for subdir in scraped_dir.iterdir():
        if not subdir.is_dir():
            continue

        png_files = list(subdir.glob("*.png"))
        if not png_files:
            logger.info(f"  ⏭️  Skipping empty scrape directory: {subdir.name}")
            continue

        logger.info(f"  📁 Processing scrape directory: {subdir.name} ({len(png_files)} images)")

        # Create album name
        album_name = f"Scrape - {subdir.name}"

        # Check if album exists
        existing = Album.query.filter_by(name=album_name).first()
        if existing:
            logger.info(f"    ℹ️  Album already exists: {album_name}")
            album = existing
        else:
            # Create album
            album = Album(
                name=album_name,
                description=f"Images from scrape job: {subdir.name}",
                source_type="scrape",
                is_public=True,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.session.add(album)
            db.session.flush()
            imported_albums += 1
            logger.info(f"    ✅ Created album: {album_name}")

        # Import images (same logic as batch)
        for png_file in png_files:
            existing_image = Image.query.filter_by(file_path=str(png_file)).first()

            if existing_image:
                link = AlbumImage.query.filter_by(
                    album_id=album.id, image_id=existing_image.id
                ).first()
                if not link:
                    assoc = AlbumImage(album_id=album.id, image_id=existing_image.id)
                    db.session.add(assoc)
                continue

            # Create new image
            image = Image(
                filename=png_file.name,
                file_path=str(png_file),
                is_nsfw=False,
                is_public=True,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.session.add(image)
            db.session.flush()

            assoc = AlbumImage(album_id=album.id, image_id=image.id)
            db.session.add(assoc)
            imported_images += 1

    db.session.commit()
    logger.info(f"✅ Imported {imported_albums} scrape albums with {imported_images} new images")


def import_orphaned_single_images():
    """Import single-generation images from outputs root."""
    from server.database import AlbumImage, Image

    config = load_config()
    outputs_dir = Path(config["output"]["directory"])

    # Find PNG files in root
    png_files = [f for f in outputs_dir.glob("*.png")]

    if not png_files:
        logger.info("  ℹ️  No single-generation images found in outputs root")
        return

    logger.info(f"  Found {len(png_files)} single-generation images")

    # Create one album for all ad-hoc generations
    album_name = "Ad-hoc Generations"
    album = Album.query.filter_by(name=album_name).first()

    if not album:
        album = Album(
            name=album_name,
            description="Single image generations and test renders",
            source_type="manual",
            is_public=True,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.session.add(album)
        db.session.flush()
        logger.info(f"  ✅ Created album: {album_name}")
    else:
        logger.info(f"  ℹ️  Album already exists: {album_name}")

    imported_count = 0
    for png_file in png_files:
        # Check if already in DB
        existing_image = Image.query.filter_by(file_path=str(png_file)).first()

        if existing_image:
            # Link if not already linked
            link = AlbumImage.query.filter_by(album_id=album.id, image_id=existing_image.id).first()
            if not link:
                assoc = AlbumImage(album_id=album.id, image_id=existing_image.id)
                db.session.add(assoc)
            continue

        # Load metadata
        json_file = png_file.with_suffix(".json")
        metadata = {}
        if json_file.exists():
            with open(json_file, "r") as f:
                metadata = json.load(f)

        # Create image
        image = Image(
            filename=png_file.name,
            file_path=str(png_file),
            prompt=metadata.get("prompt"),
            negative_prompt=metadata.get("negative_prompt"),
            seed=metadata.get("seed"),
            steps=metadata.get("steps"),
            guidance_scale=metadata.get("guidance_scale"),
            width=metadata.get("width"),
            height=metadata.get("height"),
            lora_config=json.dumps(metadata.get("loras", [])) if metadata.get("loras") else None,
            is_nsfw=False,
            is_public=True,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.session.add(image)
        db.session.flush()

        # Link to album
        assoc = AlbumImage(album_id=album.id, image_id=image.id)
        db.session.add(assoc)
        imported_count += 1

    db.session.commit()
    logger.info(f"✅ Imported {imported_count} single-generation images to '{album_name}'")


def add_scrape_job_album_name():
    """Add album_name column to scrape_jobs table."""

    inspector = db.inspect(db.engine)
    columns = [col["name"] for col in inspector.get_columns("scrape_jobs")]

    if "album_name" not in columns:
        with db.engine.connect() as conn:
            conn.execute(
                text(
                    """
                ALTER TABLE scrape_jobs ADD COLUMN album_name VARCHAR(255)
            """
                )
            )
            conn.commit()
        logger.info("✅ Added album_name column to scrape_jobs")
    else:
        logger.warning("⚠️  album_name column already exists on scrape_jobs")


def create_backup():
    """Create a timestamped backup of the database before migration."""
    from server.api import app

    with app.app_context():
        db_path = Path(app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", ""))

        if not db_path.exists():
            logger.warning(f"⚠️  Database not found at {db_path}, skipping backup")
            return None

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = db_path.parent / f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"

        import shutil

        shutil.copy2(db_path, backup_path)

        # Verify backup
        if backup_path.exists() and backup_path.stat().st_size > 0:
            logger.info(f"✅ Database backup created: {backup_path}")
            logger.info(f"   Size: {backup_path.stat().st_size:,} bytes")
            return backup_path
        else:
            raise Exception("Backup verification failed")


def verify_migration_success(app):
    """Verify the migration completed successfully."""
    with app.app_context():
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()

        checks = {
            "batch_templates table exists": "batch_templates" in tables,
            "batch_generation_runs table exists": "batch_generation_runs" in tables,
        }

        if "albums" in tables:
            cols = [c["name"] for c in inspector.get_columns("albums")]
            checks["albums.source_type exists"] = "source_type" in cols
            checks["albums.source_id exists"] = "source_id" in cols

        # Check no template albums remain
        from sqlalchemy import text

        template_album_count = db.session.execute(
            text("SELECT COUNT(*) FROM albums WHERE is_set_template = 1")
        ).fetchone()[0]
        checks["template albums deleted"] = template_album_count == 0

        # Check batch templates created
        batch_template_count = db.session.execute(
            text("SELECT COUNT(*) FROM batch_templates")
        ).fetchone()[0]
        checks["batch templates seeded"] = batch_template_count >= 3

        all_passed = all(checks.values())

        logger.info("\n" + "=" * 80)
        logger.info("MIGRATION VERIFICATION")
        logger.info("=" * 80)
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            logger.info(f"{status} {check}")

        return all_passed


if __name__ == "__main__":
    # Import Flask app
    from server.api import app

    logger.info("=" * 80)
    logger.info("TEMPLATE-ALBUM SEPARATION MIGRATION")
    logger.info("=" * 80)
    logger.info(f"Project root: {PROJECT_ROOT}")

    # Step 0: Create backup
    logger.info("\n[Step 0] Creating database backup...")
    backup_path = None
    try:
        backup_path = create_backup()
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        logger.error("Migration aborted for safety.")
        sys.exit(1)

    # Run migration
    try:
        run_migration(app)

        # Verify migration
        if verify_migration_success(app):
            logger.info("\n✅ Migration completed successfully!")
            logger.info(f"\nBackup saved at: {backup_path}")
            logger.info(
                "You can safely delete the backup after verifying the system works correctly."
            )
            sys.exit(0)
        else:
            logger.error("\n❌ Migration verification failed!")
            logger.error(f"To rollback: cp {backup_path} {backup_path.parent / 'imagineer.db'}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"\n❌ Migration failed: {e}", exc_info=True)
        logger.error("\n⚠️  Database may be in an inconsistent state.")
        logger.error("\nTo rollback, run:")
        logger.error(f"  cp {backup_path} {backup_path.parent / 'imagineer.db'}")
        sys.exit(1)
