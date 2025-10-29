#!/usr/bin/env python3
"""
Migration script to import existing images from /mnt/speedy/imagineer/outputs to database
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask  # noqa: E402

from server.database import Album, AlbumImage, Image, MigrationHistory, db  # noqa: E402

MIGRATION_MARKER_NAME = "filesystem_outputs_import_v1"


def create_app():
    """Create Flask app for migration"""
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///imagineer.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    return app


def find_metadata_file(image_path):
    """Find corresponding .json metadata file for an image"""
    base_path = Path(image_path).with_suffix("")
    json_path = base_path.with_suffix(".json")
    return json_path if json_path.exists() else None


def load_image_metadata(json_path):
    """Load metadata from JSON file"""
    try:
        with open(json_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading metadata from {json_path}: {e}")
        return {}


def create_thumbnail_path(image_path):
    """Generate thumbnail path (placeholder for now)"""
    # TODO: Implement actual thumbnail generation
    return None


def migrate_images():
    """Migrate all images from outputs directory to database"""
    app = create_app()

    with app.app_context():
        # Create tables if they don't exist
        db.create_all()

        if MigrationHistory.has_run(MIGRATION_MARKER_NAME):
            existing_marker = MigrationHistory.query.filter_by(name=MIGRATION_MARKER_NAME).first()
            applied = (
                existing_marker.applied_at.isoformat()
                if existing_marker and existing_marker.applied_at
                else "unknown"
            )
            print(
                f"Migration '{MIGRATION_MARKER_NAME}' has already been recorded "
                f"(first applied at {applied}). Skipping import."
            )
            return

        # Base paths
        outputs_dir = Path("/mnt/speedy/imagineer/outputs")
        if not outputs_dir.exists():
            print(f"Outputs directory not found: {outputs_dir}")
            return

        print(f"Scanning outputs directory: {outputs_dir}")

        # Find all batch directories
        batch_dirs = [d for d in outputs_dir.iterdir() if d.is_dir()]
        print(f"Found {len(batch_dirs)} batch directories")

        total_images = 0
        total_albums = 0

        for batch_dir in batch_dirs:
            print(f"\nProcessing batch: {batch_dir.name}")

            # Create album for this batch
            album = Album(
                name=batch_dir.name,
                description=f"Imported batch from {batch_dir.name}",
                album_type="batch",
                is_public=True,
            )
            db.session.add(album)
            db.session.flush()  # Get the album ID

            # Find all image files in this batch
            image_files = []
            for ext in ["*.png", "*.jpg", "*.jpeg"]:
                image_files.extend(batch_dir.glob(ext))

            print(f"  Found {len(image_files)} images")

            for image_path in image_files:
                # Skip if already in database
                if Image.query.filter_by(filename=image_path.name).first():
                    print(f"    Skipping {image_path.name} (already in database)")
                    continue

                # Load metadata
                metadata = {}
                json_path = find_metadata_file(image_path)
                if json_path:
                    metadata = load_image_metadata(json_path)

                # Create image record
                image = Image(
                    filename=image_path.name,
                    file_path=str(image_path),
                    thumbnail_path=create_thumbnail_path(image_path),
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
                    is_nsfw=False,  # Default to False, can be updated later
                    is_public=True,
                )

                db.session.add(image)
                db.session.flush()  # Get the image ID

                # Add to album
                album_image = AlbumImage(
                    album_id=album.id, image_id=image.id, sort_order=total_images
                )
                db.session.add(album_image)

                total_images += 1
                print(f"    Imported: {image_path.name}")

            total_albums += 1

        # Commit all changes
        migration_summary = json.dumps(
            {
                "total_albums": total_albums,
                "total_images": total_images,
                "script": "scripts/migrate_to_database.py",
                "recorded_at": datetime.utcnow().isoformat() + "Z",
            }
        )
        MigrationHistory.ensure_record(MIGRATION_MARKER_NAME, details=migration_summary)
        db.session.commit()

        print("\nMigration completed!")
        print(f"  Albums created: {total_albums}")
        print(f"  Images imported: {total_images}")
        print(f"  Recorded migration marker: {MIGRATION_MARKER_NAME}")

        # Show summary
        print("\nDatabase summary:")
        print(f"  Total albums: {Album.query.count()}")
        print(f"  Total images: {Image.query.count()}")
        print(f"  Total album-image relationships: {AlbumImage.query.count()}")


if __name__ == "__main__":
    migrate_images()
