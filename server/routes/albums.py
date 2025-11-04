"""
Album management endpoints
"""

import json
from typing import Any

from flask import Blueprint, abort, jsonify, request
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from server.auth import current_user, require_admin
from server.database import Album, AlbumImage, Image, Label, db

albums_bp = Blueprint("albums", __name__, url_prefix="/api/albums")


def _is_admin_user() -> bool:
    try:
        return bool(current_user.is_authenticated and current_user.is_admin())
    except Exception:  # pragma: no cover
        return False


def _load_album_or_abort(album_id: int, options: Any | None = None) -> Album:
    query = db.session.query(Album)
    if options:
        if isinstance(options, (list, tuple)):
            for option in options:
                query = query.options(option)
        else:
            query = query.options(options)
    album = query.filter(Album.id == album_id).one_or_none()
    if album is None:
        abort(404, description="Album not found")
    return album


@albums_bp.route("", methods=["GET"])
def list_albums():
    """List all albums (public, with pagination)"""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 100)
    preview_limit = min(request.args.get("preview_limit", 5, type=int), 10)

    query = Album.query.options(
        joinedload(Album.album_images).joinedload(AlbumImage.image)
    ).order_by(Album.created_at.desc())

    album_type = request.args.get("album_type")
    if album_type:
        query = query.filter(Album.album_type == album_type)

    is_set_template_param = request.args.get("is_set_template")
    if is_set_template_param is not None:
        lowered = is_set_template_param.strip().lower()
        filter_value = lowered in {"1", "true", "yes", "on"}
        query = query.filter(Album.is_set_template.is_(filter_value))

    pagination = query.paginate(page=page, per_page=per_page)

    albums_data = []
    for album in pagination.items:
        album_dict = album.to_dict()
        # Add preview images (limited number for thumbnails)
        preview_images = []
        for association in album.album_images[:preview_limit]:
            if association.image:
                preview_images.append(
                    {
                        "id": association.image.id,
                        "filename": association.image.filename,
                        "thumbnail_path": association.image.thumbnail_path,
                    }
                )
        album_dict["preview_images"] = preview_images
        albums_data.append(album_dict)

    return jsonify(
        {
            "albums": albums_data,
            "total": pagination.total,
            "page": page,
            "per_page": per_page,
            "pages": pagination.pages,
        }
    )


@albums_bp.route("/<int:album_id>", methods=["GET"])
def get_album(album_id):
    """Get album details with images (public)"""
    include_param = request.args.get("include_labels")
    include_labels = False
    if isinstance(include_param, str):
        include_labels = include_param.lower() not in {"0", "false", "no"}

    loader = joinedload(Album.album_images).joinedload(AlbumImage.image)
    if include_labels:
        loader = loader.joinedload(Image.labels)

    album = _load_album_or_abort(album_id, loader)
    if not album.is_public and not _is_admin_user():
        # Avoid leaking the existence of private albums to anonymous users
        abort(404)
    album_data = album.to_dict()
    images_payload: list[dict] = []

    include_sensitive = _is_admin_user()

    for association in album.album_images:
        image = association.image
        if not image:
            continue

        image_payload = image.to_dict(include_sensitive=include_sensitive)

        labels = image.labels or []
        image_payload["labels"] = [label.to_dict() for label in labels]

        if include_labels:
            image_payload["label_count"] = len(labels)
            image_payload["manual_label_count"] = sum(
                1 for label in labels if (label.label_type or "").lower() in {"manual", "user"}
            )

        images_payload.append(image_payload)

    album_data["images"] = images_payload
    return jsonify(album_data)


@albums_bp.route("/<int:album_id>/labeling/analytics", methods=["GET"])
@require_admin
def album_labeling_analytics(album_id: int):
    """Return aggregated labeling statistics for an album (admin only)."""
    album = _load_album_or_abort(
        album_id, joinedload(Album.album_images).joinedload(AlbumImage.image)
    )

    image_ids = [association.image_id for association in album.album_images if association.image_id]
    distinct_image_ids = list({image_id for image_id in image_ids if image_id is not None})
    image_count = len(distinct_image_ids)

    if image_count == 0:
        return jsonify(
            {
                "album_id": album.id,
                "image_count": 0,
                "labels_total": 0,
                "labels_by_type": {},
                "images_with_labels": 0,
                "images_with_manual_labels": 0,
                "images_with_captions": 0,
                "unlabeled_images": 0,
                "average_labels_per_image": 0.0,
                "coverage": {
                    "labels_percent": 0.0,
                    "manual_percent": 0.0,
                    "caption_percent": 0.0,
                },
                "top_tags": [],
                "last_labeled_at": None,
            }
        )

    base_filter = Label.image_id.in_(distinct_image_ids)

    labels_by_type_rows = (
        db.session.query(Label.label_type, func.count())
        .filter(base_filter)
        .group_by(Label.label_type)
        .all()
    )
    labels_by_type: dict[str, int] = {}
    total_labels = 0
    for label_type, count in labels_by_type_rows:
        key = (label_type or "unknown").lower()
        labels_by_type[key] = count
        total_labels += count

    images_with_labels = (
        db.session.query(func.count(func.distinct(Label.image_id))).filter(base_filter).scalar()
        or 0
    )
    images_with_manual = (
        db.session.query(func.count(func.distinct(Label.image_id)))
        .filter(
            base_filter,
            Label.label_type.in_(("manual", "user")),
        )
        .scalar()
        or 0
    )
    images_with_captions = (
        db.session.query(func.count(func.distinct(Label.image_id)))
        .filter(base_filter, Label.label_type == "caption")
        .scalar()
        or 0
    )

    unlabeled_images = max(0, image_count - images_with_labels)
    average_labels = total_labels / image_count if image_count else 0.0

    top_tags_rows = (
        db.session.query(Label.label_text, func.count().label("count"))
        .filter(
            base_filter,
            Label.label_text.isnot(None),
            Label.label_text != "",
            Label.label_type.in_(("tag", "manual", "user")),
        )
        .group_by(Label.label_text)
        .order_by(func.count().desc())
        .limit(10)
        .all()
    )
    top_tags = [{"label_text": text, "count": count} for text, count in top_tags_rows]

    last_labeled_at = db.session.query(func.max(Label.created_at)).filter(base_filter).scalar()

    def _percent(part: int) -> float:
        return round((part / image_count) * 100.0, 2) if image_count else 0.0

    return jsonify(
        {
            "album_id": album.id,
            "image_count": image_count,
            "labels_total": total_labels,
            "labels_by_type": labels_by_type,
            "images_with_labels": images_with_labels,
            "images_with_manual_labels": images_with_manual,
            "images_with_captions": images_with_captions,
            "unlabeled_images": unlabeled_images,
            "average_labels_per_image": round(average_labels, 2),
            "coverage": {
                "labels_percent": _percent(images_with_labels),
                "manual_percent": _percent(images_with_manual),
                "caption_percent": _percent(images_with_captions),
            },
            "top_tags": top_tags,
            "last_labeled_at": last_labeled_at.isoformat() if last_labeled_at else None,
        }
    )


