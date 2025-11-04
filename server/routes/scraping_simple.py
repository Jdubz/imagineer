"""
Web scraping API endpoints - Simple threading implementation (no Celery required)

This is a simpler alternative to the Celery-based scraping that uses the same
threading pattern as image generation.
"""

import json
import logging
import queue
import shutil
import threading
from datetime import datetime, timedelta, timezone

from flask import Blueprint, abort, jsonify, request

from server.auth import current_user, require_admin
from server.database import ScrapeJob, db

logger = logging.getLogger(__name__)

scraping_bp = Blueprint("scraping", __name__, url_prefix="/api/scraping")

# Simple threading-based queue (like generation.py)
scrape_queue: queue.Queue[int] = queue.Queue()  # Stores job IDs
current_scrape_job_id: int | None = None


def get_scrape_job_or_404(job_id: int) -> ScrapeJob:
    job = db.session.get(ScrapeJob, job_id)
    if job is None:
        abort(404)
    return job


def _is_admin_user() -> bool:
    try:
        return bool(current_user.is_authenticated and current_user.is_admin())
    except Exception:  # pragma: no cover
        return False


def process_scrape_jobs():
    """
    Background worker to process scraping jobs.
    Runs in a separate thread, similar to image generation worker.
    """
    global current_scrape_job_id

    # Import here to avoid circular imports
    from server.api import app
    from server.tasks.scraping import scrape_site_implementation

    while True:
        job_id = scrape_queue.get()
        if job_id is None:  # Shutdown signal
            break

        current_scrape_job_id = job_id

        try:
            with app.app_context():
                try:
                    logger.info(f"Processing scrape job {job_id}")
                    scrape_site_implementation(job_id)
                except Exception as e:
                    logger.error(f"Error processing scrape job {job_id}: {e}", exc_info=True)
                    try:
                        job = db.session.get(ScrapeJob, job_id)
                        if job:
                            job.status = "failed"
                            job.error_message = str(e)
                            job.completed_at = datetime.now(timezone.utc)
                            db.session.commit()
                    except Exception as db_err:
                        logger.error(f"Failed to update job {job_id} status: {db_err}")
        finally:
            current_scrape_job_id = None
            scrape_queue.task_done()


# Start background worker thread
worker_thread = threading.Thread(target=process_scrape_jobs, daemon=True)
worker_thread.start()


@scraping_bp.route("/start", methods=["POST"])
@require_admin
def start_scrape():
    """Start web scraping job (admin only)"""
    try:
        data = request.json or {}

        # Validate required fields
        url = data.get("url")
        if not url:
            return jsonify({"error": "URL is required"}), 400

        # Validate URL format
        if not url.startswith(("http://", "https://")):
            return jsonify({"error": "Invalid URL format"}), 400

        # Get optional parameters
        name = data.get("name", f"Scrape {url}")
        description = data.get("description", f"Web scraping job for {url}")
        depth = data.get("depth", 3)
        max_images = data.get("max_images", 1000)
        follow_links = data.get("follow_links", True)
        download_images = data.get("download_images", True)

        # Validate parameters
        if not isinstance(depth, int) or depth < 1 or depth > 10:
            return jsonify({"error": "Depth must be between 1 and 10"}), 400

        if not isinstance(max_images, int) or max_images < 1 or max_images > 10000:
            return jsonify({"error": "Max images must be between 1 and 10000"}), 400

        # Create scrape config
        scrape_config = {
            "depth": depth,
            "max_images": max_images,
            "follow_links": follow_links,
            "download_images": download_images,
        }

        # Create job record
        job = ScrapeJob(
            name=name,
            description=description,
            source_url=url,
            scrape_config=json.dumps(scrape_config),
            status="pending",
        )

        db.session.add(job)
        db.session.commit()

        # Add job to queue
        scrape_queue.put(job.id)

        logger.info(f"Queued scrape job {job.id} for URL {url}")

        return (
            jsonify({"success": True, "job_id": job.id, "status": "pending"}),
            201,
        )

    except Exception as e:
        logger.error(f"Error starting scrape job: {e}", exc_info=True)
        return jsonify({"error": "Failed to start scrape job"}), 500


@scraping_bp.route("/jobs", methods=["GET"])
def list_scrape_jobs():
    """List all scrape jobs (public)"""
    try:
        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 20, type=int), 100)

        # Query jobs
        jobs_query = ScrapeJob.query.order_by(ScrapeJob.created_at.desc())
        jobs = jobs_query.paginate(page=page, per_page=per_page, error_out=False)

        include_sensitive = _is_admin_user()

        return jsonify(
            {
                "jobs": [job.to_dict(include_sensitive=include_sensitive) for job in jobs.items],
                "total": jobs.total,
                "page": page,
                "per_page": per_page,
                "pages": jobs.pages,
            }
        )

    except Exception as e:
        logger.error(f"Error listing scrape jobs: {e}", exc_info=True)
        return jsonify({"error": "Failed to list scrape jobs"}), 500


@scraping_bp.route("/jobs/<int:job_id>", methods=["GET"])
def get_scrape_job(job_id):
    """Get scrape job status (public)"""
    try:
        job = db.session.get(ScrapeJob, job_id)
        if not job:
            return jsonify({"error": "Scrape job not found"}), 404
        return jsonify(job.to_dict(include_sensitive=_is_admin_user()))

    except Exception as e:
        logger.error(f"Error getting scrape job {job_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to get scrape job"}), 500


