"""
Album management endpoints
"""

from flask import Blueprint, jsonify, request

from server.auth import current_user, require_admin
from server.database import Album, AlbumImage, db

albums_bp = Blueprint("albums", __name__, url_prefix="/api/albums")


@albums_bp.route("", methods=["GET"])
def list_albums():
    """List all albums (public)"""
    albums = Album.query.order_by(Album.created_at.desc()).all()
    return jsonify({"albums": [album.to_dict() for album in albums]})


@albums_bp.route("/<int:album_id>", methods=["GET"])
def get_album(album_id):
    """Get album details with images (public)"""
    album = Album.query.get_or_404(album_id)
    return jsonify(album.to_dict(include_images=True))


@albums_bp.route("", methods=["POST"])
@require_admin
def create_album():
    """Create new album (admin only)"""
    data = request.json

    album = Album(
        name=data["name"],
        description=data.get("description", ""),
        is_training_source=data.get("is_training_source", False),
        created_by=current_user.email,
    )

    db.session.add(album)
    db.session.commit()

    return jsonify(album.to_dict()), 201


@albums_bp.route("/<int:album_id>", methods=["PUT"])
@require_admin
def update_album(album_id):
    """Update album (admin only)"""
    album = Album.query.get_or_404(album_id)
    data = request.json

    if "name" in data:
        album.name = data["name"]
    if "description" in data:
        album.description = data["description"]
    if "is_training_source" in data:
        album.is_training_source = data["is_training_source"]
    if "cover_image_id" in data:
        album.cover_image_id = data["cover_image_id"]

    db.session.commit()

    return jsonify(album.to_dict())


@albums_bp.route("/<int:album_id>", methods=["DELETE"])
@require_admin
def delete_album(album_id):
    """Delete album (admin only)"""
    album = Album.query.get_or_404(album_id)

    db.session.delete(album)
    db.session.commit()

    return jsonify({"success": True})


@albums_bp.route("/<int:album_id>/images", methods=["POST"])
@require_admin
def add_images_to_album(album_id):
    """Add images to album (admin only)"""
    # Verify album exists
    Album.query.get_or_404(album_id)
    data = request.json

    image_ids = data.get("image_ids", [])

    for image_id in image_ids:
        # Check if already in album
        existing = AlbumImage.query.filter_by(album_id=album_id, image_id=image_id).first()

        if not existing:
            assoc = AlbumImage(album_id=album_id, image_id=image_id, added_by=current_user.email)
            db.session.add(assoc)

    db.session.commit()

    return jsonify({"success": True, "added": len(image_ids)})


@albums_bp.route("/<int:album_id>/images/<int:image_id>", methods=["DELETE"])
@require_admin
def remove_image_from_album(album_id, image_id):
    """Remove image from album (admin only)"""
    assoc = AlbumImage.query.filter_by(album_id=album_id, image_id=image_id).first_or_404()

    db.session.delete(assoc)
    db.session.commit()

    return jsonify({"success": True})
