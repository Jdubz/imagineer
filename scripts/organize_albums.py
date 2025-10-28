#!/usr/bin/env python3
"""
Album Organization Script

Organizes all generated images into sensible albums based on their
directory location and metadata.

Categories:
1. Sexy Barnyard Animals Playing Cards (set) - card_deck_*
2. Tarot Deck - Major Arcana (set) - tarot_deck_*
3. Zodiac Signs (set) - zodiac_*
4. LoRA Model Tests (collection) - lora_tests/
5. User Uploads (collection) - uploads/
6. Experimental & Test Generations (manual) - root level misc images
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask  # noqa: E402

from server.database import Album, AlbumImage, Image, db  # noqa: E402


def create_app():
    """Create Flask app with database context."""
    app = Flask(__name__)

    # Use absolute path to database
    db_path = Path(__file__).parent.parent / "instance" / "imagineer.db"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    return app


def create_or_get_album(name, description, album_type="collection", is_public=True):
    """Create album or return existing one."""
    existing = Album.query.filter_by(name=name).first()
    if existing:
        print(f"  ✓ Album '{name}' already exists (ID: {existing.id})")
        return existing

    album = Album(name=name, description=description, album_type=album_type, is_public=is_public)
    db.session.add(album)
    db.session.commit()
    print(f"  ✓ Created album '{name}' (ID: {album.id})")
    return album


def add_images_to_album(album, image_paths, outputs_dir):
    """Add images to album based on file paths."""
    added_count = 0
    skipped_count = 0

    for path_pattern in image_paths:
        # Find images matching the pattern
        if "*" in path_pattern:
            # Glob pattern
            from glob import glob

            matching_files = glob(str(outputs_dir / path_pattern / "*.png"))
            matching_files.extend(glob(str(outputs_dir / path_pattern / "*.jpg")))
        else:
            # Direct path pattern
            matching_files = list((outputs_dir / path_pattern).glob("*.png"))
            matching_files.extend(list((outputs_dir / path_pattern).glob("*.jpg")))

        for img_path in matching_files:
            # Get relative path from outputs directory
            file_path = str(Path(img_path).relative_to(outputs_dir))

            # Find image in database
            image = Image.query.filter_by(file_path=file_path).first()

            if not image:
                print(f"    ⚠ Image not in database: {file_path}")
                continue

            # Check if already in album
            existing = AlbumImage.query.filter_by(album_id=album.id, image_id=image.id).first()

            if existing:
                skipped_count += 1
                continue

            # Add to album
            album_image = AlbumImage(
                album_id=album.id, image_id=image.id, sort_order=len(album.album_images)
            )
            db.session.add(album_image)
            added_count += 1

    db.session.commit()
    print(f"    Added {added_count} images, skipped {skipped_count} duplicates")
    return added_count


def organize_albums():
    """Main function to organize all images into albums."""
    outputs_dir = Path("/mnt/speedy/imagineer/outputs")

    print("=" * 70)
    print("ALBUM ORGANIZATION SCRIPT")
    print("=" * 70)
    print()

    # Get total image count
    total_images = Image.query.count()
    print(f"Total images in database: {total_images}")
    print()

    # Define album structure
    albums_config = [
        {
            "name": "🃏 Sexy Barnyard Animals Playing Cards",
            "description": (
                "Complete 54-card playing deck featuring anthropomorphic barnyard "
                "animals with mystical card meanings. Generated with custom LoRA models."
            ),
            "album_type": "set",
            "paths": ["card_deck_*"],
        },
        {
            "name": "🔮 Tarot Deck - Major Arcana",
            "description": (
                "22 Major Arcana tarot cards with traditional mystical symbolism "
                "and detailed illustrations."
            ),
            "album_type": "set",
            "paths": ["tarot_deck_*"],
        },
        {
            "name": "♈ Zodiac Signs Collection",
            "description": "All 12 zodiac signs with astrological symbolism and celestial themes.",
            "album_type": "set",
            "paths": ["zodiac_*"],
        },
        {
            "name": "🎨 LoRA Model Tests",
            "description": (
                "Test outputs for evaluating LoRA model quality, consistency, "
                "and capabilities. Used for model validation before production use."
            ),
            "album_type": "collection",
            "paths": ["lora_tests"],
        },
        {
            "name": "📤 User Uploads",
            "description": (
                "Images uploaded by users through the web interface for reference, "
                "inspiration, or training data preparation."
            ),
            "album_type": "collection",
            "paths": ["uploads"],
        },
        {
            "name": "🧪 Experimental & Test Generations",
            "description": (
                "Miscellaneous test generations, experiments, and one-off creations. "
                "Includes prompt testing, style experiments, and concept validation."
            ),
            "album_type": "manual",
            "paths": [],  # Will handle root-level images separately
        },
    ]

    # Create albums and assign images
    print("Creating albums and organizing images...")
    print()

    for config in albums_config:
        print(f"📁 {config['name']}")

        album = create_or_get_album(
            name=config["name"], description=config["description"], album_type=config["album_type"]
        )

        if config["paths"]:
            add_images_to_album(album, config["paths"], outputs_dir)

        print()

    # Handle root-level images for Experimental album
    print("📁 🧪 Experimental & Test Generations")
    experimental_album = Album.query.filter_by(name="🧪 Experimental & Test Generations").first()

    if experimental_album:
        # Get all root-level images (not in subdirectories)
        all_images = Image.query.all()
        root_images = [
            img
            for img in all_images
            if "/" not in img.file_path and img.file_path.endswith((".png", ".jpg"))
        ]

        added_count = 0
        for image in root_images:
            # Check if already in any album
            if not image.album_images:
                album_image = AlbumImage(
                    album_id=experimental_album.id,
                    image_id=image.id,
                    sort_order=len(experimental_album.album_images),
                )
                db.session.add(album_image)
                added_count += 1

        db.session.commit()
        print(f"    Added {added_count} root-level images")
        print()

    # Print summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    all_albums = Album.query.all()
    for album in all_albums:
        image_count = len(album.album_images)
        print(f"  {album.name}: {image_count} images")

    print()
    print(f"Total albums: {len(all_albums)}")
    print(f"Total images organized: {sum(len(a.album_images) for a in all_albums)}")
    print()
    print("✅ Album organization complete!")


if __name__ == "__main__":
    app = create_app()

    with app.app_context():
        organize_albums()