@albums_bp.route("", methods=["POST"])
@require_admin
def create_album():
    """Create new album (admin only)"""
    data = request.json
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid payload"}), 400

    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Album name is required"}), 400

    album_type = (data.get("album_type") or "batch").strip() or "batch"
    is_set_template = bool(data.get("is_set_template", False))

    album = Album(
        name=name,
        description=data.get("description", ""),
        album_type=album_type,
        is_training_source=data.get("is_training_source", False),
        is_public=data.get("is_public", True),
        created_by=current_user.email,
        is_set_template=is_set_template,
    )

    _apply_template_fields(album, data)

    db.session.add(album)
    db.session.commit()

    return jsonify(album.to_dict()), 201


@albums_bp.route("/<int:album_id>", methods=["PUT"])
@require_admin
def update_album(album_id):
    """Update album (admin only)"""
    album = _load_album_or_abort(album_id)
    data = request.json

    if "name" in data:
        album.name = data["name"]
    if "description" in data:
        album.description = data["description"]
    if "is_training_source" in data:
        album.is_training_source = data["is_training_source"]
    if "is_public" in data:
        album.is_public = data["is_public"]
    if "album_type" in data:
        album.album_type = (data.get("album_type") or "").strip() or album.album_type
    if "is_set_template" in data:
        album.is_set_template = bool(data["is_set_template"])
    _apply_template_fields(album, data)
    if "cover_image_id" in data:
        album.cover_image_id = data["cover_image_id"]

    db.session.commit()

    return jsonify(album.to_dict())


@albums_bp.route("/<int:album_id>", methods=["DELETE"])
@require_admin
def delete_album(album_id):
    """Delete album (admin only)"""
    album = _load_album_or_abort(album_id)

    db.session.delete(album)
    db.session.commit()

    return jsonify({"success": True})


def _normalize_template_payload(value: Any) -> str | None:
    """Normalise template JSON payloads."""
    if value is None or value == "":
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value)


def _apply_template_fields(album: Album, data: dict[str, Any]) -> None:
    """Apply set-template metadata to an album instance."""
    template_fields = {
        "csv_data": _normalize_template_payload(data.get("csv_data")),
        "base_prompt": data.get("base_prompt"),
        "prompt_template": data.get("prompt_template"),
        "style_suffix": data.get("style_suffix"),
        "example_theme": data.get("example_theme"),
        "lora_config": _normalize_template_payload(data.get("lora_config")),
        "generation_config": _normalize_template_payload(data.get("generation_config")),
    }

    for field, value in template_fields.items():
        if value is not None or field in data:
            setattr(album, field, value)


@albums_bp.route("/<int:album_id>/images", methods=["POST"])
@require_admin
def add_images_to_album(album_id):
    """Add images to album (admin only)"""
    # Verify album exists
    _load_album_or_abort(album_id)
    data = request.json

    image_ids = data.get("image_ids", [])
    added_count = 0
    for image_id in image_ids:
        # Check if already in album
        existing = AlbumImage.query.filter_by(album_id=album_id, image_id=image_id).first()

        if not existing:
            assoc = AlbumImage(album_id=album_id, image_id=image_id, added_by=current_user.email)
            db.session.add(assoc)
            added_count += 1

    db.session.commit()

    return jsonify({"success": True, "added_count": added_count})


@albums_bp.route("/<int:album_id>/images/<int:image_id>", methods=["DELETE"])
@require_admin
def remove_image_from_album(album_id, image_id):
    """Remove image from album (admin only)"""
    assoc = AlbumImage.query.filter_by(album_id=album_id, image_id=image_id).first_or_404()

    db.session.delete(assoc)
    db.session.commit()

    return jsonify({"success": True})
