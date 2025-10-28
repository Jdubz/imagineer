#!/usr/bin/env python3
"""
Image Indexing Script

Scans the outputs directory and indexes all images into the database
with their metadata from JSON sidecar files.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask  # noqa: E402

from server.database import Image, MigrationHistory, db  # noqa: E402

INDEX_MARKER_NAME = "image_indexing_v1"


def create_app():
    """Create Flask app with database context."""
    app = Flask(__name__)

    # Use absolute path to database
    db_path = Path(__file__).parent.parent / "instance" / "imagineer.db"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    return app


def load_metadata(json_path):
    """Load metadata from JSON sidecar file."""
    try:
        with open(json_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"    ⚠ Error reading {json_path}: {e}")
        return {}


def index_images(outputs_dir):  # noqa: C901
    """Scan outputs directory and index all images."""
    print("=" * 70)
    print("IMAGE INDEXING SCRIPT")
    print("=" * 70)
    print()
    print(f"Scanning directory: {outputs_dir}")
    print()

    # Find all image files
    image_extensions = {".png", ".jpg", ".jpeg"}
    image_files = []

    for ext in image_extensions:
        image_files.extend(list(outputs_dir.rglob(f"*{ext}")))

    print(f"Found {len(image_files)} image files")
    print()

    # Statistics
    added_count = 0
    skipped_count = 0
    error_count = 0

    for img_path in image_files:
        # Skip thumbnails
        if "thumbnails" in str(img_path):
            continue

        # Get relative path from outputs directory
        try:
            relative_to_outputs = img_path.relative_to(outputs_dir)
            file_path = str(relative_to_outputs)
        except ValueError:
            print(f"    ⚠ Skipping file outside outputs: {img_path}")
            continue

        filename = img_path.name

        # Check if already indexed
        existing = Image.query.filter_by(filename=filename).first()
        if existing:
            skipped_count += 1
            continue

        # Load metadata from JSON sidecar
        json_path = img_path.with_suffix(".json")
        metadata = {}
        if json_path.exists():
            metadata = load_metadata(json_path)

        # Get file creation time
        created_at = datetime.fromtimestamp(img_path.stat().st_mtime)

        # Create database entry
        try:
            image = Image(
                filename=filename,
                file_path=file_path,
                prompt=metadata.get("prompt"),
                negative_prompt=metadata.get("negative_prompt"),
                seed=metadata.get("seed"),
                steps=metadata.get("steps"),
                guidance_scale=metadata.get("guidance_scale"),
                width=metadata.get("width"),
                height=metadata.get("height"),
                lora_config=json.dumps(metadata.get("lora", [])) if metadata.get("lora") else None,
                created_at=created_at,
            )
            db.session.add(image)
            added_count += 1

            if added_count % 10 == 0:
                print(f"  Indexed {added_count} images...", end="\r")

        except Exception as e:
            error_count += 1
            print(f"    ✗ Error indexing {filename}: {e}")
            continue

    # Commit all changes
    try:
        indexing_summary = json.dumps(
            {
                "added": added_count,
                "skipped": skipped_count,
                "errors": error_count,
                "script": "scripts/index_images.py",
                "recorded_at": datetime.utcnow().isoformat() + "Z",
            }
        )
        MigrationHistory.ensure_record(
            INDEX_MARKER_NAME,
            details=indexing_summary,
            refresh_timestamp=True,
        )
        db.session.commit()
        print()
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"  ✓ Added: {added_count}")
        print(f"  ⊘ Skipped (already indexed): {skipped_count}")
        print(f"  ✗ Errors: {error_count}")
        print(f"  Total in database: {Image.query.count()}")
        print()
        print("✅ Image indexing complete!")

    except Exception as e:
        db.session.rollback()
        print(f"✗ Error committing to database: {e}")
        return False

    return True


if __name__ == "__main__":
    outputs_dir = Path("/mnt/speedy/imagineer/outputs")

    if not outputs_dir.exists():
        print(f"Error: Outputs directory not found: {outputs_dir}")
        sys.exit(1)

    app = create_app()

    with app.app_context():
        success = index_images(outputs_dir)
        sys.exit(0 if success else 1)
