"""
Batch template management endpoints
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, abort, jsonify, request

from server.auth import current_user, require_admin
from server.config_loader import load_config
from server.database import BatchGenerationRun, BatchTemplate, db

# Import from generation routes for job queuing
from server.routes import generation

batch_templates_bp = Blueprint("batch_templates", __name__, url_prefix="/api/batch-templates")


def _is_admin_user() -> bool:
    try:
        return bool(current_user.is_authenticated and current_user.is_admin())
    except Exception:  # pragma: no cover
        return False


def _load_template_or_abort(template_id: int) -> BatchTemplate:
    template = db.session.query(BatchTemplate).filter(BatchTemplate.id == template_id).one_or_none()
    if template is None:
        abort(404, description="Batch template not found")
    return template


@batch_templates_bp.route("", methods=["GET"])
def list_batch_templates():
    """List all batch templates"""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 100)

    query = BatchTemplate.query.order_by(BatchTemplate.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page)

    templates_data = [template.to_dict() for template in pagination.items]

    return jsonify(
        {
            "templates": templates_data,
            "total": pagination.total,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "pages": pagination.pages,
        }
    )


@batch_templates_bp.route("/<int:template_id>", methods=["GET"])
def get_batch_template(template_id: int):
    """Get a specific batch template with full details"""
    template = _load_template_or_abort(template_id)

    template_dict = template.to_dict()

    # Add full CSV data if available
    if template.csv_data:
        try:
            template_dict["csv_items"] = json.loads(template.csv_data)
        except json.JSONDecodeError:
            template_dict["csv_items"] = []

    return jsonify(template_dict)


@batch_templates_bp.route("", methods=["POST"])
@require_admin
def create_batch_template():
    """Create a new batch template (admin only)"""
    data = request.get_json()

    if not data:
        abort(400, description="Request body is required")

    # Validate required fields
    required_fields = ["name", "csv_path", "prompt_template"]
    for field in required_fields:
        if field not in data:
            abort(400, description=f"Missing required field: {field}")

    # Create template
    template = BatchTemplate(
        name=data["name"],
        description=data.get("description"),
        csv_path=data["csv_path"],
        csv_data=json.dumps(data["csv_data"]) if data.get("csv_data") else None,
        base_prompt=data.get("base_prompt"),
        prompt_template=data["prompt_template"],
        style_suffix=data.get("style_suffix"),
        example_theme=data.get("example_theme"),
        width=data.get("width", 512),
        height=data.get("height", 512),
        negative_prompt=data.get("negative_prompt"),
        lora_config=json.dumps(data["lora_config"]) if data.get("lora_config") else None,
        created_by=current_user.email if current_user.is_authenticated else None,
    )

    db.session.add(template)
    db.session.commit()

    return jsonify(template.to_dict()), 201


@batch_templates_bp.route("/<int:template_id>", methods=["PUT"])
@require_admin
def update_batch_template(template_id: int):
    """Update a batch template (admin only)"""
    template = _load_template_or_abort(template_id)
    data = request.get_json()

    if not data:
        abort(400, description="Request body is required")

    # Update fields
    updatable_fields = [
        "name",
        "description",
        "csv_path",
        "base_prompt",
        "prompt_template",
        "style_suffix",
        "example_theme",
        "width",
        "height",
        "negative_prompt",
    ]

    for field in updatable_fields:
        if field in data:
            setattr(template, field, data[field])

    # Handle JSON fields
    if "csv_data" in data:
        template.csv_data = json.dumps(data["csv_data"]) if data["csv_data"] else None

    if "lora_config" in data:
        template.lora_config = json.dumps(data["lora_config"]) if data["lora_config"] else None

    db.session.commit()

    return jsonify(template.to_dict())


@batch_templates_bp.route("/<int:template_id>", methods=["DELETE"])
@require_admin
def delete_batch_template(template_id: int):
    """Delete a batch template (admin only)"""
    template = _load_template_or_abort(template_id)

    # Check if template has generation runs
    run_count = BatchGenerationRun.query.filter_by(template_id=template_id).count()
    if run_count > 0:
        abort(
            400,
            description=(
                f"Cannot delete template with {run_count} generation runs. "
                "Delete runs first or keep template for historical records."
            ),
        )

    db.session.delete(template)
    db.session.commit()

    return jsonify({"message": "Template deleted successfully"}), 200


@batch_templates_bp.route("/<int:template_id>/runs", methods=["GET"])
def list_template_runs(template_id: int):
    """List all generation runs for a template"""
    template = _load_template_or_abort(template_id)

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 100)

    query = BatchGenerationRun.query.filter_by(template_id=template_id).order_by(
        BatchGenerationRun.created_at.desc()
    )

    pagination = query.paginate(page=page, per_page=per_page)

    runs_data = [run.to_dict() for run in pagination.items]

    return jsonify(
        {
            "runs": runs_data,
            "total": pagination.total,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "pages": pagination.pages,
            "template": template.to_dict(),
        }
    )


@batch_templates_bp.route("/<int:template_id>/runs/<int:run_id>", methods=["GET"])
def get_run_status(template_id: int, run_id: int):
    """
    Get the status of a specific generation run

    Returns current progress, status, and album link if completed.
    Use this endpoint for real-time progress polling.
    """
    template = _load_template_or_abort(template_id)

    run = (
        db.session.query(BatchGenerationRun)
        .filter_by(id=run_id, template_id=template_id)
        .one_or_none()
    )

    if not run:
        abort(404, description="Generation run not found")

    return jsonify({"run": run.to_dict(), "template": template.to_dict()})


@batch_templates_bp.route("/<int:template_id>/generate", methods=["POST"])
def generate_from_template(template_id: int):  # noqa: C901
    """
    Generate a batch of images from a template

    This endpoint creates a new BatchGenerationRun and queues jobs for each CSV row.
    Once all jobs complete, an Album will be created automatically.

    Request body:
    {
        "album_name": "My Custom Theme Cards",
        "user_theme": "steampunk aesthetic",
        "steps": 25,  // optional override
        "seed": 42,  // optional override
        "width": 512,  // optional override
        "height": 720,  // optional override
        "guidance_scale": 7.5,  // optional override
        "negative_prompt": "custom negative prompt"  // optional override
    }
    """
    template = _load_template_or_abort(template_id)
    data = request.get_json()

    if not data:
        abort(400, description="Request body is required")

    # Validate required fields
    album_name = data.get("album_name", "").strip()
    if not album_name:
        abort(400, description="Missing required field: album_name")
    if len(album_name) > 200:
        abort(400, description="album_name too long (max 200 chars)")

    user_theme = data.get("user_theme", "").strip()
    if not user_theme:
        abort(400, description="Missing required field: user_theme")
    if len(user_theme) > 500:
        abort(400, description="user_theme too long (max 500 chars)")

    # Validate optional overrides
    seed = data.get("seed")
    if seed is not None:
        try:
            seed = int(seed)
            if seed < 0 or seed > 2147483647:
                abort(400, description="Seed must be between 0 and 2147483647")
        except (ValueError, TypeError):
            abort(400, description="Invalid seed value")

    steps = data.get("steps")
    if steps is not None:
        try:
            steps = int(steps)
            if steps < 1 or steps > 150:
                abort(400, description="Steps must be between 1 and 150")
        except (ValueError, TypeError):
            abort(400, description="Invalid steps value")

    width = data.get("width")
    if width is not None:
        try:
            width = int(width)
            if width < 64 or width > 2048 or width % 8 != 0:
                abort(400, description="Width must be between 64-2048 and divisible by 8")
        except (ValueError, TypeError):
            abort(400, description="Invalid width value")
    else:
        width = template.width  # Use template default

    height = data.get("height")
    if height is not None:
        try:
            height = int(height)
            if height < 64 or height > 2048 or height % 8 != 0:
                abort(400, description="Height must be between 64-2048 and divisible by 8")
        except (ValueError, TypeError):
            abort(400, description="Invalid height value")
    else:
        height = template.height  # Use template default

    guidance_scale = data.get("guidance_scale")
    if guidance_scale is not None:
        try:
            guidance_scale = float(guidance_scale)
            if guidance_scale < 0 or guidance_scale > 30:
                abort(400, description="Guidance scale must be between 0 and 30")
        except (ValueError, TypeError):
            abort(400, description="Invalid guidance scale value")

    # Handle negative prompts (merge template and user overrides)
    negative_prompt = data.get("negative_prompt", "").strip()
    if negative_prompt and template.negative_prompt:
        negative_prompt = f"{negative_prompt}, {template.negative_prompt}"
    elif template.negative_prompt:
        negative_prompt = template.negative_prompt
    if negative_prompt and len(negative_prompt) > 2000:
        abort(400, description="Negative prompt too long (max 2000 chars)")

    # Load CSV data
    try:
        csv_items = json.loads(template.csv_data) if template.csv_data else []
    except json.JSONDecodeError:
        abort(500, description="Template has invalid CSV data")

    if not csv_items:
        abort(400, description="Template has no CSV items to generate")

    # Load LoRA config
    loras = []
    if template.lora_config:
        try:
            loras = json.loads(template.lora_config)
        except json.JSONDecodeError:
            pass  # If invalid, just skip LoRAs

    # Create batch output directory
    config = load_config()
    batch_id = f"{album_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    batch_output_dir = Path(config["output"]["directory"]) / batch_id
    batch_output_dir.mkdir(parents=True, exist_ok=True)

    # Create BatchGenerationRun record
    run = BatchGenerationRun(
        template_id=template_id,
        album_name=album_name,
        user_theme=user_theme,
        steps=steps,
        seed=seed,
        width=width,
        height=height,
        guidance_scale=guidance_scale,
        negative_prompt=negative_prompt,
        status="queued",
        total_items=len(csv_items),
        completed_items=0,
        failed_items=0,
        batch_id=batch_id,
        output_directory=str(batch_output_dir),
        created_by=current_user.email if current_user.is_authenticated else None,
        created_at=datetime.now(timezone.utc),
    )

    db.session.add(run)
    db.session.commit()

    # Queue jobs for each CSV item
    job_ids = []
    for item in csv_items:
        # Construct prompt using template
        prompt = generation.construct_prompt(
            base_prompt=template.base_prompt or "",
            user_theme=user_theme,
            csv_data=item,
            prompt_template=template.prompt_template or "",
            style_suffix=template.style_suffix or "",
        )

        # Determine item name for filename
        if "value" in item and "suit" in item:
            item_name = f"{item['value']}_of_{item['suit']}"
        elif "name" in item:
            item_name = item["name"]
        elif "card" in item:
            item_name = item["card"]
        elif "sign" in item:
            item_name = item["sign"]
        else:
            item_name = next(iter(item.values())) if item else "item"

        # Get next job ID
        job_id = generation._get_next_job_id()

        # Create job dict
        job = {
            "id": job_id,
            "prompt": prompt,
            "status": "queued",
            "submitted_at": datetime.now().isoformat(),
            "batch_id": batch_id,
            "batch_item_name": item_name,
            "batch_item_data": item,
            "output_dir": str(batch_output_dir),
            "batch_generation_run_id": run.id,  # Link to run
        }

        # Add optional parameters
        optional_fields = {
            "seed": seed,
            "steps": steps,
            "width": width,
            "height": height,
            "guidance_scale": guidance_scale,
            "negative_prompt": negative_prompt,
        }

        # Add LoRA configuration
        if loras:
            optional_fields["lora_paths"] = [lora["path"] for lora in loras]
            optional_fields["lora_weights"] = [lora["weight"] for lora in loras]

        job.update(generation._prune_none_fields(optional_fields))

        # Queue the job
        generation.job_queue.put(job)
        job_ids.append(job_id)

    # Update run status to processing (jobs are now queued)
    run.status = "processing"
    run.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return (
        jsonify(
            {
                "run": run.to_dict(),
                "template": template.to_dict(),
                "batch_id": batch_id,
                "job_ids": job_ids,
                "output_dir": str(batch_output_dir),
                "message": f"Queued {len(job_ids)} generation jobs",
            }
        ),
        202,
    )
