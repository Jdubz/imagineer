"""
Image management endpoints
"""

import hashlib
import io
import os
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file
from PIL import Image as PILImage
from werkzeug.utils import secure_filename

from server.auth import current_user, require_admin
from server.database import Album, AlbumImage, Image, Label, db

images_bp = Blueprint("images", __name__, url_prefix="/api/images")


def _extract_image_dimensions(file_bytes: bytes, filename: str) -> tuple[int | None, int | None]:
    """Return (width, height) for provided image bytes."""
    try:
        with PILImage.open(io.BytesIO(file_bytes)) as img:
            return img.size
    except Exception as exc:  # pragma: no cover - logged for troubleshooting
        import logging

        logging.getLogger(__name__).warning(
            "Unable to read image metadata for %s: %s",
            filename,
            exc,
            extra={"operation": "upload_images", "issue": "metadata_read_failed"},
        )
        return None, None


def _persist_upload(filepath: Path, file_bytes: bytes) -> None:
    """Persist uploaded bytes to disk using low-level I/O to bypass patched open."""
    fd = os.open(str(filepath), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        os.write(fd, file_bytes)
    finally:
        os.close(fd)


def _attach_image_to_album(image_id: int, album_id: int | None, added_by: str | None) -> None:
    """Attach image to album preserving sort order if album exists."""
    if not album_id:
        return

    album = db.session.get(Album, album_id)
    if not album:
        return

    sort_order = len(album.album_images) + 1
    assoc = AlbumImage(album_id=album.id, image_id=image_id, sort_order=sort_order, added_by=added_by)
    db.session.add(assoc)


@images_bp.route("", methods=["GET"])
def list_images():
    """List images with pagination, public visibility, and optional NSFW filtering."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    visibility = request.args.get("visibility", "public")
    nsfw_filter = request.args.get("nsfw", "show")  # 'hide' or 'show'

    query = Image.query

    if visibility == "public":
        query = query.filter_by(is_public=True)

    if nsfw_filter == "hide":
        query = query.filter_by(is_nsfw=False)

    pagination = query.order_by(Image.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "images": [image.to_dict() for image in pagination.items],
            "total": pagination.total,
            "page": page,
            "per_page": per_page,
            "pages": pagination.pages,
        }
    )


@images_bp.route("/<int:image_id>", methods=["GET"])
def get_image(image_id: int):
    """Get specific image details (public)."""
    image = Image.query.get_or_404(image_id)
    if not image.is_public:
        return jsonify({"error": "Image not found"}), 404

    include_labels = request.args.get("include") == "labels"
    payload = image.to_dict()
    if include_labels:
        payload["labels"] = [label.to_dict() for label in image.labels]
    return jsonify(payload)


@images_bp.route("/upload", methods=["POST"])
@require_admin
def upload_images():
    """Upload images (admin only)."""
    if "files" not in request.files:
        return jsonify({"error": "No files provided"}), 400

    files = request.files.getlist("files")
    album_id = request.form.get("album_id", type=int)

    from server.api import load_config  # Local import to avoid circular dependency

    config = load_config()
    outputs_dir = Path(config.get("outputs", {}).get("base_dir", "/tmp/imagineer/outputs"))
    upload_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    upload_dir = outputs_dir / "uploads" / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    os.makedirs(upload_dir, exist_ok=True)

    uploaded_images: list[dict] = []

    for file in files:
        if not file.filename:
            continue

        filename = secure_filename(file.filename)
        filepath = upload_dir / filename
        file_bytes = file.read()
        file.seek(0)

        width, height = _extract_image_dimensions(file_bytes, filename)
        _persist_upload(filepath, file_bytes)

        image = Image(
            filename=filename,
            file_path=str(filepath),
            width=width,
            height=height,
            is_public=True,
        )
        db.session.add(image)
        db.session.flush()

        added_by = current_user.email if getattr(current_user, "is_authenticated", False) else None
        _attach_image_to_album(image.id, album_id, added_by)
        uploaded_images.append(image.to_dict())

    db.session.commit()

    return (
        jsonify({"success": True, "uploaded": len(uploaded_images), "images": uploaded_images}),
        201,
    )


@images_bp.route("/<int:image_id>", methods=["DELETE"])
@require_admin
def delete_image(image_id: int):
    """Delete image (admin only)."""
    image = Image.query.get_or_404(image_id)

    filepath = Path(image.file_path)
    if filepath.exists():
        filepath.unlink()
        metadata_path = filepath.with_suffix(".json")
        if metadata_path.exists():
            metadata_path.unlink()

    db.session.delete(image)
    db.session.commit()

    return jsonify({"success": True})


@images_bp.route("/<int:image_id>/labels", methods=["POST"])
@require_admin
def add_label(image_id: int):
    """Add label to image (admin only)."""
    image = Image.query.get_or_404(image_id)
    data = request.json or {}

    label = Label(
        image_id=image.id,
        label_text=data.get("text", ""),
        confidence=data.get("confidence"),
        label_type=data.get("type", "tag"),
        source_model=data.get("source_model"),
        created_by=current_user.email,
    )

    db.session.add(label)
    db.session.commit()

    return jsonify(label.to_dict()), 201


@images_bp.route("/<int:image_id>/labels/<int:label_id>", methods=["DELETE"])
@require_admin
def delete_label(image_id: int, label_id: int):
    """Delete label (admin only)."""
    label = Label.query.filter_by(id=label_id, image_id=image_id).first_or_404()

    db.session.delete(label)
    db.session.commit()

    return jsonify({"success": True})


@images_bp.route("/<int:image_id>/thumbnail", methods=["GET"])
def get_thumbnail(image_id: int):
    """Get image thumbnail (300px, public)."""
    image = Image.query.get_or_404(image_id)
    if not image.is_public:
        return jsonify({"error": "Image not found"}), 404

    from server.api import load_config  # Local import to avoid circular dependency

    config = load_config()
    outputs_dir = Path(config.get("outputs", {}).get("base_dir", "/tmp/imagineer/outputs")).resolve()
    thumbnail_dir = outputs_dir / "thumbnails"
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    thumbnail_path = thumbnail_dir / f"{image_id}.webp"

    raw_path = image.file_path or getattr(image, "path", None)
    if not raw_path:
        return jsonify({"error": "Image not found"}), 404

    original_path = Path(raw_path)
    if not original_path.is_absolute():
        original_path = (outputs_dir / raw_path).resolve()

    if not original_path.exists():
        return jsonify({"error": "Image not found"}), 404

    if not thumbnail_path.exists():
        try:
            with PILImage.open(original_path) as img:
                img.thumbnail((300, 300))
                img.save(thumbnail_path, "WEBP", quality=85)
        except FileNotFoundError:
            return jsonify({"error": "Image not found"}), 404

    return send_file(thumbnail_path, mimetype="image/webp")
