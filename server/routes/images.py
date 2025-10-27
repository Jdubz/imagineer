"""
Image management endpoints
"""

import hashlib
import io
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file
from PIL import Image as PILImage
from werkzeug.utils import secure_filename

from server.auth import current_user, require_admin
from server.database import Image, Label, db

images_bp = Blueprint("images", __name__, url_prefix="/api/images")


@images_bp.route("", methods=["GET"])
def list_images():
    """List all images (public, with pagination)"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    nsfw_filter = request.args.get("nsfw", "blur")  # 'hide', 'blur', 'show'

    query = Image.query

    # Filter NSFW if requested
    if nsfw_filter == "hide":
        query = query.filter_by(nsfw_flag=False)

    # Order by newest first
    query = query.order_by(Image.created_at.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page)

    return jsonify(
        {
            "images": [img.to_dict() for img in pagination.items],
            "total": pagination.total,
            "page": page,
            "per_page": per_page,
            "pages": pagination.pages,
        }
    )


@images_bp.route("/<int:image_id>", methods=["GET"])
def get_image(image_id):
    """Get image details (public)"""
    image = Image.query.get_or_404(image_id)
    return jsonify(image.to_dict(include_labels=True))


@images_bp.route("/upload", methods=["POST"])
@require_admin
def upload_images():
    """Upload images (admin only)"""
    if "files" not in request.files:
        return jsonify({"error": "No files provided"}), 400

    files = request.files.getlist("files")
    album_id = request.form.get("album_id", type=int)

    # Create upload directory
    from datetime import datetime

    upload_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    upload_dir = Path(f"/mnt/speedy/imagineer/outputs/uploads/{upload_id}")
    upload_dir.mkdir(parents=True, exist_ok=True)

    uploaded_images = []

    for file in files:
        if file.filename == "":
            continue

        # Save file
        filename = secure_filename(file.filename)
        filepath = upload_dir / filename
        file.save(filepath)

        # Get image dimensions
        with PILImage.open(filepath) as img:
            width, height = img.size

        # Calculate checksum
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        checksum = sha256.hexdigest()

        # Create database record
        image = Image(
            filename=filename,
            path=str(filepath),
            source_type="upload",
            source_id=upload_id,
            width=width,
            height=height,
            file_size=filepath.stat().st_size,
            checksum=checksum,
        )

        db.session.add(image)
        db.session.flush()  # Get image.id

        # Add to album if specified
        if album_id:
            from server.database import AlbumImage

            assoc = AlbumImage(album_id=album_id, image_id=image.id, added_by=current_user.email)
            db.session.add(assoc)

        uploaded_images.append(image.to_dict())

    db.session.commit()

    return (
        jsonify({"success": True, "uploaded": len(uploaded_images), "images": uploaded_images}),
        201,
    )


@images_bp.route("/<int:image_id>", methods=["DELETE"])
@require_admin
def delete_image(image_id):
    """Delete image (admin only)"""
    image = Image.query.get_or_404(image_id)

    # Delete file from filesystem
    filepath = Path(image.path)
    if filepath.exists():
        filepath.unlink()

        # Also delete metadata JSON if exists
        json_path = filepath.with_suffix(".json")
        if json_path.exists():
            json_path.unlink()

    # Delete from database (cascade deletes labels and album associations)
    db.session.delete(image)
    db.session.commit()

    return jsonify({"success": True})


@images_bp.route("/<int:image_id>/labels", methods=["POST"])
@require_admin
def add_label(image_id):
    """Add label to image (admin only)"""
    image = Image.query.get_or_404(image_id)
    data = request.json

    label = Label(
        image_id=image.id,
        label_text=data["text"],
        confidence=data.get("confidence"),
        label_type=data.get("type", "tag"),
        source=data.get("source", "manual"),
        created_by=current_user.email,
    )

    db.session.add(label)
    db.session.commit()

    return jsonify(label.to_dict()), 201


@images_bp.route("/<int:image_id>/labels/<int:label_id>", methods=["DELETE"])
@require_admin
def delete_label(image_id, label_id):
    """Delete label (admin only)"""
    label = Label.query.filter_by(id=label_id, image_id=image_id).first_or_404()

    db.session.delete(label)
    db.session.commit()

    return jsonify({"success": True})


# Thumbnail generation endpoint
@images_bp.route("/<int:image_id>/thumbnail", methods=["GET"])
def get_thumbnail(image_id):
    """Get image thumbnail (300px, public)"""
    image = Image.query.get_or_404(image_id)

    # Check for cached thumbnail
    thumbnail_dir = Path("/mnt/speedy/imagineer/outputs/thumbnails")
    thumbnail_dir.mkdir(exist_ok=True)
    thumbnail_path = thumbnail_dir / f"{image_id}.webp"

    if not thumbnail_path.exists():
        # Generate thumbnail
        with PILImage.open(image.path) as img:
            img.thumbnail((300, 300))
            img.save(thumbnail_path, "WEBP", quality=85)

    return send_file(thumbnail_path, mimetype="image/webp")
