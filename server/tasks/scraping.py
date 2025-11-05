"""
Web scraping integration tasks
"""

import hashlib
import json
import logging
import os
import re
import selectors
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image as PILImage

from server.celery_app import celery
from server.database import Album, AlbumImage, Image, Label, ScrapeJob, db
from server.utils.file_ops import safe_remove_path

logger = logging.getLogger(__name__)

# Will be set from config in the task
SCRAPED_OUTPUT_PATH = None
TRAINING_DATA_REPO_PATH: Path | None = None

SCRAPING_MAX_DURATION_SECONDS = int(
    os.environ.get("IMAGINEER_SCRAPE_TIMEOUT_SECONDS", str(2 * 60 * 60))
)
SCRAPING_IDLE_TIMEOUT_SECONDS = int(os.environ.get("IMAGINEER_SCRAPE_IDLE_TIMEOUT_SECONDS", "600"))
SCRAPING_TERMINATE_GRACE_SECONDS = int(
    os.environ.get("IMAGINEER_SCRAPE_TERMINATE_GRACE_SECONDS", "30")
)
SCRAPING_RETENTION_DAYS = int(os.environ.get("IMAGINEER_SCRAPE_RETENTION_DAYS", "30"))


def _load_scrape_config(job: ScrapeJob) -> dict:
    """Parse scrape configuration JSON safely."""
    if not job.scrape_config:
        return {}
    try:
        parsed = json.loads(job.scrape_config)
        return parsed if isinstance(parsed, dict) else {}
    except (ValueError, TypeError):
        return {}


