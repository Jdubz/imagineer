"""
Celery tasks for AI labeling using Claude vision.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from server.celery_app import celery
from server.constants import NSFW_BLUR_RATINGS
from server.database import Album, AlbumImage, Image, Label, db

logger = logging.getLogger(__name__)


def _apply_label_results(image: Image, result: Dict[str, Any]) -> None:
    """
    Persist labeling results for a single image.

    Args:
        image: Image instance being labeled.
        result: Result dictionary from the labeling service.
    """

    # Update NSFW flag based on rating (boolean: blur or not)
    image.is_nsfw = result.get("nsfw_rating") in NSFW_BLUR_RATINGS

    # Persist caption if provided
    description = result.get("description")
    if description:
        db.session.add(
            Label(
                image_id=image.id,
                label_text=description,
                label_type="caption",
                source_model="claude-3-5-sonnet",
            )
        )

    # Persist tags
    for tag in result.get("tags", []):
        db.session.add(
            Label(
                image_id=image.id,
                label_text=tag,
                label_type="tag",
                source_model="claude-3-5-sonnet",
            )
        )


@celery.task(bind=True, name="server.tasks.labeling.label_image")
def label_image_task(self, image_id: int, prompt_type: str = "default") -> Dict[str, Any]:
    """
    Label a single image asynchronously.

    Args:
        image_id: Database ID of the image.
        prompt_type: Prompt template to use.
    """
    from server.api import app
    from server.services.labeling import label_image_with_claude

    with app.app_context():
        image = db.session.get(Image, image_id)
        if not image:
            logger.error("Image %s not found for labeling task", image_id)
            return {"status": "error", "message": "Image not found"}

        logger.info("Starting labeling task for image %s", image_id)

        result = label_image_with_claude(image.file_path, prompt_type)

        if result.get("status") != "success":
            logger.error("Labeling failed for image %s: %s", image_id, result.get("message"))
            return {"status": "error", "message": result.get("message", "Labeling failed")}

        _apply_label_results(image, result)
        db.session.commit()

        logger.info(
            "Labeling completed for image %s",
            image_id,
            extra={"operation": "label_image", "image_id": image_id},
        )

        return {
            "status": "success",
            "image_id": image_id,
            "nsfw_rating": result.get("nsfw_rating"),
            "tags": result.get("tags", []),
        }


@celery.task(bind=True, name="server.tasks.labeling.label_album")
def label_album_task(
    self, album_id: int, prompt_type: str = "sd_training", force: bool = False
) -> Dict[str, Any]:
    """
    Label every image in an album asynchronously.

    Args:
        album_id: ID of the album to label.
        prompt_type: Prompt template to use for Claude.
        force: If True, relabel images even if labels already exist.
    """
    from server.api import app
    from server.services.labeling import label_image_with_claude

    with app.app_context():
        album = db.session.get(Album, album_id)
        if not album:
            logger.error("Album %s not found for labeling task", album_id)
            return {"status": "error", "message": "Album not found"}

        associations = AlbumImage.query.filter_by(album_id=album_id).all()
        images = [assoc.image for assoc in associations if assoc.image]

        if not images:
            logger.warning("Album %s is empty. Skipping labeling.", album_id)
            return {"status": "error", "message": "Album is empty"}

        if not force:
            images = [img for img in images if not img.labels]

        if not images:
            logger.info("All images already labeled for album %s", album_id)
            return {"status": "error", "message": "All images already labeled"}

        total = len(images)
        successes = 0
        failures = 0
        results: Dict[int, Dict[str, Any]] = {}

        logger.info("Starting album labeling task for album %s (%s images)", album_id, total)

        for index, image in enumerate(images, start=1):
            if getattr(self.request, "id", None):
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": index,
                        "total": total,
                        "success": successes,
                        "failed": failures,
                    },
                )

            result = label_image_with_claude(image.file_path, prompt_type)
            if result.get("status") == "success":
                _apply_label_results(image, result)
                successes += 1
                results[image.id] = {
                    "status": "success",
                    "nsfw_rating": result.get("nsfw_rating"),
                    "tags": result.get("tags", []),
                }
            else:
                failures += 1
                logger.error(
                    "Batch labeling failed for image %s in album %s: %s",
                    image.id,
                    album_id,
                    result.get("message"),
                )
                results[image.id] = {"status": "error", "message": result.get("message")}

            db.session.commit()

        logger.info(
            "Album labeling completed for album %s: %s success / %s failed",
            album_id,
            successes,
            failures,
            extra={"operation": "label_album", "album_id": album_id},
        )

        return {
            "status": "success",
            "album_id": album_id,
            "total": total,
            "success": successes,
            "failed": failures,
            "results": results,
            "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
