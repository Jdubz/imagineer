#!/usr/bin/env python3
"""Verify album organization"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask  # noqa: E402

from server.database import Album, Image, db  # noqa: E402

app = Flask(__name__)
db_path = Path(__file__).parent.parent / "instance" / "imagineer.db"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

with app.app_context():
    albums = Album.query.all()

    print("\n" + "=" * 70)
    print("ALBUM VERIFICATION")
    print("=" * 70 + "\n")

    for album in albums:
        image_count = len(album.album_images)
        print(f"📁 {album.name}")
        print(f"   ID: {album.id}")
        print(f"   Type: {album.album_type}")
        print(f"   Images: {image_count}")
        print(f"   Public: {album.is_public}")
        desc = album.description if album.description else ""
        if len(desc) > 60:
            print(f"   Description: {desc[:60]}...")
        else:
            print(f"   Description: {desc}")
        print()

    # Get unorganized images
    all_images = Image.query.all()
    unorganized = [img for img in all_images if not img.album_images]

    print("=" * 70)
    print(f"Total Albums: {len(albums)}")
    print(f"Total Image Associations: {sum(len(a.album_images) for a in albums)}")
    print(f"Total Images in DB: {len(all_images)}")
    print(f"Unorganized Images: {len(unorganized)}")

    if unorganized:
        print("\nUnorganized images:")
        for img in unorganized[:10]:
            print(f"  - {img.file_path}")
        if len(unorganized) > 10:
            print(f"  ... and {len(unorganized) - 10} more")

    print("=" * 70 + "\n")