@scraping_bp.route("/jobs/<int:job_id>/cancel", methods=["POST"])
@require_admin
def cancel_scrape_job(job_id):
    """Cancel running scrape job (admin only)"""
    try:
        job = get_scrape_job_or_404(job_id)

        if job.status not in ["pending", "running"]:
            return jsonify({"error": "Job cannot be cancelled"}), 400

        # For pending jobs, just update status
        if job.status == "pending":
            job.status = "cancelled"
            db.session.commit()
            logger.info(f"Cancelled pending scrape job {job_id}")
            return jsonify({"success": True, "message": "Job cancelled successfully"})

        # For running jobs, we can't easily kill the subprocess without
        # storing process info, so just mark as cancelled and let it finish
        job.status = "cancelled"
        job.description = "Cancellation requested (will finish current operation)"
        db.session.commit()

        logger.info(f"Marked scrape job {job_id} for cancellation")

        return jsonify(
            {
                "success": True,
                "message": "Job marked for cancellation (will finish current operation)",
            }
        )

    except Exception as e:
        logger.error(f"Error cancelling scrape job {job_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to cancel scrape job"}), 500


@scraping_bp.route("/jobs/<int:job_id>/cleanup", methods=["POST"])
@require_admin
def cleanup_job(job_id):
    """Clean up completed scrape job (admin only)"""
    try:
        job = get_scrape_job_or_404(job_id)

        if job.status not in ["completed", "failed", "cancelled"]:
            return (
                jsonify({"error": "Job must be completed, failed, or cancelled before cleanup"}),
                400,
            )

        # Delete image records and album associations for this job
        if job.album_id:
            from pathlib import Path

            from server.database import Album, AlbumImage, Image

            album = db.session.get(Album, job.album_id)
            if album:
                # Get all images in this album
                album_images = AlbumImage.query.filter_by(album_id=album.id).all()
                image_ids = [ai.image_id for ai in album_images]

                # Delete album associations
                for ai in album_images:
                    db.session.delete(ai)

                # Delete images that were scraped (check file_path is in output_directory)
                if job.output_directory:
                    output_path = Path(job.output_directory)
                    for image_id in image_ids:
                        image = db.session.get(Image, image_id)
                        if image and image.file_path:
                            image_path = Path(image.file_path)
                            # Only delete if image file is in the scrape output directory
                            try:
                                if image_path.is_relative_to(output_path):
                                    db.session.delete(image)
                            except (ValueError, AttributeError):
                                # is_relative_to not available or path comparison failed
                                # Fall back to string comparison
                                if str(image_path).startswith(str(output_path)):
                                    db.session.delete(image)

                # Delete the album
                db.session.delete(album)

                logger.info(
                    "Deleted album %s and associated images for scrape job %s", album.id, job_id
                )

        # Clean up output directory if it exists
        if job.output_directory:
            from pathlib import Path

            output_path = Path(job.output_directory)
            if output_path.exists():
                shutil.rmtree(output_path)
                logger.info(f"Cleaned up output directory for job {job_id}")

        # Mark job as cleaned up
        job.status = "cleaned_up"
        job.output_directory = None
        db.session.commit()

        logger.info(f"Cleaned up scrape job {job_id}")

        return jsonify({"success": True, "message": "Cleanup completed successfully"})

    except Exception as e:
        logger.error(f"Error starting cleanup for job {job_id}: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({"error": "Failed to cleanup job"}), 500


@scraping_bp.route("/stats", methods=["GET"])
def get_scraping_stats():
    """Get scraping statistics (public)"""
    try:
        from sqlalchemy import func

        from server.tasks.scraping import get_scraped_output_path

        # Get job counts by status
        status_counts = (
            db.session.query(ScrapeJob.status, func.count(ScrapeJob.id))
            .group_by(ScrapeJob.status)
            .all()
        )

        # Get total images scraped
        total_images = db.session.query(func.sum(ScrapeJob.images_scraped)).scalar() or 0

        # Get recent jobs (last 7 days)
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_jobs = ScrapeJob.query.filter(ScrapeJob.created_at >= week_ago).count()

        output_root = get_scraped_output_path()
        storage: dict[str, object]
        try:
            usage = shutil.disk_usage(output_root)
            total_gb = round(usage.total / (1024**3), 2)
            used_gb = round(usage.used / (1024**3), 2)
            free_gb = round(usage.free / (1024**3), 2)
            free_percent = round((usage.free / usage.total) * 100, 2) if usage.total else None
            storage = {
                "path": str(output_root),
                "total_gb": total_gb,
                "used_gb": used_gb,
                "free_gb": free_gb,
                "free_percent": free_percent,
            }
        except OSError as exc:
            logger.warning(
                "Unable to read disk usage for scrape output directory %s: %s",
                output_root,
                exc,
            )
            storage = {
                "path": str(output_root),
                "error": str(exc),
            }

        stats = {
            "total_jobs": ScrapeJob.query.count(),
            "total_images_scraped": int(total_images),
            "recent_jobs": recent_jobs,
            "status_breakdown": dict(status_counts),
            "storage": storage,
        }

        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error getting scraping stats: {e}", exc_info=True)
        return jsonify({"error": "Failed to get scraping stats"}), 500


@scraping_bp.route("/queue", methods=["GET"])
def get_queue_status():
    """Get current queue status"""
    return jsonify(
        {
            "queue_size": scrape_queue.qsize(),
            "current_job_id": current_scrape_job_id,
        }
    )