def _persist_runtime_state(
    job: ScrapeJob,
    config: dict,
    *,
    stage: str | None = None,
    discovered: int | None = None,
    downloaded: int | None = None,
    message: str | None = None,
) -> None:
    """Store real-time telemetry about the scrape job."""
    runtime = config.get("runtime", {})
    if not isinstance(runtime, dict):
        runtime = {}

    if stage:
        runtime["stage"] = stage
    if discovered is not None:
        runtime["discovered"] = discovered
    if downloaded is not None:
        runtime["downloaded"] = downloaded
    if message is not None:
        runtime["last_message"] = message
    else:
        runtime["last_message"] = job.description or ""

    runtime["progress"] = job.progress
    runtime["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    config["runtime"] = runtime
    job.scrape_config = json.dumps(config)


def _get_training_data_repo() -> Path:
    """Return the root of the training-data repository used for scraping."""
    global TRAINING_DATA_REPO_PATH

    if TRAINING_DATA_REPO_PATH is not None:
        return TRAINING_DATA_REPO_PATH

    candidate = os.environ.get("IMAGINEER_TRAINING_DATA_PATH")

    if not candidate:
        from server.api import load_config

        config = load_config()
        candidate = (
            config.get("scraping", {}).get("training_data_repo")
            if isinstance(config, dict)
            else None
        )

    if candidate:
        repo_path = Path(candidate).expanduser()
    else:
        repo_path = Path(__file__).parent.parent.parent / "training-data"

    if not repo_path.exists():
        try:
            repo_path.mkdir(parents=True, exist_ok=True)
            logger.info(
                "Created training data repository directory at %s",
                repo_path,
            )
        except OSError as exc:
            if os.environ.get("FLASK_ENV") == "production":
                raise RuntimeError(
                    f"Unable to initialize training data repository at {repo_path}: {exc}. "
                    "Set IMAGINEER_TRAINING_DATA_PATH or scraping.training_data_repo in "
                    "config.yaml to a writable location."
                ) from exc
            logger.warning(
                "Training data repository %s does not exist and could not be created: %s; "
                "continuing using development defaults.",
                repo_path,
                exc,
            )

    TRAINING_DATA_REPO_PATH = repo_path
    return repo_path


def get_scraped_output_path() -> Path:
    """Resolve base directory for scraped outputs from configuration."""
    global SCRAPED_OUTPUT_PATH

    if SCRAPED_OUTPUT_PATH is None:
        from server.api import load_config

        config = load_config()
        outputs_config = config.get("outputs", {}) if isinstance(config, dict) else {}

        base_dir = outputs_config.get("base_dir")
        scraped_dir = outputs_config.get("scraped_dir")

        if scraped_dir:
            candidate_path = Path(scraped_dir).expanduser()
        elif base_dir:
            candidate_path = Path(base_dir).expanduser() / "scraped"
        else:
            candidate_path = Path("/tmp/imagineer/outputs/scraped")

        fallback_path = Path(base_dir).expanduser() / "scraped" if base_dir else None

        try:
            candidate_path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            if os.environ.get("FLASK_ENV") == "production":
                raise RuntimeError(
                    f"Unable to initialize scraped output directory at {candidate_path}: {exc}. "
                    "Configure outputs.base_dir or outputs.scraped_dir with writable storage."
                ) from exc

            logger.warning(
                "Unable to initialize scraped output directory %s: %s. "
                "Attempting fallback for development.",
                candidate_path,
                exc,
            )

            fallback_candidate = (
                fallback_path
                if fallback_path and fallback_path != candidate_path
                else Path("/tmp/imagineer/outputs/scraped")
            )

            try:
                fallback_candidate.mkdir(parents=True, exist_ok=True)
                candidate_path = fallback_candidate
            except OSError:
                # Fallback also failed, use /tmp as last resort
                logger.warning(
                    "Fallback directory %s also inaccessible. Using /tmp fallback.",
                    fallback_candidate,
                )
                candidate_path = Path("/tmp/imagineer/outputs/scraped")
                candidate_path.mkdir(parents=True, exist_ok=True)

        SCRAPED_OUTPUT_PATH = candidate_path

    return SCRAPED_OUTPUT_PATH


def scrape_site_implementation(scrape_job_id, celery_task=None):  # noqa: C901
    """
    Execute web scraping job using training-data project.

    This is the core implementation that can be called from either Celery or threading.

    Args:
        scrape_job_id: Database ID of scrape job
        celery_task: Optional Celery task instance for progress updates

    Returns:
        Dict with job results
    """
    from server.api import app

    with app.app_context():
        job = db.session.get(ScrapeJob, scrape_job_id)
        if not job:
            return {"status": "error", "message": "Job not found"}

        config = _load_scrape_config(job)

        # Update job status
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        job.progress = 0
        job.description = "Initializing scrape job"
        _persist_runtime_state(
            job,
            config,
            stage="initializing",
            discovered=0,
            downloaded=0,
            message=job.description,
        )
        db.session.commit()

        logger.info(f"Starting scrape job {scrape_job_id}: {job.source_url}")

        try:
            output_base = get_scraped_output_path()
            output_base.mkdir(parents=True, exist_ok=True)

            # Create output directory
            output_dir = output_base / f"job_{scrape_job_id}"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Parse scrape config
            depth = config.get("depth", 3)
            max_images = config.get("max_images", 1000)

            # Run training-data scraper
            training_data_repo = _get_training_data_repo()

            # Use training-data's virtual environment Python
            training_venv_python = training_data_repo / "venv" / "bin" / "python"
            if not training_venv_python.exists():
                # Fall back to system Python if venv doesn't exist
                training_venv_python = Path("/usr/bin/python3")

            # training-data CLI expects: [OPTIONS] URL [PROMPT] OUTPUT_DIR
            # We need to provide all 3 positional args
            cmd = [
                str(training_venv_python),
                "-m",
                "training_data",
            ]

            # Add options FIRST
            if max_images > 0:
                cmd.extend(["--max-images", str(max_images)])

            if depth > 0:
                cmd.extend(["--max-depth", str(depth)])

            # Add positional arguments: URL PROMPT OUTPUT_DIR
            cmd.extend(
                [
                    job.source_url,  # URL
                    "training data",  # PROMPT positional arg required by training-data CLI
                    str(output_dir),  # OUTPUT_DIR
                ]
            )

            # Add config if it exists
            default_config = training_data_repo / "config" / "default_config.yaml"
            if default_config.exists():
                cmd.extend(["--config", str(default_config)])

            # Check for Anthropic API key
            if not os.environ.get("ANTHROPIC_API_KEY"):
                # Try to load from training-data .env
                env_file = training_data_repo / ".env"
                if env_file.exists():
                    from dotenv import load_dotenv

                    load_dotenv(env_file)

            logger.info(f"Running scraper command: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                cwd=training_data_repo,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            # Stream output and update progress
            discovered_count = 0
            downloaded_count = 0
            stage = "running"
            start_time = time.monotonic()
            last_output_time = start_time
            timeout_reason: str | None = None

            selector = selectors.DefaultSelector()
            if process.stdout:
                selector.register(process.stdout, selectors.EVENT_READ)

            discovered_pattern = re.compile(r"Discovered\s+(\d+)\s+images", re.IGNORECASE)
            downloaded_pattern = re.compile(
                r"Downloaded\s+(\d+)(?:/(\d+))?\s+images", re.IGNORECASE
            )
            caption_pattern = re.compile(r"Captioning\s+image\s+(\d+)(?:/(\d+))?", re.IGNORECASE)

            try:
                while True:
                    now = time.monotonic()
                    if (
                        SCRAPING_MAX_DURATION_SECONDS > 0
                        and now - start_time > SCRAPING_MAX_DURATION_SECONDS
                        and timeout_reason is None
                    ):
                        timeout_reason = (
                            "Scrape exceeded maximum duration of "
                            f"{SCRAPING_MAX_DURATION_SECONDS} seconds"
                        )
                        break

                    events = selector.select(timeout=1)
                    if events:
                        for key, _ in events:
                            line = key.fileobj.readline()
                            if line == "":
                                continue
                            line = line.strip()
                            if not line:
                                continue

                            last_output_time = time.monotonic()
                            logger.info(f"Scraper: {line}")

                            # Parse training-data output format
                            # "INFO     Discovered X images"
                            # "INFO     Downloaded X/Y images"
                            # "INFO     Captioning image X/Y"
                            discovered_match = discovered_pattern.search(line)
                            if discovered_match:
                                discovered_count = int(discovered_match.group(1))
                                stage = "discovering"
                            elif downloaded_match := downloaded_pattern.search(line):
                                downloaded_count = int(downloaded_match.group(1))
                                job.images_scraped = downloaded_count
                                if max_images > 0:
                                    progress = min(90, int((downloaded_count / max_images) * 90))
                                    job.progress = progress
                                stage = "downloading"
                            elif caption_match := caption_pattern.search(line):
                                captioned_count = int(caption_match.group(1))
                                if max_images > 0:
                                    progress = min(95, 90 + int((captioned_count / max_images) * 5))
                                    job.progress = progress
                                stage = "captioning"

                            job.description = line[-200:] if len(line) > 200 else line
                            _persist_runtime_state(
                                job,
                                config,
                                stage=stage,
                                discovered=discovered_count,
                                downloaded=downloaded_count,
                                message=job.description,
                            )
                            db.session.commit()

                            # Update Celery task state if available
                            if celery_task:
                                celery_task.update_state(
                                    state="PROGRESS",
                                    meta={
                                        "discovered": discovered_count,
                                        "downloaded": downloaded_count,
                                        "progress": job.progress,
                                        "message": job.description,
                                    },
                                )
                    else:
                        if (
                            SCRAPING_IDLE_TIMEOUT_SECONDS > 0
                            and time.monotonic() - last_output_time > SCRAPING_IDLE_TIMEOUT_SECONDS
                            and timeout_reason is None
                        ):
                            timeout_reason = (
                                "Scrape produced no output for "
                                f"{SCRAPING_IDLE_TIMEOUT_SECONDS} seconds"
                            )
                            break

                    if process.poll() is not None:
                        break
            finally:
                if process.stdout:
                    try:
                        selector.unregister(process.stdout)
                    except Exception:  # pragma: no cover - best effort cleanup
                        pass
                    process.stdout.close()
                selector.close()

            if timeout_reason:
                try:
                    process.terminate()
                    try:
                        process.wait(timeout=SCRAPING_TERMINATE_GRACE_SECONDS)
                    except subprocess.TimeoutExpired:
                        process.kill()
                except Exception as exc:  # pragma: no cover - best effort terminate
                    logger.warning("Failed to terminate scraper process: %s", exc, exc_info=True)

                job.status = "failed"
                job.completed_at = datetime.now(timezone.utc)
                job.description = timeout_reason
                job.progress = job.progress if job.progress else 0
                _persist_runtime_state(
                    job,
                    config,
                    stage="failed",
                    discovered=discovered_count,
                    downloaded=downloaded_count,
                    message=timeout_reason,
                )
                db.session.commit()

                return {
                    "status": "failed",
                    "message": timeout_reason,
                }

            return_code = process.wait()

            if return_code == 0:
                # Scraping successful - import results
                logger.info(f"Scraper completed successfully for job {scrape_job_id}")
                result = import_scraped_images(scrape_job_id, output_dir)

                job.status = "completed"
                job.completed_at = datetime.now(timezone.utc)
                job.progress = 100
                job.output_directory = str(output_dir)
                job.album_id = result.get("album_id")
                job.description = "Scrape completed successfully"
                _persist_runtime_state(
                    job,
                    config,
                    stage="completed",
                    discovered=discovered_count,
                    downloaded=downloaded_count,
                    message=job.description,
                )
                db.session.commit()

                return {
                    "status": "success",
                    "images_imported": result["imported"],
                    "album_id": result["album_id"],
                    "output_directory": str(output_dir),
                }
            else:
                error_msg = f"Scraper failed with code {process.returncode}"
                logger.error(f"Scraper failed for job {scrape_job_id}: {error_msg}")

                job.status = "failed"
                job.completed_at = datetime.now(timezone.utc)
                job.error_message = error_msg
                job.last_error_at = datetime.now(timezone.utc)
                job.description = error_msg
                _persist_runtime_state(
                    job,
                    config,
                    stage="failed",
                    discovered=discovered_count,
                    downloaded=downloaded_count,
                    message=error_msg,
                )
                db.session.commit()

                return {"status": "error", "message": error_msg}

        except Exception as e:
            error_msg = f"Scrape job error: {str(e)}"
            logger.error(f"Scrape job {scrape_job_id} error: {e}", exc_info=True)

            job.status = "failed"
            job.completed_at = datetime.now(timezone.utc)
            job.error_message = error_msg
            job.last_error_at = datetime.now(timezone.utc)
            job.description = error_msg
            _persist_runtime_state(
                job,
                config,
                stage="failed",
                discovered=0,
                downloaded=0,
                message=error_msg,
            )
            db.session.commit()

            return {"status": "error", "message": error_msg}


@celery.task(bind=True, name="server.tasks.scraping.scrape_site")
def scrape_site_task(self, scrape_job_id):
    """
    Celery task wrapper for scrape_site_implementation.

    Args:
        scrape_job_id: Database ID of scrape job

    Returns:
        Dict with job results
    """
    return scrape_site_implementation(scrape_job_id, celery_task=self)


def import_scraped_images(scrape_job_id, output_dir):  # noqa: C901
    """
    Import scraped images into database and create album.

    Args:
        scrape_job_id: Scrape job ID
        output_dir: Path to scraped images directory

    Returns:
        Dict with import results
    """
    job = db.session.get(ScrapeJob, scrape_job_id)
    if not job:
        return {"imported": 0, "album_id": None}

    # Create album with source tracking
    album = Album(
        name=f"Scraped: {job.name}",
        description=f"Images scraped from {job.source_url}",
        album_type="scraped",
        is_public=True,
        source_type="scrape",
        source_id=scrape_job_id,
    )
    db.session.add(album)
    db.session.flush()

    # Find images directory
    images_dir = output_dir / "images"
    if not images_dir.exists():
        # Try alternative structure
        images_dir = output_dir
        if not any(images_dir.glob("*.jpg")):
            logger.warning(f"No images found in {output_dir}")
            return {"imported": 0, "album_id": album.id}

    imported_count = 0
    skipped_count = 0

    # Import all images
    for image_file in images_dir.glob("*.jpg"):
        try:
            # Check if image already exists (by filename)
            existing_image = Image.query.filter_by(filename=image_file.name).first()
            if existing_image:
                logger.info(f"Image {image_file.name} already exists, skipping")
                skipped_count += 1
                continue

            # Read caption if exists
            caption_file = image_file.with_suffix(".txt")
            caption = None
            if caption_file.exists():
                caption = caption_file.read_text().strip()

            # Get image dimensions and file size
            with PILImage.open(image_file) as img:
                width, height = img.size

            # file_size = image_file.stat().st_size  # TODO: Store file size in database

            # Calculate checksum (for future use)
            sha256 = hashlib.sha256()
            with open(image_file, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
            # checksum = sha256.hexdigest()  # TODO: Store checksum in database

            # Create image record
            image = Image(
                filename=image_file.name,
                file_path=str(image_file),
                width=width,
                height=height,
                is_public=True,
                is_nsfw=False,  # Will be updated by AI labeling if needed
            )
            db.session.add(image)
            db.session.flush()

            # Add caption as label if exists
            if caption:
                label = Label(
                    image_id=image.id,
                    label_text=caption,
                    label_type="caption",
                    source_model="scraper",
                )
                db.session.add(label)

            # Add to album
            assoc = AlbumImage(album_id=album.id, image_id=image.id, sort_order=imported_count)
            db.session.add(assoc)

            imported_count += 1

            if imported_count % 10 == 0:
                db.session.commit()
                logger.info(f"Imported {imported_count} images so far...")

        except Exception as e:
            logger.error(f"Error importing image {image_file.name}: {e}")
            skipped_count += 1
            continue

    db.session.commit()

    logger.info(
        f"Imported {imported_count} images from scrape job {scrape_job_id} "
        f"(skipped {skipped_count})"
    )

    return {"imported": imported_count, "skipped": skipped_count, "album_id": album.id}


@celery.task(name="server.tasks.scraping.purge_stale_scrape_artifacts")
def purge_stale_scrape_artifacts(retention_days: int | None = None):
    """Delete scrape outputs beyond the retention window."""

    from server.api import app

    days = int(retention_days or SCRAPING_RETENTION_DAYS)
    if days <= 0:
        return {"status": "skipped", "reason": "retention-disabled"}

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    jobs_processed = 0
    outputs_removed = 0

    with app.app_context():
        candidates = ScrapeJob.query.filter(
            ScrapeJob.status.in_(["completed", "failed", "cancelled", "cleaned_up"])
        )
        for job in candidates:
            reference_ts = job.completed_at or job.last_error_at or job.created_at
            if not reference_ts or reference_ts >= cutoff:
                continue

            target_path = (
                Path(job.output_directory)
                if job.output_directory
                else get_scraped_output_path() / f"job_{job.id}"
            )

            if safe_remove_path(target_path):
                outputs_removed += 1
                job.output_directory = ""

            jobs_processed += 1

        db.session.commit()

    return {
        "status": "success",
        "retention_days": days,
        "jobs_processed": jobs_processed,
        "outputs_removed": outputs_removed,
    }


@celery.task(name="server.tasks.scraping.cleanup_scrape_job")
def cleanup_scrape_job(scrape_job_id):
    """
    Clean up old scrape job data and files.

    Args:
        scrape_job_id: Scrape job ID to clean up
    """
    from server.api import app

    with app.app_context():
        job = db.session.get(ScrapeJob, scrape_job_id)
        if not job:
            return {"status": "error", "message": "Job not found"}

        try:
            # Delete image records and album associations for this job
            if job.album_id:
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
                        "Deleted album %s and associated images for scrape job %s",
                        album.id,
                        scrape_job_id,
                    )

            # Clean up output directory if it exists
            if job.output_directory:
                output_path = Path(job.output_directory)
                if output_path.exists():
                    import shutil

                    shutil.rmtree(output_path)
                    logger.info(f"Cleaned up output directory for job {scrape_job_id}")

            # Mark job as cleaned up
            job.status = "cleaned_up"
            job.output_directory = None
            db.session.commit()

            return {"status": "success", "message": "Job cleaned up successfully"}

        except Exception as e:
            logger.error(f"Error cleaning up job {scrape_job_id}: {e}", exc_info=True)
            db.session.rollback()
            return {"status": "error", "message": str(e)}


@celery.task(name="server.tasks.scraping.reset_stuck_scrape_jobs")
def reset_stuck_scrape_jobs(timeout_hours: int | None = None):
    """
    Detect and reset scrape jobs stuck in pending or running state.

    Args:
        timeout_hours: Hours after which a job is considered stuck (default: 2)

    Returns:
        Dict with reset statistics
    """
    from server.api import app

    # Default timeout is 2 hours
    timeout = timeout_hours or int(os.environ.get("IMAGINEER_SCRAPE_STUCK_TIMEOUT_HOURS", "2"))
    cutoff = datetime.now(timezone.utc) - timedelta(hours=timeout)

    reset_count = 0
    jobs_checked = 0

    with app.app_context():
        # Find jobs stuck in pending or running state
        stuck_jobs = ScrapeJob.query.filter(
            ScrapeJob.status.in_(["pending", "running"]),
            ScrapeJob.created_at < cutoff,
        ).all()

        for job in stuck_jobs:
            jobs_checked += 1

            # For pending jobs, check if they were never started
            if job.status == "pending" and not job.started_at:
                job.status = "failed"
                job.completed_at = datetime.now(timezone.utc)
                job.error_message = f"Job stuck in pending state for over {timeout} hours"
                job.last_error_at = datetime.now(timezone.utc)
                reset_count += 1
                logger.warning(f"Reset stuck pending job {job.id}: never started")

            # For running jobs, check if they haven't updated in timeout period
            elif job.status == "running":
                # Check when the job was last updated
                last_update = job.started_at or job.created_at
                if last_update < cutoff:
                    job.status = "failed"
                    job.completed_at = datetime.now(timezone.utc)
                    job.error_message = f"Job stuck in running state for over {timeout} hours"
                    job.last_error_at = datetime.now(timezone.utc)
                    reset_count += 1
                    logger.warning(
                        f"Reset stuck running job {job.id}: no updates since {last_update}"
                    )

        if reset_count > 0:
            db.session.commit()
            logger.info(f"Reset {reset_count} stuck scrape jobs out of {jobs_checked} checked")

    return {
        "status": "success",
        "timeout_hours": timeout,
        "jobs_checked": jobs_checked,
        "jobs_reset": reset_count,
    }
