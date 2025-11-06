"""
Celery tasks for image upload and processing
"""

import io
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image as PILImage
from werkzeug.utils import secure_filename

from server.celery_app import celery
from server.database import Album, AlbumImage, Image, db

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
MAX_UPLOAD_FILE_BYTES = int(os.environ.get("IMAGINEER_UPLOAD_MAX_BYTES", str(20 * 1024 * 1024)))
MAX_UPLOAD_DIMENSION = int(os.environ.get("IMAGINEER_UPLOAD_MAX_DIMENSION", "4096"))


def _extract_image_dimensions(file_bytes: bytes, filename: str) -> tuple[int | None, int | None]:
    """Return (width, height) for provided image bytes."""
    try:
        with PILImage.open(io.BytesIO(file_bytes)) as img:
            return img.size
    except Exception as exc:
        logger.warning(
            "Unable to read image metadata for %s: %s",
            filename,
            exc,
            extra={"operation": "bulk_upload", "issue": "metadata_read_failed"},
        )
        return None, None


def _persist_upload(filepath: Path, file_bytes: bytes) -> None:
    """Persist uploaded bytes to disk using low-level I/O."""
    fd = os.open(str(filepath), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        os.write(fd, file_bytes)
    finally:
        os.close(fd)


def _path_exists(path: Path) -> bool:
    """Filesystem existence check."""
    try:
        return os.path.exists(path)
    except OSError:
        return False


@celery.task(bind=True, name="images.bulk_upload")
def bulk_upload_task(
    self, files_data: list[dict], album_id: int | None, album_name: str | None, added_by: str | None
):
    """
    Background task for bulk image uploads.

    Args:
        files_data: List of dicts with 'filename' and 'content' (bytes as list)
        album_id: Target album ID (optional)
        album_name: Album name (creates if not exists, optional)
        added_by: Email of user who uploaded

    Returns:
        dict with success status and uploaded image details
    """
    from server.api import app, load_config

    with app.app_context():
        try:
            # Support creating new album by name
            if album_name and not album_id:
                album = Album.query.filter_by(name=album_name).first()
                if not album:
                    album = Album(
                        name=album_name,
                        album_type="manual",
                        source_type="manual",
                        description=f"Created via bulk upload at {datetime.now().isoformat()}",
                    )
                    db.session.add(album)
                    db.session.flush()
                album_id = album.id

            config = load_config()
            outputs_dir = Path(config.get("outputs", {}).get("base_dir", "/tmp/imagineer/outputs"))
            upload_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            upload_dir = outputs_dir / "uploads" / upload_id
            upload_dir.mkdir(parents=True, exist_ok=True)

            uploaded_images = []
            failed_files = []
            total_files = len(files_data)

            for idx, file_data in enumerate(files_data):
                # Update progress
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": idx + 1,
                        "total": total_files,
                        "status": f"Processing {file_data['filename']}",
                    },
                )

                try:
                    filename = secure_filename(file_data["filename"])
                    file_bytes = bytes(file_data["content"])

                    # Validate file extension
                    ext = Path(filename).suffix.lower()
                    if ext not in ALLOWED_IMAGE_EXTENSIONS:
                        failed_files.append(
                            {
                                "filename": filename,
                                "error": f"Unsupported file type: {ext}",
                            }
                        )
                        continue

                    # Validate file size
                    file_size = len(file_bytes)
                    if file_size == 0:
                        failed_files.append({"filename": filename, "error": "File is empty"})
                        continue

                    if MAX_UPLOAD_FILE_BYTES and file_size > MAX_UPLOAD_FILE_BYTES:
                        max_mb = MAX_UPLOAD_FILE_BYTES / (1024 * 1024)
                        failed_files.append(
                            {
                                "filename": filename,
                                "error": f"Exceeds per-file limit of {max_mb:.1f} MiB",
                            }
                        )
                        continue

                    # Validate dimensions
                    width, height = _extract_image_dimensions(file_bytes, filename)
                    if width is None or height is None:
                        failed_files.append(
                            {"filename": filename, "error": "Not a valid image file"}
                        )
                        continue

                    if MAX_UPLOAD_DIMENSION and (
                        width > MAX_UPLOAD_DIMENSION or height > MAX_UPLOAD_DIMENSION
                    ):
                        failed_files.append(
                            {
                                "filename": filename,
                                "error": (
                                    f"Dimensions {width}x{height} exceed "
                                    f"maximum {MAX_UPLOAD_DIMENSION}px"
                                ),
                            }
                        )
                        continue

                    # Handle filename conflicts
                    filepath = upload_dir / filename
                    if _path_exists(filepath):
                        stem = Path(filename).stem
                        for counter in range(1, 50):
                            candidate = upload_dir / f"{stem}_{counter}{ext}"
                            if not _path_exists(candidate):
                                filename = candidate.name
                                filepath = candidate
                                break
                        else:
                            unique_name = f"{stem}_{uuid.uuid4().hex}{ext}"
                            filepath = upload_dir / unique_name
                            filename = filepath.name

                    # Save file
                    _persist_upload(filepath, file_bytes)

                    # Create database record
                    image = Image(
                        filename=filename,
                        file_path=str(filepath),
                        width=width,
                        height=height,
                        is_public=True,
                    )
                    db.session.add(image)
                    db.session.flush()

                    # Attach to album
                    if album_id:
                        album = db.session.get(Album, album_id)
                        if album:
                            sort_order = len(album.album_images) + 1
                            assoc = AlbumImage(
                                album_id=album.id,
                                image_id=image.id,
                                sort_order=sort_order,
                                added_by=added_by,
                            )
                            db.session.add(assoc)

                    uploaded_images.append(
                        {
                            "id": image.id,
                            "filename": image.filename,
                            "width": image.width,
                            "height": image.height,
                        }
                    )

                except Exception as exc:
                    logger.error(
                        f"Error processing file {file_data.get('filename')}: {exc}",
                        exc_info=True,
                    )
                    failed_files.append(
                        {
                            "filename": file_data.get("filename", "unknown"),
                            "error": str(exc),
                        }
                    )

            db.session.commit()

            return {
                "success": True,
                "uploaded": len(uploaded_images),
                "failed": len(failed_files),
                "images": uploaded_images,
                "failures": failed_files,
            }

        except Exception as exc:
            logger.error(f"Bulk upload task failed: {exc}", exc_info=True)
            db.session.rollback()
            return {
                "success": False,
                "error": str(exc),
                "uploaded": 0,
                "failed": total_files,
            }
