#!/usr/bin/env python3
"""
Clean up test data from production database.

This script identifies and removes test images, albums, labels, and other
test artifacts that were created during development/testing.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from server.api import app  # noqa: E402
from server.database import (  # noqa: E402
    Album,
    AlbumImage,
    BatchGenerationRun,
    BatchTemplate,
    Image,
    Label,
    ScrapeJob,
    db,
)


def identify_test_data():
    """Identify all test data in the database."""
    with app.app_context():
        print("=== Analyzing Database for Test Data ===\n")

        # Check albums
        albums = Album.query.all()
        test_albums = []
        for album in albums:
            if any(
                keyword in (album.name or "").lower()
                for keyword in ["test", "rate limit", "debug", "sample", "demo"]
            ):
                test_albums.append(album)

        print(f"📁 Albums: {len(albums)} total, {len(test_albums)} appear to be test data")
        if test_albums:
            print("   Test albums:")
            for album in test_albums[:10]:  # Show first 10
                img_count = AlbumImage.query.filter_by(album_id=album.id).count()
                print(
                    f"   - ID {album.id}: '{album.name}' "
                    f"({album.album_type}, {img_count} images)"
                )
            if len(test_albums) > 10:
                print(f"   ... and {len(test_albums) - 10} more")

        # Check images (look for test/rate limit test images)
        images = Image.query.all()
        test_images = []
        for image in images:
            if any(
                keyword in (image.filename or "").lower()
                for keyword in ["test", "sample", "debug", "tmp", "rate_limit", "rate limit"]
            ):
                test_images.append(image)

        print(f"\n🖼️  Images: {len(images)} total, {len(test_images)} appear to be test data")

        # Check scrape jobs
        scrape_jobs = ScrapeJob.query.all()
        test_scrapes = []
        for job in scrape_jobs:
            if any(keyword in (job.name or "").lower() for keyword in ["test", "sample", "debug"]):
                test_scrapes.append(job)

        print(
            f"\n🕷️  Scrape Jobs: {len(scrape_jobs)} total, "
            f"{len(test_scrapes)} appear to be test data"
        )
        if test_scrapes:
            print("   Test scrape jobs:")
            for job in test_scrapes:
                print(f"   - ID {job.id}: '{job.name}' (status: {job.status})")

        # Check batch templates
        templates = BatchTemplate.query.all()
        test_templates = []
        for template in templates:
            if any(
                keyword in (template.name or "").lower() for keyword in ["test", "sample", "debug"]
            ):
                test_templates.append(template)

        print(
            f"\n📋 Batch Templates: {len(templates)} total, "
            f"{len(test_templates)} appear to be test data"
        )

        # Check batch generation runs
        runs = BatchGenerationRun.query.all()
        test_runs = []
        for run in runs:
            if run.album_id:
                album = Album.query.get(run.album_id)
                if album and any(
                    keyword in (album.name or "").lower() for keyword in ["test", "sample", "debug"]
                ):
                    test_runs.append(run)

        print(
            f"\n🎨 Batch Generation Runs: {len(runs)} total, "
            f"{len(test_runs)} appear to be test data"
        )

        # Check labels
        labels = Label.query.all()
        print(f"\n🏷️  Labels: {len(labels)} total")

        return {
            "test_albums": test_albums,
            "test_images": test_images,
            "test_scrapes": test_scrapes,
            "test_templates": test_templates,
            "test_runs": test_runs,
        }


def cleanup_test_data(dry_run=True):
    """
    Clean up test data from database and file system.

    Args:
        dry_run: If True, only show what would be deleted without actually deleting
    """
    with app.app_context():
        test_data = identify_test_data()

        if not any(test_data.values()):
            print("\n✅ No test data found!")
            return

        print("\n" + "=" * 60)
        if dry_run:
            print("DRY RUN - Showing what would be deleted")
        else:
            print("⚠️  DELETION MODE - This will permanently delete data!")
        print("=" * 60)

        # Delete test albums and their images
        for album in test_data["test_albums"]:
            album_images = AlbumImage.query.filter_by(album_id=album.id).all()
            image_ids = [ai.image_id for ai in album_images]
            images = Image.query.filter(Image.id.in_(image_ids)).all() if image_ids else []

            print(f"\n🗑️  Album '{album.name}' (ID: {album.id}):")
            print(f"   - {len(album_images)} album-image associations")
            print(f"   - {len(images)} images")

            if not dry_run:
                # Delete labels for these images
                if image_ids:
                    Label.query.filter(Label.image_id.in_(image_ids)).delete(
                        synchronize_session=False
                    )

                # Delete album-image associations
                AlbumImage.query.filter_by(album_id=album.id).delete()

                # Delete images and their files
                for image in images:
                    if image.file_path and Path(image.file_path).exists():
                        try:
                            Path(image.file_path).unlink()
                            print(f"   ✓ Deleted file: {image.file_path}")
                        except Exception as e:
                            print(f"   ✗ Error deleting file {image.file_path}: {e}")

                    db.session.delete(image)

                # Delete the album
                db.session.delete(album)
                print("   ✓ Deleted album and all associated data")

        # Delete test scrape jobs
        for job in test_data["test_scrapes"]:
            print(f"\n🗑️  Scrape Job '{job.name}' (ID: {job.id})")

            if not dry_run:
                # Delete output directory if it exists
                if job.output_directory and Path(job.output_directory).exists():
                    import shutil

                    try:
                        shutil.rmtree(job.output_directory)
                        print(f"   ✓ Deleted output directory: {job.output_directory}")
                    except Exception as e:
                        print(f"   ✗ Error deleting directory: {e}")

                db.session.delete(job)
                print("   ✓ Deleted scrape job")

        # Delete test batch generation runs
        for run in test_data["test_runs"]:
            print(f"\n🗑️  Batch Generation Run (ID: {run.id})")

            if not dry_run:
                db.session.delete(run)
                print("   ✓ Deleted batch generation run")

        # Delete individual test images from non-test albums
        # (e.g., rate_limit_test images in "Ad-hoc Generations")
        orphan_test_images = []
        for image in test_data["test_images"]:
            # Check if this image is in any test album
            in_test_album = False
            album_assocs = AlbumImage.query.filter_by(image_id=image.id).all()

            for assoc in album_assocs:
                if assoc.album_id in [a.id for a in test_data["test_albums"]]:
                    in_test_album = True
                    break

            # If not in a test album, it's an orphan test image
            if not in_test_album:
                orphan_test_images.append(image)

        if orphan_test_images:
            print(f"\n🗑️  Orphan Test Images (not in test albums): {len(orphan_test_images)}")
            print(
                f"   Examples: {', '.join([img.filename[:40] for img in orphan_test_images[:5]])}"
            )

            if not dry_run:
                for image in orphan_test_images:
                    # Delete labels
                    Label.query.filter_by(image_id=image.id).delete()

                    # Delete album associations
                    AlbumImage.query.filter_by(image_id=image.id).delete()

                    # Delete file
                    if image.file_path and Path(image.file_path).exists():
                        try:
                            Path(image.file_path).unlink()
                            print(f"   ✓ Deleted file: {image.file_path}")
                        except Exception as e:
                            print(f"   ✗ Error deleting file {image.file_path}: {e}")

                    # Delete thumbnail if exists (using image_id)
                    from server.config_loader import load_config

                    config = load_config()
                    outputs_base = config.get("outputs", {}).get(
                        "base_dir", "/tmp/imagineer/outputs"
                    )
                    outputs_dir = Path(outputs_base).resolve()
                    thumbnail_path = outputs_dir / "thumbnails" / f"{image.id}.webp"
                    if thumbnail_path.exists():
                        try:
                            thumbnail_path.unlink()
                        except Exception:
                            pass

                    # Delete image record
                    db.session.delete(image)

                print(f"   ✓ Deleted {len(orphan_test_images)} orphan test images")

        if not dry_run:
            db.session.commit()
            print("\n✅ Cleanup complete!")
        else:
            print("\n💡 Run with --execute to actually delete this data")


def show_all_data():
    """Show all data in the database for review."""
    with app.app_context():
        print("=== All Database Records ===\n")

        print("📁 ALBUMS:")
        albums = Album.query.order_by(Album.created_at.desc()).all()
        for album in albums:
            img_count = AlbumImage.query.filter_by(album_id=album.id).count()
            print(
                f"  ID {album.id}: '{album.name}' ({album.album_type}, "
                f"{album.source_type}, {img_count} images, created: {album.created_at})"
            )

        print(f"\n🖼️  IMAGES: {Image.query.count()} total")

        print(f"\n🕷️  SCRAPE JOBS:")
        jobs = ScrapeJob.query.order_by(ScrapeJob.created_at.desc()).all()
        for job in jobs:
            print(
                f"  ID {job.id}: '{job.name}' - {job.source_url} "
                f"(status: {job.status}, created: {job.created_at})"
            )

        print(f"\n📋 BATCH TEMPLATES:")
        templates = BatchTemplate.query.order_by(BatchTemplate.created_at.desc()).all()
        for template in templates:
            print(f"  ID {template.id}: '{template.name}' (created: {template.created_at})")

        print(f"\n🎨 BATCH GENERATION RUNS: {BatchGenerationRun.query.count()} total")
        print(f"🏷️  LABELS: {Label.query.count()} total")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Clean up test data from production")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete data (default is dry-run)",
    )
    parser.add_argument("--show-all", action="store_true", help="Show all database records")

    args = parser.parse_args()

    if args.show_all:
        show_all_data()
    else:
        cleanup_test_data(dry_run=not args.execute)
