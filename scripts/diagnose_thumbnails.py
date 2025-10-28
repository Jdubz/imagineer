#!/usr/bin/env python3
"""
Diagnostic script for thumbnail generation issues
Run this on the production server to identify the problem
"""

import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml  # noqa: E402
from flask import Flask  # noqa: E402

from server.database import Image, init_database  # noqa: E402


def diagnose():  # noqa: C901
    """Run diagnostics on thumbnail system"""
    print("=" * 70)
    print("THUMBNAIL DIAGNOSTICS")
    print("=" * 70)

    # Check config
    config_path = Path(__file__).parent.parent / "config.yaml"
    print(f"\n1. Config file: {config_path}")
    print(f"   Exists: {config_path.exists()}")

    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)

        outputs_dir = Path(config.get("outputs", {}).get("base_dir", "/tmp/imagineer/outputs"))
        print(f"\n2. Outputs directory: {outputs_dir}")
        print(f"   Exists: {outputs_dir.exists()}")
        print(f"   Is absolute: {outputs_dir.is_absolute()}")
        print(f"   Resolved: {outputs_dir.resolve()}")

        if outputs_dir.exists():
            print(f"   Readable: {os.access(outputs_dir, os.R_OK)}")
            print(f"   Writable: {os.access(outputs_dir, os.W_OK)}")
            print(f"   Executable: {os.access(outputs_dir, os.X_OK)}")

        # Check thumbnails directory
        thumbnail_dir = outputs_dir / "thumbnails"
        print(f"\n3. Thumbnail directory: {thumbnail_dir}")
        print(f"   Exists: {thumbnail_dir.exists()}")

        if not thumbnail_dir.exists():
            print("   Attempting to create...")
            try:
                thumbnail_dir.mkdir(parents=True, exist_ok=True)
                print("   ✓ Created successfully")
            except Exception as e:
                print(f"   ✗ Failed: {e}")
        else:
            print(f"   Readable: {os.access(thumbnail_dir, os.R_OK)}")
            print(f"   Writable: {os.access(thumbnail_dir, os.W_OK)}")

    # Check database
    app = Flask(__name__)
    db_path = Path(__file__).parent.parent / "instance" / "imagineer.db"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    print(f"\n4. Database: {db_path}")
    print(f"   Exists: {db_path.exists()}")

    if db_path.exists():
        init_database(app)

        with app.app_context():
            total_images = Image.query.count()
            public_images = Image.query.filter_by(is_public=True).count()

            print(f"   Total images: {total_images}")
            print(f"   Public images: {public_images}")

            # Check a few sample images
            if total_images > 0:
                print("\n5. Sample images:")
                samples = Image.query.filter_by(is_public=True).limit(5).all()

                for img in samples:
                    image_path = Path(img.file_path)
                    if not image_path.is_absolute():
                        image_path = (outputs_dir / img.file_path).resolve()

                    exists = image_path.exists() if outputs_dir.exists() else False
                    print(f"   ID {img.id}: {img.file_path}")
                    print(f"      Resolved: {image_path}")
                    print(f"      Exists: {exists}")

                    if exists:
                        print(f"      Size: {image_path.stat().st_size} bytes")
                        print(f"      Readable: {os.access(image_path, os.R_OK)}")

    print("\n" + "=" * 70)
    print("DIAGNOSTICS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    try:
        diagnose()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
