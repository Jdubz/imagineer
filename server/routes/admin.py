"""
Administrative endpoints for configuration and resource management.
"""

from __future__ import annotations

import logging

from flask import Blueprint, abort, jsonify, request
from flask_login import current_user

from server.auth import ROLE_ADMIN, load_users, require_admin, save_users
from server.config_loader import clear_config_cache, get_cache_stats, load_config
from server.database import Album, Image, db
from server.utils.disk_stats import collect_disk_statistics

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _get_image_or_abort(image_id: int) -> Image:
    image = db.session.get(Image, image_id)
    if image is None:
        abort(404, description="Image not found")
    return image


@admin_bp.route("/config/cache", methods=["GET"])
@require_admin
def get_config_cache_stats():
    """Return configuration cache statistics (admin only)."""
    try:
        stats = get_cache_stats()
        return jsonify(stats)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error getting cache stats: %s", exc, exc_info=True)
        return jsonify({"error": "Failed to get cache statistics"}), 500


@admin_bp.route("/config/reload", methods=["POST"])
@require_admin
def reload_config_cache():
    """Force configuration reload from disk (admin only)."""
    try:
        clear_config_cache()
        load_config(force_reload=True)

        logger.info(
            "Configuration reloaded by admin",
            extra={
                "operation": "config_reload",
                "user": current_user.email if current_user.is_authenticated else "unknown",
            },
        )

        return jsonify(
            {
                "success": True,
                "message": "Configuration reloaded from disk",
                "cache_stats": get_cache_stats(),
            }
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error reloading config: %s", exc, exc_info=True)
        return jsonify({"error": "Failed to reload configuration"}), 500


@admin_bp.route("/disk-stats", methods=["GET"])
@require_admin
def get_disk_statistics_admin():
    """Return disk usage statistics for key application directories."""
    try:
        stats = collect_disk_statistics()
        return jsonify(stats)
    except FileNotFoundError as exc:
        logger.warning("admin.disk_stats.missing_path", extra={"error": str(exc)})
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("admin.disk_stats.failure", extra={"error": str(exc)}, exc_info=True)
        return jsonify({"error": "Failed to collect disk statistics"}), 500


@admin_bp.route("/users", methods=["GET"])
@require_admin
def get_admin_users():
    """Return all users (admin only)."""
    try:
        logger.info(
            "Admin accessing user list",
            extra={
                "operation": "admin_get_users",
                "user_id": current_user.email if current_user.is_authenticated else "unknown",
            },
        )
        users = load_users()

        user_count = len([u for u in users.values() if isinstance(u, dict)])
        logger.info(
            "Retrieved %s users for admin",
            user_count,
            extra={"operation": "admin_get_users", "user_count": user_count},
        )

        return jsonify(users)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(
            "Error getting users: %s",
            exc,
            exc_info=True,
            extra={"operation": "admin_get_users", "error_type": type(exc).__name__},
        )
        return jsonify({"error": "Failed to get users"}), 500


@admin_bp.route("/users/<email>", methods=["PUT"])
@require_admin
def update_user_role(email: str):
    """Update user role (admin only)."""
    try:
        data = request.json
        if not data or "role" not in data:
            return jsonify({"error": "role field is required"}), 400

        role = data["role"]
        if role not in [None, ROLE_ADMIN]:
            return jsonify({"error": "Invalid role. Must be null (public) or 'admin'"}), 400

        users = load_users()
        if email not in users:
            users[email] = {}

        users[email]["role"] = role
        save_users(users)

        return jsonify(
            {"success": True, "message": f"Updated user {email} role to {role or 'public'}"}
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error updating user role: %s", exc, exc_info=True)
        return jsonify({"error": "Failed to update user role"}), 500


@admin_bp.route("/images", methods=["GET"])
@require_admin
def get_admin_images():
    """Return all images including private ones (admin only)."""
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)

        images = Image.query.order_by(Image.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify(
            {
                "images": [image.to_dict() for image in images.items],
                "total": images.total,
                "pages": images.pages,
                "current_page": page,
                "per_page": per_page,
            }
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error getting admin images: %s", exc, exc_info=True)
        return jsonify({"error": "Failed to get images"}), 500


@admin_bp.route("/images/<int:image_id>/visibility", methods=["PUT"])
@require_admin
def update_image_visibility(image_id: int):
    """Update image visibility (admin only)."""
    try:
        data = request.json
        if not data or "is_public" not in data:
            return jsonify({"error": "is_public field is required"}), 400

        image = _get_image_or_abort(image_id)
        image.is_public = bool(data["is_public"])
        db.session.commit()

        visibility = "public" if image.is_public else "private"
        return jsonify({"success": True, "message": f"Updated image visibility to {visibility}"})
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error updating image visibility: %s", exc, exc_info=True)
        return jsonify({"error": "Failed to update image visibility"}), 500


@admin_bp.route("/albums", methods=["GET"])
@require_admin
def get_admin_albums():
    """Return all albums including private ones (admin only)."""
    try:
        albums = Album.query.order_by(Album.created_at.desc()).all()
        return jsonify([album.to_dict() for album in albums])
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error getting admin albums: %s", exc, exc_info=True)
        return jsonify({"error": "Failed to get albums"}), 500
