"""
Generation queue and LoRA management endpoints.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import random
import subprocess
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path

import yaml
from flask import Blueprint, jsonify, request, send_from_directory
from flask_login import current_user

from server.auth import require_admin
from server.config_loader import PROJECT_ROOT, load_config
from server.database import Album, db

logger = logging.getLogger(__name__)

generation_bp = Blueprint("generation", __name__, url_prefix="/api")

# Rate limiting configuration -------------------------------------------------
GENERATION_RATE_LIMIT = int(os.environ.get("IMAGINEER_GENERATE_LIMIT", "10"))
GENERATION_RATE_WINDOW_SECONDS = int(os.environ.get("IMAGINEER_GENERATE_WINDOW_SECONDS", "60"))

_generation_rate_lock = threading.Lock()
_generation_request_times: defaultdict[str, deque[float]] = defaultdict(deque)

# Generation worker configuration --------------------------------------------
VENV_PYTHON = PROJECT_ROOT / "venv" / "bin" / "python"
GENERATE_SCRIPT = PROJECT_ROOT / "examples" / "generate.py"

job_queue: queue.Queue[dict] = queue.Queue()
job_history: list[dict] = []


def _prune_none_fields(payload: dict) -> dict:
    """Remove keys with None values to keep API responses clean."""
    return {key: value for key, value in payload.items() if value is not None}


current_job: dict | None = None


def _check_generation_rate_limit() -> tuple[dict, int] | None:
    """Apply a simple per-user rate limit for generation endpoints."""
    if GENERATION_RATE_LIMIT <= 0 or GENERATION_RATE_WINDOW_SECONDS <= 0:
        return None

    identifier = getattr(current_user, "email", None) or request.remote_addr or "anonymous"
    now = time.monotonic()

    with _generation_rate_lock:
        history = _generation_request_times[identifier]
        while history and now - history[0] > GENERATION_RATE_WINDOW_SECONDS:
            history.popleft()

        if len(history) >= GENERATION_RATE_LIMIT:
            retry_after = max(1, int(GENERATION_RATE_WINDOW_SECONDS - (now - history[0])))
            logger.warning(
                "Generation rate limit exceeded",
                extra={
                    "operation": "generate_rate_limit",
                    "identifier": identifier,
                    "limit": GENERATION_RATE_LIMIT,
                    "window_seconds": GENERATION_RATE_WINDOW_SECONDS,
                },
            )
            response = jsonify(
                {
                    "success": False,
                    "error": "Rate limit exceeded. Please wait before submitting another job.",
                }
            )
            response.headers["Retry-After"] = str(retry_after)
            return response, 429

        history.append(now)

    return None


def construct_prompt(base_prompt, user_theme, csv_data, prompt_template, style_suffix):
    """Construct a prompt string from template components."""
    csv_text = prompt_template
    for key, value in csv_data.items():
        csv_text = csv_text.replace(f"{{{key}}}", value)

    parts = []
    if base_prompt:
        parts.append(base_prompt)
    if user_theme:
        parts.append(f"Art style: {user_theme}")
    if csv_text:
        parts.append(csv_text)
    if style_suffix:
        parts.append(style_suffix)

    return ". ".join(parts)


def generate_random_theme():
    """Generate a random art style theme for inspiration."""
    styles = [
        "watercolor",
        "oil painting",
        "digital art",
        "pencil sketch",
        "ink drawing",
        "pastel",
        "acrylic",
        "charcoal",
        "mixed media",
        "gouache",
        "airbrush",
        "impressionist",
        "art nouveau",
        "art deco",
        "baroque",
        "renaissance",
        "surrealist",
        "abstract",
        "minimalist",
        "pop art",
        "cyberpunk",
        "steampunk",
        "vaporwave",
        "synthwave",
        "retro",
        "vintage",
        "modern",
        "contemporary",
    ]

    environments = [
        "mystical forest",
        "cosmic nebula",
        "underwater world",
        "desert landscape",
        "mountain peaks",
        "ancient ruins",
        "futuristic city",
        "enchanted garden",
        "stormy ocean",
        "peaceful meadow",
        "dark cavern",
        "floating islands",
        "crystal palace",
        "volcanic terrain",
        "frozen tundra",
        "tropical paradise",
        "haunted mansion",
        "steampunk workshop",
        "neon-lit streets",
        "starlit sky",
    ]

    moods = [
        "ethereal glowing light",
        "dramatic shadows",
        "soft diffused lighting",
        "golden hour glow",
        "moonlit atmosphere",
        "harsh sunlight",
        "bioluminescent glow",
        "candlelit ambiance",
        "aurora borealis",
        "sunset colors",
        "dawn light",
        "neon glow",
        "firelight",
        "lightning flashes",
        "rainbow light",
        "foggy mist",
    ]

    colors = [
        "deep purples and blues",
        "warm oranges and reds",
        "cool greens and teals",
        "monochromatic grayscale",
        "vibrant rainbow",
        "pastel pinks and lavenders",
        "earth tones",
        "metallic gold and silver",
        "black and gold",
        "navy and cream",
        "emerald and sapphire",
        "crimson and gold",
        "turquoise and coral",
    ]

    components = random.sample(
        [
            f"{random.choice(styles)} style",
            random.choice(environments),
            random.choice(moods),
            random.choice(colors),
        ],
        k=random.randint(2, 3),
    )
    return ", ".join(components)


def process_jobs():  # noqa: C901
    """Background worker to process generation jobs."""
    global current_job

    while True:
        job = job_queue.get()
        if job is None:
            break

        current_job = job
        job["status"] = "running"
        job["started_at"] = datetime.now().isoformat()

        try:
            cmd = [str(VENV_PYTHON), str(GENERATE_SCRIPT), "--prompt", job["prompt"]]

            if job.get("seed"):
                cmd.extend(["--seed", str(job["seed"])])
            if job.get("steps"):
                cmd.extend(["--steps", str(job["steps"])])
            if job.get("width"):
                cmd.extend(["--width", str(job["width"])])
            if job.get("height"):
                cmd.extend(["--height", str(job["height"])])
            if job.get("guidance_scale"):
                cmd.extend(["--guidance-scale", str(job["guidance_scale"])])
            if job.get("negative_prompt"):
                cmd.extend(["--negative-prompt", job["negative_prompt"]])

            if job.get("lora_paths") and job.get("lora_weights"):
                cmd.extend(["--lora-paths"] + job["lora_paths"])
                cmd.extend(["--lora-weights"] + [str(weight) for weight in job["lora_weights"]])

            if job.get("output"):
                cmd.extend(["--output", job["output"]])
            elif job.get("output_dir") and job.get("batch_item_name"):
                safe_name = "".join(
                    c for c in job["batch_item_name"] if c.isalnum() or c in (" ", "_", "-")
                ).strip()
                safe_name = safe_name.replace(" ", "_")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = Path(job["output_dir"]) / f"{timestamp}_{safe_name}.png"
                cmd.extend(["--output", str(output_path)])

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)

            if result.returncode == 0:
                job["status"] = "completed"
                job["output"] = result.stdout
                for line in result.stdout.split("\n"):
                    if "Image saved to:" in line:
                        job["output_path"] = line.split("Image saved to:")[1].strip()
            else:
                job["status"] = "failed"
                job["error"] = result.stderr

        except Exception as exc:  # pragma: no cover - defensive
            job["status"] = "failed"
            job["error"] = str(exc)

        job["completed_at"] = datetime.now().isoformat()
        job = _prune_none_fields(job)
        job_history.append(job)
        current_job = None
        job_queue.task_done()


worker_thread = threading.Thread(target=process_jobs, daemon=True)
worker_thread.start()


@generation_bp.route("/generate", methods=["POST"])
@require_admin
def generate():  # noqa: C901
    """Submit a new image generation job."""
    try:
        data = request.json
        if not data or not data.get("prompt"):
            return jsonify({"success": False, "error": "Prompt is required"}), 400

        prompt = str(data["prompt"]).strip()
        if not prompt:
            return jsonify({"success": False, "error": "Prompt is required"}), 400
        if len(prompt) > 2000:
            return jsonify({"success": False, "error": "Prompt too long (max 2000 chars)"}), 400

        seed = data.get("seed")
        if seed is not None:
            try:
                seed = int(seed)
                if seed < 0 or seed > 2147483647:
                    return (
                        jsonify(
                            {"success": False, "error": "Seed must be between 0 and 2147483647"}
                        ),
                        400,
                    )
            except (ValueError, TypeError):
                return jsonify({"success": False, "error": "Invalid seed value"}), 400

        steps = data.get("steps")
        if steps is not None:
            try:
                steps = int(steps)
                if steps < 1 or steps > 150:
                    return (
                        jsonify({"success": False, "error": "Steps must be between 1 and 150"}),
                        400,
                    )
            except (ValueError, TypeError):
                return jsonify({"success": False, "error": "Invalid steps value"}), 400

        width = data.get("width")
        if width is not None:
            try:
                width = int(width)
                if width < 64 or width > 2048 or width % 8 != 0:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "Width must be between 64-2048 and divisible by 8",
                            }
                        ),
                        400,
                    )
            except (ValueError, TypeError):
                return jsonify({"success": False, "error": "Invalid width value"}), 400

        height = data.get("height")
        if height is not None:
            try:
                height = int(height)
                if height < 64 or height > 2048 or height % 8 != 0:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "Height must be between 64-2048 and divisible by 8",
                            }
                        ),
                        400,
                    )
            except (ValueError, TypeError):
                return jsonify({"success": False, "error": "Invalid height value"}), 400

        guidance_scale = data.get("guidance_scale")
        if guidance_scale is not None:
            try:
                guidance_scale = float(guidance_scale)
                if guidance_scale < 0 or guidance_scale > 30:
                    return (
                        jsonify(
                            {"success": False, "error": "Guidance scale must be between 0 and 30"}
                        ),
                        400,
                    )
            except (ValueError, TypeError):
                return jsonify({"success": False, "error": "Invalid guidance scale value"}), 400

        negative_prompt = data.get("negative_prompt")
        if negative_prompt is not None:
            negative_prompt = str(negative_prompt).strip()
            if len(negative_prompt) > 2000:
                return (
                    jsonify(
                        {"success": False, "error": "Negative prompt too long (max 2000 chars)"}
                    ),
                    400,
                )

        output = data.get("output")
        if output is not None:
            output = str(output).strip()
            if ".." in output or output.startswith("/"):
                if not Path(output).is_absolute():
                    return jsonify({"success": False, "error": "Invalid output path"}), 400

        lora_paths = data.get("lora_paths")
        lora_weights = data.get("lora_weights")

        job = {
            "id": len(job_history) + job_queue.qsize() + 1,
            "prompt": prompt,
            "status": "queued",
            "submitted_at": datetime.now().isoformat(),
        }

        optional_fields = {
            "seed": seed,
            "steps": steps,
            "width": width,
            "height": height,
            "guidance_scale": guidance_scale,
            "negative_prompt": negative_prompt,
            "output": output,
            "lora_paths": lora_paths if isinstance(lora_paths, list) else None,
            "lora_weights": lora_weights if isinstance(lora_weights, list) else None,
        }
        job.update(_prune_none_fields(optional_fields))

        rate_limit_response = _check_generation_rate_limit()
        if rate_limit_response:
            return rate_limit_response

        job_queue.put(job)

        response = jsonify(
            {
                "id": job["id"],
                "status": job["status"],
                "submitted_at": job["submitted_at"],
                "queue_position": job_queue.qsize(),
                "prompt": job["prompt"],
            }
        )
        response.status_code = 201
        response.headers["Location"] = f"/api/jobs/{job['id']}"
        return response

    except Exception:  # pragma: no cover - defensive
        return jsonify({"error": "Invalid request"}), 400


@generation_bp.route("/themes/random", methods=["GET"])
def get_random_theme_endpoint():
    """Return a random art style theme."""
    try:
        theme = generate_random_theme()
        return jsonify({"theme": theme})
    except Exception as exc:  # pragma: no cover - defensive
        return jsonify({"error": str(exc)}), 500


@generation_bp.route("/albums/<int:album_id>/generate/batch", methods=["POST"])
@require_admin
def generate_batch_from_album(album_id):  # noqa: C901
    """Queue generation jobs for every item in a set-template album."""
    album = db.session.get(Album, album_id)
    if not album:
        return jsonify({"error": "Album not found"}), 404
    if not album.is_set_template:
        return jsonify({"error": "Album is not a set template"}), 400

    data = request.json or {}
    if "user_theme" not in data:
        return jsonify({"error": "user_theme is required"}), 400

    user_theme = str(data["user_theme"]).strip()
    if not user_theme:
        return jsonify({"error": "user_theme cannot be empty"}), 400
    if len(user_theme) > 500:
        return jsonify({"error": "user_theme too long (max 500 chars)"}), 400

    template_items = json.loads(album.csv_data or "[]")
    if not template_items:
        return jsonify({"error": "No template items in album"}), 400

    gen_config = json.loads(album.generation_config or "{}")
    loras = json.loads(album.lora_config or "[]")

    seed = data.get("seed")
    if seed is not None:
        try:
            seed = int(seed)
            if seed < 0 or seed > 2147483647:
                return jsonify({"error": "Seed must be between 0 and 2147483647"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid seed value"}), 400

    steps = data.get("steps")
    if steps is not None:
        try:
            steps = int(steps)
            if steps < 1 or steps > 150:
                return jsonify({"error": "Steps must be between 1 and 150"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid steps value"}), 400

    width = data.get("width")
    if width is None:
        width = gen_config.get("width", 512)
    else:
        try:
            width = int(width)
            if width < 64 or width > 2048 or width % 8 != 0:
                return jsonify({"error": "Width must be between 64-2048 and divisible by 8"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid width value"}), 400

    height = data.get("height")
    if height is None:
        height = gen_config.get("height", 512)
    else:
        try:
            height = int(height)
            if height < 64 or height > 2048 or height % 8 != 0:
                return jsonify({"error": "Height must be between 64-2048 and divisible by 8"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid height value"}), 400

    guidance_scale = data.get("guidance_scale")
    if guidance_scale is not None:
        try:
            guidance_scale = float(guidance_scale)
            if guidance_scale < 0 or guidance_scale > 30:
                return jsonify({"error": "Guidance scale must be between 0 and 30"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid guidance scale value"}), 400

    negative_prompt = data.get("negative_prompt")
    album_negative = gen_config.get("negative_prompt", "")
    if negative_prompt and album_negative:
        negative_prompt = f"{negative_prompt}, {album_negative}"
    elif album_negative:
        negative_prompt = album_negative
    if negative_prompt and len(negative_prompt) > 2000:
        return jsonify({"error": "Negative prompt too long (max 2000 chars)"}), 400

    batch_id = f"{album.name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    config = load_config()
    batch_output_dir = Path(config["output"]["directory"]) / batch_id
    batch_output_dir.mkdir(parents=True, exist_ok=True)

    rate_limit_response = _check_generation_rate_limit()
    if rate_limit_response:
        return rate_limit_response

    job_ids = []
    for item in template_items:
        prompt = construct_prompt(
            base_prompt=album.base_prompt or "",
            user_theme=user_theme,
            csv_data=item,
            prompt_template=album.prompt_template or "",
            style_suffix=album.style_suffix or "",
        )

        if "value" in item and "suit" in item:
            item_name = f"{item['value']}_of_{item['suit']}"
        elif "name" in item:
            item_name = item["name"]
        else:
            item_name = next(iter(item.values())) if item else "item"

        job_id = len(job_history) + job_queue.qsize() + 1
        job = {
            "id": job_id,
            "prompt": prompt,
            "status": "queued",
            "submitted_at": datetime.now().isoformat(),
            "batch_id": batch_id,
            "batch_item_name": item_name,
            "batch_item_data": item,
            "output_dir": str(batch_output_dir),
            "album_id": album.id,
        }

        optional_fields = {
            "seed": seed,
            "steps": steps,
            "width": width,
            "height": height,
            "guidance_scale": guidance_scale,
            "negative_prompt": negative_prompt,
        }

        if loras:
            optional_fields["lora_paths"] = [lora["path"] for lora in loras]
            optional_fields["lora_weights"] = [lora["weight"] for lora in loras]

        job.update(_prune_none_fields(optional_fields))

        job_queue.put(job)
        job_ids.append(job_id)

    return (
        jsonify(
            {
                "message": f"Queued {len(job_ids)} generation jobs",
                "album_id": album.id,
                "album_name": album.name,
                "batch_id": batch_id,
                "job_ids": job_ids,
                "output_dir": str(batch_output_dir),
            }
        ),
        201,
    )


@generation_bp.route("/jobs", methods=["GET"])
def get_jobs():
    """Return job history and queue snapshot."""
    queue_list = list(job_queue.queue)
    return jsonify(
        {
            "current": current_job,
            "queue": queue_list,
            "history": job_history[-50:],
        }
    )


@generation_bp.route("/jobs/<int:job_id>", methods=["GET"])
def get_job(job_id):
    """Return a single job entry."""
    if current_job and current_job["id"] == job_id:
        job_response = {
            **current_job,
            "queue_position": 0,
            "estimated_time_remaining": None,
        }
        return jsonify(job_response)

    position = 1
    for job in list(job_queue.queue):
        if job["id"] == job_id:
            job_response = {
                **job,
                "queue_position": position,
                "estimated_time_remaining": None,
            }
            return jsonify(job_response)
        position += 1

    for job in job_history:
        if job["id"] == job_id:
            if job.get("started_at") and job.get("completed_at"):
                start = datetime.fromisoformat(job["started_at"])
                end = datetime.fromisoformat(job["completed_at"])
                job["duration_seconds"] = (end - start).total_seconds()
            return jsonify(job)

    return jsonify({"error": "Job not found"}), 404


@generation_bp.route("/jobs/<int:job_id>", methods=["DELETE"])
def cancel_job(job_id):
    """Cancel a queued job."""
    global job_queue

    if current_job and current_job["id"] == job_id:
        return jsonify({"error": "Cannot cancel job that is currently running"}), 409

    for job in job_history:
        if job["id"] == job_id:
            return jsonify({"error": "Cannot cancel completed job"}), 410

    queue_list = list(job_queue.queue)
    found = False
    for job in queue_list:
        if job["id"] == job_id:
            job["status"] = "cancelled"
            job["cancelled_at"] = datetime.now().isoformat()
            job_history.append(job)
            found = True
            break

    if found:
        new_queue: queue.Queue[dict] = queue.Queue()
        for job in queue_list:
            if job["id"] != job_id:
                new_queue.put(job)
        job_queue = new_queue
        return jsonify({"message": "Job cancelled successfully"}), 200

    return jsonify({"error": "Job not found"}), 404


@generation_bp.route("/batches", methods=["GET"])
def list_batches():
    """List all batch output directories."""
    try:
        config = load_config()
        output_dir = Path(config["output"]["directory"])

        batches = []
        if output_dir.exists():
            for batch_dir in sorted(output_dir.iterdir(), key=os.path.getmtime, reverse=True):
                if batch_dir.is_dir():
                    image_count = len(list(batch_dir.glob("*.png")))
                    batches.append(
                        {
                            "batch_id": batch_dir.name,
                            "path": str(batch_dir),
                            "image_count": image_count,
                            "created": datetime.fromtimestamp(
                                batch_dir.stat().st_mtime
                            ).isoformat(),
                        }
                    )

        return jsonify({"batches": batches})
    except Exception as exc:  # pragma: no cover - defensive
        return jsonify({"error": str(exc)}), 500


@generation_bp.route("/batches/<batch_id>", methods=["GET"])
def get_batch(batch_id):
    """Return details for a specific generation batch."""
    try:
        if ".." in batch_id or "/" in batch_id or "\\" in batch_id:
            return jsonify({"error": "Invalid batch ID"}), 400

        config = load_config()
        batch_dir = Path(config["output"]["directory"]) / batch_id

        if not batch_dir.exists() or not batch_dir.is_dir():
            return jsonify({"error": "Batch not found"}), 404

        images = []
        for img_file in sorted(batch_dir.glob("*.png"), key=os.path.getmtime):
            metadata_file = img_file.with_suffix(".json")
            metadata = {}
            if metadata_file.exists():
                with open(metadata_file, "r") as handle:
                    metadata = json.load(handle)

            images.append(
                {
                    "filename": img_file.name,
                    "relative_path": f"{batch_id}/{img_file.name}",
                    "download_url": f"/api/outputs/{batch_id}/{img_file.name}",
                    "size": img_file.stat().st_size,
                    "created": datetime.fromtimestamp(img_file.stat().st_mtime).isoformat(),
                    "metadata": metadata,
                }
            )

        return jsonify({"batch_id": batch_id, "image_count": len(images), "images": images})
    except Exception as exc:  # pragma: no cover - defensive
        return jsonify({"error": str(exc)}), 500


@generation_bp.route("/loras", methods=["GET"])
def list_loras():
    """List organized LoRA checkpoints from the index."""
    try:
        config = load_config()
        lora_base_dir = Path(config["model"].get("cache_dir", "/tmp/imagineer/models")) / "lora"
        index_path = lora_base_dir / "index.json"

        if not index_path.exists():
            return jsonify({"loras": []})

        with open(index_path, "r", encoding="utf-8") as handle:
            index = json.load(handle)

        loras = []
        for folder_name, entry in index.items():
            lora_folder = lora_base_dir / folder_name
            preview_path = lora_folder / "preview.png"
            has_preview = preview_path.exists()

            loras.append(
                {
                    "folder": folder_name,
                    "filename": entry.get("filename"),
                    "format": entry.get("format", "sd15"),
                    "compatible": entry.get("compatible", True),
                    "has_preview": has_preview,
                    "has_config": entry.get("has_config", False),
                    "organized_at": entry.get("organized_at"),
                    "default_weight": entry.get("default_weight"),
                }
            )

        loras.sort(key=lambda item: item.get("organized_at", ""), reverse=True)
        return jsonify({"loras": loras})
    except Exception as exc:  # pragma: no cover - defensive
        return jsonify({"error": str(exc)}), 500


@generation_bp.route("/loras/<folder>/preview", methods=["GET"])
def serve_lora_preview(folder):
    """Serve LoRA preview image."""
    try:
        if ".." in folder or "/" in folder or "\\" in folder:
            return jsonify({"error": "Invalid folder name"}), 400

        config = load_config()
        lora_base_dir = Path(config["model"].get("cache_dir", "/tmp/imagineer/models")) / "lora"
        preview_path = lora_base_dir / folder / "preview.png"

        if not preview_path.exists():
            return jsonify({"error": "Preview not found"}), 404

        return send_from_directory(preview_path.parent, preview_path.name)
    except Exception:  # pragma: no cover - defensive
        return jsonify({"error": "Invalid request"}), 400


@generation_bp.route("/loras/<folder>", methods=["GET"])
def get_lora_details(folder):
    """Return metadata for a specific LoRA folder."""
    try:
        if ".." in folder or "/" in folder or "\\" in folder:
            return jsonify({"error": "Invalid folder name"}), 400

        config = load_config()
        lora_base_dir = Path(config["model"].get("cache_dir", "/tmp/imagineer/models")) / "lora"
        lora_folder = lora_base_dir / folder
        config_path = lora_folder / "config.yaml"

        if not lora_folder.exists():
            return jsonify({"error": "LoRA not found"}), 404

        details = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as handle:
                details = yaml.safe_load(handle) or {}

        index_path = lora_base_dir / "index.json"
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as handle:
                index = json.load(handle)
                if folder in index:
                    details.update(index[folder])

        return jsonify(details)
    except Exception as exc:  # pragma: no cover - defensive
        return jsonify({"error": str(exc)}), 500


def get_generation_health() -> dict:
    """Return a snapshot of the generation queue for health checks."""
    return {
        "queue_size": job_queue.qsize(),
        "current_job": current_job is not None,
        "total_completed": len(job_history),
    }
