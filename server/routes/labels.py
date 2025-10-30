"""
Analytics endpoints for image labels.
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request
from sqlalchemy import case, func

from server.auth import current_user, require_admin
from server.database import Album, AlbumImage, Image, Label, db

labels_bp = Blueprint("labels", __name__)
logger = logging.getLogger(__name__)


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _parse_label_types() -> list[str] | None:
    raw = request.args.get("label_type")
    if raw is None or raw == "":
        return None
    if "," in raw:
        return [part.strip() for part in raw.split(",") if part.strip()]
    return [raw.strip()]


def _filtered_label_query(label_types: list[str] | None, album_id: int | None, public_only: bool):
    query = db.session.query(Label)

    if album_id is not None:
        query = query.join(AlbumImage, AlbumImage.image_id == Label.image_id).filter(
            AlbumImage.album_id == album_id
        )

    if public_only:
        query = query.join(Image, Image.id == Label.image_id).filter(Image.is_public.is_(True))

    if label_types:
        query = query.filter(Label.label_type.in_(label_types))

    return query


def _image_scope_query(album_id: int | None, public_only: bool):
    query = db.session.query(Image.id)
    if album_id is not None:
        query = query.join(AlbumImage).filter(AlbumImage.album_id == album_id)
    if public_only:
        query = query.filter(Image.is_public.is_(True))
    return query.distinct()


@labels_bp.route("/api/labels/stats", methods=["GET"])
@require_admin
def label_stats():
    """Return aggregate statistics about labels."""
    logger.info(
        "labels.stats.requested",
        extra={"user": getattr(current_user, "email", None)},
    )

    label_types = _parse_label_types()
    album_id = request.args.get("album_id", type=int)
    public_only = _parse_bool(request.args.get("public_only"), default=False)
    top_limit = request.args.get("top_limit", default=10, type=int)
    top_limit = max(1, min(top_limit, 100))

    label_query = _filtered_label_query(label_types, album_id, public_only)

    total_labels = label_query.count()

    unique_labels = (
        label_query.with_entities(
            func.count(func.distinct(func.lower(func.trim(Label.label_text))))
        ).scalar()
        or 0
    )

    labels_per_image_subq = (
        label_query.with_entities(
            Label.image_id.label("image_id"), func.count(Label.id).label("label_count")
        )
        .group_by(Label.image_id)
        .subquery()
    )

    images_with_labels = (
        db.session.query(func.count()).select_from(labels_per_image_subq).scalar() or 0
    )

    avg_labels_per_image = (
        round(total_labels / images_with_labels, 2) if images_with_labels else 0.0
    )

    image_scope_count = _image_scope_query(album_id, public_only).count()
    label_coverage_percent = (
        round(images_with_labels / image_scope_count * 100, 2) if image_scope_count else 0.0
    )

    by_type_rows = (
        _filtered_label_query(None, album_id, public_only)
        .with_entities(Label.label_type, func.count(Label.id))
        .group_by(Label.label_type)
        .order_by(func.count(Label.id).desc())
        .all()
    )

    by_type = {label_type or "unknown": count for label_type, count in by_type_rows}

    normalized_label = func.lower(func.trim(Label.label_text))
    top_tags_rows = (
        label_query.with_entities(
            normalized_label.label("tag"), func.count(Label.id).label("count")
        )
        .group_by(normalized_label)
        .order_by(func.count(Label.id).desc())
        .limit(top_limit)
        .all()
    )

    top_tags = [
        {
            "tag": tag or "",
            "count": count,
            "percentage": round(count / total_labels * 100, 2) if total_labels else 0.0,
        }
        for tag, count in top_tags_rows
    ]

    return jsonify(
        {
            "total_labels": total_labels,
            "unique_labels": unique_labels,
            "avg_labels_per_image": avg_labels_per_image,
            "images_with_labels": images_with_labels,
            "total_images": image_scope_count,
            "label_coverage_percent": label_coverage_percent,
            "by_type": by_type,
            "top_tags": top_tags,
        }
    )


@labels_bp.route("/api/labels/top-tags", methods=["GET"])
@require_admin
def label_top_tags():
    """Return the most frequent label texts."""

    label_types = _parse_label_types()
    album_id = request.args.get("album_id", type=int)
    public_only = _parse_bool(request.args.get("public_only"), default=False)
    limit = request.args.get("limit", default=50, type=int)
    limit = max(1, min(limit, 200))
    min_count = request.args.get("min_count", default=1, type=int)
    min_count = max(1, min_count)

    label_query = _filtered_label_query(label_types, album_id, public_only)
    total_labels = label_query.count()

    normalized_label = func.lower(func.trim(Label.label_text))
    rows = (
        label_query.with_entities(
            normalized_label.label("tag"), func.count(Label.id).label("count")
        )
        .group_by(normalized_label)
        .having(func.count(Label.id) >= min_count)
        .order_by(func.count(Label.id).desc())
        .limit(limit)
        .all()
    )

    tags = [
        {
            "tag": tag or "",
            "count": count,
            "percentage": round(count / total_labels * 100, 2) if total_labels else 0.0,
        }
        for tag, count in rows
    ]

    return jsonify({"total_labels": total_labels, "results": tags})


@labels_bp.route("/api/labels/distribution", methods=["GET"])
@require_admin
def label_distribution():
    """Return label distribution grouped by album."""

    label_types = _parse_label_types()
    public_only = _parse_bool(request.args.get("public_only"), default=False)
    page = max(1, request.args.get("page", default=1, type=int))
    page_size = request.args.get("page_size", default=20, type=int)
    page_size = max(1, min(page_size, 100))

    sort_field = request.args.get("sort", default="label_count")
    sort_dir = request.args.get("direction", default="desc").lower()
    sort_desc = sort_dir != "asc"

    query = (
        db.session.query(
            Album.id.label("album_id"),
            Album.name.label("album_name"),
            func.count(func.distinct(Image.id)).label("image_count"),
            func.count(Label.id).label("label_count"),
            func.count(
                func.distinct(
                    case(
                        (Label.id.isnot(None), Image.id),
                        else_=None,
                    )
                )
            ).label("images_with_labels"),
        )
        .join(AlbumImage, AlbumImage.album_id == Album.id)
        .join(Image, Image.id == AlbumImage.image_id)
        .outerjoin(Label, Label.image_id == Image.id)
    )

    if public_only:
        query = query.filter(Image.is_public.is_(True))

    if label_types:
        query = query.filter(Label.label_type.in_(label_types))

    grouped = query.group_by(Album.id, Album.name)
    total_albums = grouped.count()

    sort_columns = {
        "album": Album.name,
        "album_name": Album.name,
        "image_count": func.count(func.distinct(Image.id)),
        "label_count": func.count(Label.id),
        "images_with_labels": func.count(
            func.distinct(
                case(
                    (Label.id.isnot(None), Image.id),
                    else_=None,
                )
            )
        ),
    }

    sort_column = sort_columns.get(sort_field, sort_columns["label_count"])
    if sort_desc:
        grouped = grouped.order_by(sort_column.desc())
    else:
        grouped = grouped.order_by(sort_column.asc())

    results = grouped.offset((page - 1) * page_size).limit(page_size).all() if total_albums else []

    payload = []
    for row in results:
        images_with_labels = row.images_with_labels or 0
        image_count = row.image_count or 0
        label_count = row.label_count or 0
        coverage = round(images_with_labels / image_count * 100, 2) if image_count else 0.0
        avg_labels = round(label_count / images_with_labels, 2) if images_with_labels else 0.0
        payload.append(
            {
                "album_id": row.album_id,
                "album_name": row.album_name,
                "label_count": label_count,
                "image_count": image_count,
                "images_with_labels": images_with_labels,
                "label_coverage_percent": coverage,
                "avg_labels_per_labeled_image": avg_labels,
            }
        )

    return jsonify(
        {
            "page": page,
            "page_size": page_size,
            "total_albums": total_albums,
            "results": payload,
        }
    )
