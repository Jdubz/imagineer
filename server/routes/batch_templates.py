"""
Batch template management endpoints
"""

import json

from flask import Blueprint, abort, jsonify, request

from server.auth import current_user, require_admin
from server.database import BatchGenerationRun, BatchTemplate, db

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


@batch_templates_bp.route("/<int:template_id>/generate", methods=["POST"])
def generate_from_template(template_id: int):
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
    if "album_name" not in data:
        abort(400, description="Missing required field: album_name")
    if "user_theme" not in data:
        abort(400, description="Missing required field: user_theme")

    # Load CSV data
    try:
        csv_items = json.loads(template.csv_data) if template.csv_data else []
    except json.JSONDecodeError:
        abort(500, description="Template has invalid CSV data")

    if not csv_items:
        abort(400, description="Template has no CSV items to generate")

    # Create BatchGenerationRun record
    from datetime import datetime, timezone

    run = BatchGenerationRun(
        template_id=template_id,
        album_name=data["album_name"],
        user_theme=data["user_theme"],
        steps=data.get("steps"),
        seed=data.get("seed"),
        width=data.get("width"),
        height=data.get("height"),
        guidance_scale=data.get("guidance_scale"),
        negative_prompt=data.get("negative_prompt"),
        status="queued",
        total_items=len(csv_items),
        created_by=current_user.email if current_user.is_authenticated else None,
        created_at=datetime.now(timezone.utc),
    )

    db.session.add(run)
    db.session.commit()

    # Return the run record
    # NOTE: Actual job queuing and album creation will be implemented in Phase 2.2
    # For now, this creates the run record and returns it
    return (
        jsonify(
            {
                "run": run.to_dict(),
                "template": template.to_dict(),
                "message": (
                    "Batch generation run created. " "Job queuing to be implemented in Phase 2.2"
                ),
            }
        ),
        202,
    )
