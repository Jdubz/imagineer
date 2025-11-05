#!/usr/bin/env python3
"""
Migration: Remove is_training_source column from albums table.

The is_training_source flag was a premature optimization. Training runs
should be able to select any albums with properly labeled images, not just
pre-designated "training source" albums.

This migration:
1. Removes is_training_source column from Album model
2. Updates Album.to_dict() to no longer include the field
3. GET /api/training/albums will return ALL albums with labeling metadata
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.api import app  # noqa: E402
from server.database import db  # noqa: E402


def migrate():
    """Remove is_training_source column from albums table."""
    with app.app_context():
        print("=" * 60)
        print("Migration: Remove is_training_source column")
        print("=" * 60)

        # Check if column exists
        inspector = db.inspect(db.engine)
        columns = [col["name"] for col in inspector.get_columns("albums")]

        if "is_training_source" not in columns:
            print("✓ is_training_source column already removed")
            return

        print("\n1. Checking current albums with is_training_source=True...")
        result = db.session.execute(
            db.text("SELECT id, name, is_training_source FROM albums WHERE is_training_source = 1")
        )
        training_albums = result.fetchall()

        if training_albums:
            print(f"   Found {len(training_albums)} albums marked as training sources:")
            for album in training_albums:
                print(f"   - Album {album[0]}: {album[1]}")
        else:
            print("   No albums currently marked as training sources")

        print("\n2. Dropping is_training_source column...")
        try:
            # SQLite doesn't support DROP COLUMN directly, need to recreate table
            db.session.execute(
                db.text(
                    """
                CREATE TABLE albums_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    album_type VARCHAR(50) DEFAULT 'batch',
                    is_public BOOLEAN DEFAULT 1,
                    created_by VARCHAR(255),
                    generation_prompt TEXT,
                    generation_config TEXT,
                    is_set_template BOOLEAN DEFAULT 0,
                    csv_data TEXT,
                    base_prompt TEXT,
                    prompt_template TEXT,
                    style_suffix TEXT,
                    example_theme TEXT,
                    lora_config TEXT,
                    created_at DATETIME,
                    updated_at DATETIME,
                    source_type VARCHAR(50) DEFAULT 'manual',
                    source_id INTEGER
                )
            """
                )
            )

            # Copy data (excluding is_training_source)
            db.session.execute(
                db.text(
                    """
                INSERT INTO albums_new (
                    id, name, description, album_type, is_public, created_by,
                    generation_prompt, generation_config, is_set_template, csv_data,
                    base_prompt, prompt_template, style_suffix, example_theme,
                    lora_config, created_at, updated_at, source_type, source_id
                )
                SELECT
                    id, name, description, album_type, is_public, created_by,
                    generation_prompt, generation_config, is_set_template, csv_data,
                    base_prompt, prompt_template, style_suffix, example_theme,
                    lora_config, created_at, updated_at, source_type, source_id
                FROM albums
            """
                )
            )

            # Drop old table and rename new one
            db.session.execute(db.text("DROP TABLE albums"))
            db.session.execute(db.text("ALTER TABLE albums_new RENAME TO albums"))

            db.session.commit()
            print("   ✓ Column removed successfully")

        except Exception as e:
            print(f"   ✗ Error: {e}")
            db.session.rollback()
            raise

        print("\n3. Verifying migration...")
        inspector = db.inspect(db.engine)
        columns = [col["name"] for col in inspector.get_columns("albums")]

        if "is_training_source" not in columns:
            print("   ✓ is_training_source column successfully removed")
        else:
            print("   ✗ Column still exists!")
            sys.exit(1)

        print("\n" + "=" * 60)
        print("Migration Complete!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Training API now returns ALL albums")
        print("2. Frontend should query albums with labeling metadata")
        print("3. Users can select any albums with captioned images")


if __name__ == "__main__":
    migrate()
