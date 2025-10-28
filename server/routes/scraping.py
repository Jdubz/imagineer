"""
Web scraping API endpoints
"""

import json
import logging

from flask import Blueprint, abort, jsonify, request

from server.auth import require_admin
from server.database import ScrapeJob, db
from server.tasks.scraping import cleanup_scrape_job, scrape_site_task

logger = logging.getLogger(__name__)

scraping_bp = Blueprint("scraping", __name__, url_prefix="/api/scraping")


def get_scrape_job_or_404(job_id: int) -> ScrapeJob:
    job = db.session.get(ScrapeJob, job_id)
    if job is None:
        abort(404)
    return job


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

        # Submit task to Celery
        task = scrape_site_task.delay(job.id)

        logger.info(f"Started scrape job {job.id} for URL {url}")

        return (
            jsonify({"success": True, "job_id": job.id, "task_id": task.id, "status": "pending"}),
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

        return jsonify(
            {
                "jobs": [job.to_dict() for job in jobs.items],
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
        return jsonify(job.to_dict())

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

        # Cancel Celery task if it exists
        if hasattr(job, "celery_task_id") and job.celery_task_id:
            from server.celery_app import celery as celery_app

            celery_app.control.revoke(job.celery_task_id, terminate=True)

        # Update job status
        job.status = "cancelled"
        db.session.commit()

        logger.info(f"Cancelled scrape job {job_id}")

        return jsonify({"success": True, "message": "Job cancelled successfully"})

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

        # Submit cleanup task
        task = cleanup_scrape_job.delay(job_id)

        logger.info(f"Started cleanup for scrape job {job_id}")

        return jsonify({"success": True, "message": "Cleanup started", "task_id": task.id})

    except Exception as e:
        logger.error(f"Error starting cleanup for job {job_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to start cleanup"}), 500


@scraping_bp.route("/stats", methods=["GET"])
def get_scraping_stats():
    """Get scraping statistics (public)"""
    try:
        from sqlalchemy import func

        # Get job counts by status
        status_counts = (
            db.session.query(ScrapeJob.status, func.count(ScrapeJob.id))
            .group_by(ScrapeJob.status)
            .all()
        )

        # Get total images scraped
        total_images = db.session.query(func.sum(ScrapeJob.images_scraped)).scalar() or 0

        # Get recent jobs (last 7 days)
        from datetime import datetime, timedelta, timezone

        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_jobs = ScrapeJob.query.filter(ScrapeJob.created_at >= week_ago).count()

        stats = {
            "total_jobs": ScrapeJob.query.count(),
            "total_images_scraped": int(total_images),
            "recent_jobs": recent_jobs,
            "status_breakdown": dict(status_counts),
        }

        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error getting scraping stats: {e}", exc_info=True)
        return jsonify({"error": "Failed to get scraping stats"}), 500
