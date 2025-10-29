"""
Imagineer API Server
Flask-based REST API for managing image generation
"""

import json
import logging
import mimetypes
import os
import queue
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import yaml
from flask import Flask, abort, jsonify, request, send_from_directory, session, url_for
from flask_cors import CORS
from flask_login import current_user, login_user, logout_user
from flask_talisman import Talisman
from werkzeug.middleware.proxy_fix import ProxyFix

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure mimetypes are initialized before any monkeypatching in tests
mimetypes.init()

# Import auth module
from server.auth import (  # noqa: E402
    ROLE_ADMIN,
    User,
    get_user_role,
    init_auth,
    load_users,
    require_admin,
    save_users,
)
from server.database import (  # noqa: E402
    Album,
    AlbumImage,
    Image,
    Label,
    ScrapeJob,
    TrainingRun,
    db,
    init_database,
)
from server.logging_config import configure_logging  # noqa: E402
from server.tasks.labeling import label_album_task, label_image_task  # noqa: E402
from server.utils.rate_limiter import is_rate_limit_exceeded  # noqa: E402

app = Flask(__name__, static_folder="../public", static_url_path="")

# Configure ProxyFix to trust proxy headers (for HTTPS detection behind reverse proxy)
# This ensures url_for(_external=True) generates https:// URLs in production
if os.environ.get("FLASK_ENV") == "production":
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,  # Trust X-Forwarded-For
        x_proto=1,  # Trust X-Forwarded-Proto (http/https)
        x_host=1,  # Trust X-Forwarded-Host
        x_prefix=1,  # Trust X-Forwarded-Prefix
    )
    # Force HTTPS scheme for URL generation
    app.config["PREFERRED_URL_SCHEME"] = "https"

# Configure database
# Use absolute path to ensure consistency
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "instance", "imagineer.db"))
database_url = os.environ.get("DATABASE_URL")
if os.environ.get("FLASK_ENV") == "production" and not database_url:
    raise RuntimeError(
        "DATABASE_URL must be configured in production. "
        "Point it at a persistent PostgreSQL or MySQL instance for SD 1.5 training metadata."
    )
app.config["SQLALCHEMY_DATABASE_URI"] = database_url or f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Configure CORS with environment-based origins
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "").split(",")
if not ALLOWED_ORIGINS or ALLOWED_ORIGINS == [""]:
    # Only allow localhost in development mode
    if os.environ.get("FLASK_ENV") == "development":
        ALLOWED_ORIGINS = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]
    else:
        # Production: require explicit CORS configuration
        ALLOWED_ORIGINS = []

CORS(
    app,
    resources={r"/api/*": {"origins": ALLOWED_ORIGINS}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "DELETE"],
)

# Configure security headers
if os.environ.get("FLASK_ENV") == "production":
    Talisman(
        app,
        force_https=True,
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,
        content_security_policy={
            "default-src": "'self'",
            "script-src": ["'self'", "'unsafe-inline'", "accounts.google.com"],
            "style-src": ["'self'", "'unsafe-inline'"],
            "img-src": ["'self'", "data:", "*.googleusercontent.com"],
            "connect-src": ["'self'"],
            "frame-src": ["accounts.google.com"],  # Allow Google OAuth iframe
        },
        frame_options="SAMEORIGIN",  # Allow same-origin frames for OAuth
        content_security_policy_nonce_in=["script-src"],
    )

# Initialize authentication
oauth, google = init_auth(app)

# Configure logging
logger = configure_logging(app)

# Initialize database
init_database(app)

# Initialize Celery
from server.celery_app import make_celery  # noqa: E402

celery = make_celery(app)

# Register blueprints
from server.routes.images import images_bp, outputs_bp  # noqa: E402
from server.routes.scraping import scraping_bp  # noqa: E402
from server.routes.training import training_bp  # noqa: E402

app.register_blueprint(images_bp)
app.register_blueprint(outputs_bp)
app.register_blueprint(scraping_bp)
app.register_blueprint(training_bp)

# ============================================================================
# Generation Endpoint Safeguards
# ============================================================================

GENERATION_RATE_LIMIT = int(os.environ.get("IMAGINEER_GENERATE_LIMIT", "10"))
GENERATION_RATE_WINDOW_SECONDS = int(os.environ.get("IMAGINEER_GENERATE_WINDOW_SECONDS", "60"))


def _check_generation_rate_limit():
    """Apply a simple per-user rate limit for generation endpoints."""
    if GENERATION_RATE_LIMIT <= 0 or GENERATION_RATE_WINDOW_SECONDS <= 0:
        return None

    identifier = getattr(current_user, "email", None) or request.remote_addr or "anonymous"
    exceeded = is_rate_limit_exceeded(
        "generate",
        identifier,
        GENERATION_RATE_LIMIT,
        GENERATION_RATE_WINDOW_SECONDS,
    )

    if exceeded:
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
        response.headers["Retry-After"] = str(GENERATION_RATE_WINDOW_SECONDS)
        return response, 429

    return None


# Add request timing and performance logging
@app.before_request
def before_request():
    """Log request start and set timing"""
    from flask import g

    g.start_time = time.time()


@app.after_request
def after_request(response):
    """Log request completion with timing and status"""
    import time

    from flask import g, request

    # Calculate request duration
    duration_ms = 0
    if hasattr(g, "start_time"):
        duration_ms = int((time.time() - g.start_time) * 1000)

    # Log request completion
    logger.info(
        f"Request completed: {request.method} {request.path}",
        extra={
            "operation": "request_completed",
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )

    return response


# Add specific error handlers
@app.errorhandler(404)
def handle_404(e):
    """Handle 404 errors"""
    logger.warning(
        f"404 Not Found: {request.method} {request.url}",
        extra={
            "operation": "error_404",
            "path": request.path,
            "url": request.url,
            "referrer": request.referrer,
        },
    )
    return jsonify({"error": "Not found", "path": request.path}), 404


@app.errorhandler(500)
def handle_500(e):
    """Handle 500 errors"""
    logger.error(
        f"Internal server error: {e}",
        exc_info=True,
        extra={"operation": "error_500"},
    )
    return jsonify({"error": "Internal server error"}), 500


# ============================================================================
# Authentication Routes
# ============================================================================


@app.route("/api/auth/login")
@app.route("/auth/login")
def auth_login():
    """Initiate Google OAuth flow"""
    try:
        # Ensure redirect URI uses /api/ prefix for consistency
        redirect_uri = url_for("auth_callback", _external=True)

        # Force /api/ prefix if it's missing (use urlparse for safe path manipulation)
        parsed = urlparse(redirect_uri)
        if parsed.path == "/auth/google/callback":
            # Replace path with /api/ prefix
            parsed = parsed._replace(path="/api/auth/google/callback")
            redirect_uri = urlunparse(parsed)

        logger.info(f"OAuth login initiated. Redirect URI: {redirect_uri}")

        target = request.args.get("state") or request.args.get("next") or "/"
        session["login_redirect"] = target
        return google.authorize_redirect(redirect_uri)
    except Exception as e:
        logger.error(f"OAuth login error: {e}", exc_info=True)
        return jsonify({"error": "Failed to initiate OAuth login", "details": str(e)}), 500


@app.route("/api/auth/google/callback")
@app.route("/auth/google/callback")
def auth_callback():
    """Handle Google OAuth callback"""
    try:
        # Get token from Google
        token = google.authorize_access_token()

        # Get user info from Google
        user_info = token.get("userinfo")
        if not user_info:
            return jsonify({"error": "Failed to get user info"}), 400

        # Get user role from users.json
        email = user_info.get("email")
        role = get_user_role(email)

        # Create user object
        user = User(
            email=email,
            name=user_info.get("name", ""),
            picture=user_info.get("picture", ""),
            role=role,
        )

        # Store user data in session
        session["user"] = {
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
            "role": user.role,
        }
        session.permanent = True

        # Log in user with Flask-Login
        login_user(user)

        # Log successful authentication
        security_logger = logging.getLogger("security")
        security_logger.info(
            f"Successful login: {user.email}",
            extra={
                "event": "authentication_success",
                "user_email": user.email,
                "role": user.role,
            },
        )

        # Close the OAuth popup window and notify the opener
        return """
        <html>
            <head><title>Login Successful</title></head>
            <body>
                <script>
                    if (window.opener && typeof window.opener.postMessage === 'function') {
                        window.opener.postMessage(
                            { type: 'imagineer-auth-success' },
                            window.location.origin
                        );
                    }
                    // Close the popup window
                    window.close();
                    // Fallback if window.close() is blocked
                    setTimeout(function() {
                        var msg = '<h2>Login successful! You can close this window.</h2>';
                        document.body.innerHTML = msg;
                    }, 100);
                </script>
                <p>Login successful! Closing window...</p>
            </body>
        </html>
        """

    except Exception as e:
        logger.error(f"OAuth callback error: {e}", exc_info=True)
        security_logger = logging.getLogger("security")
        security_logger.warning(
            "Failed login attempt", extra={"event": "authentication_failure", "error": str(e)}
        )
        return jsonify({"error": "Authentication failed"}), 500


@app.route("/api/auth/google/<path:anomalous_path>")
def auth_callback_path_anomaly(anomalous_path, *, allow_callback: bool = False):
    """Handle OAuth callbacks that arrive on mis-encoded paths.

    Some reverse proxy deployments have reported Google returning to
    ``/api/auth/google/%2F<redirect>`` (double-encoded slash plus redirect URI),
    which the canonical callback route does not match and would therefore
    log a 404. When the request still contains an OAuth ``code`` parameter,
    treat it as a legitimate callback and process it normally.
    """

    normalized = anomalous_path.lstrip("/").rstrip("/")

    # Allow the canonical callback handler to process the standard routes.
    if normalized in {"callback", ""} and not allow_callback:
        abort(404)

    if "code" not in request.args:
        logger.warning(
            "Discarding unexpected Google OAuth path without code parameter",
            extra={
                "operation": "oauth_path_anomaly",
                "path": request.path,
                "query": request.query_string.decode("utf-8", errors="ignore"),
            },
        )
        return jsonify({"error": "Invalid OAuth callback"}), 400

    logger.warning(
        "Recovered Google OAuth callback from unexpected path",
        extra={
            "operation": "oauth_path_anomaly_recovered",
            "path": request.path,
            "normalized": normalized,
            "query": request.query_string.decode("utf-8", errors="ignore"),
        },
    )
    return auth_callback()


@app.before_request
def reroute_google_oauth_path_anomalies():
    """Intercept double-slashed Google OAuth callbacks before routing resolves."""

    path = request.path
    anomaly_prefix = "/api/auth/google//"

    if path.startswith(anomaly_prefix):
        anomalous_path = path[len("/api/auth/google/") :]  # Preserve leading slash for logging
        return auth_callback_path_anomaly(anomalous_path, allow_callback=True)


@app.route("/api/auth/logout")
@app.route("/auth/logout")
def auth_logout():
    """Logout user"""
    logout_user()
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"})


@app.route("/api/auth/me")
@app.route("/auth/me")
def auth_me():
    """Get current user info"""
    try:
        if current_user.is_authenticated:
            return jsonify(
                {
                    "authenticated": True,
                    "email": current_user.email,
                    "name": current_user.name,
                    "picture": current_user.picture,
                    "role": current_user.role,
                    "is_admin": current_user.is_admin(),
                }
            )

        return jsonify({"authenticated": False})

    except Exception as exc:  # pragma: no cover - defensive guardrail
        logger.error("Auth status check failed: %s", exc, exc_info=True)
        return (
            jsonify(
                {
                    "authenticated": False,
                    "error": "AUTH_STATUS_ERROR",
                    "message": "Failed to determine authentication status.",
                }
            ),
            500,
        )


# ============================================================================
# Configuration
# ============================================================================

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
VENV_PYTHON = PROJECT_ROOT / "venv" / "bin" / "python"
GENERATE_SCRIPT = PROJECT_ROOT / "examples" / "generate.py"

# Job queue
job_queue = queue.Queue()
job_history = []
current_job = None


def load_config():
    """Load config.yaml"""
    try:
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        # Fallback config for CI environments
        logger.info("Config file not found, using fallback config for CI")
        config = {
            "model": {"cache_dir": "/tmp/imagineer/models"},
            "outputs": {"base_dir": "/tmp/imagineer/outputs"},
            "output": {"directory": "/tmp/imagineer/outputs"},
            "generation": {"width": 512, "height": 512, "steps": 30},
            "training": {
                "checkpoint_dir": "/tmp/imagineer/checkpoints",
                "learning_rate": 1e-5,
                "max_train_steps": 1000,
                "lora": {"rank": 4, "alpha": 32, "dropout": 0.1},
            },
            "dataset": {"data_dir": "/tmp/imagineer/data/training"},
        }

    return config


def save_config(config):
    """Save config.yaml"""
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def construct_prompt(base_prompt, user_theme, csv_data, prompt_template, style_suffix):
    """Construct the final prompt from components

    Order: [Base] [User Theme] [CSV Data via Template] [Style Suffix]
    This order follows Stable Diffusion best practices where front words have strongest influence.

    Args:
        base_prompt: Base description (e.g., "A single playing card")
        user_theme: User's art style theme (e.g., "barnyard animals under a full moon")
        csv_data: Dict of CSV row data
        prompt_template: Template string with {column} placeholders
        style_suffix: Technical/style refinement terms

    Returns:
        Complete prompt string
    """
    # Replace placeholders in template with CSV data
    csv_text = prompt_template
    for key, value in csv_data.items():
        csv_text = csv_text.replace(f"{{{key}}}", value)

    # Construct final prompt with optimal ordering
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
    """Generate a random art style theme for inspiration

    Returns:
        A random theme string
    """
    import random

    # Art styles
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

    # Settings/environments
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

    # Lighting/mood
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

    # Color palettes
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

    # Construct random theme
    style = random.choice(styles)
    environment = random.choice(environments)
    mood = random.choice(moods)
    color = random.choice(colors)

    # Randomly choose 2-3 components
    components = random.sample([f"{style} style", environment, mood, color], k=random.randint(2, 3))

    return ", ".join(components)


def process_jobs():  # noqa: C901
    """Background worker to process generation jobs"""
    global current_job

    while True:
        job = job_queue.get()
        if job is None:
            break

        current_job = job
        job["status"] = "running"
        job["started_at"] = datetime.now().isoformat()

        try:
            # Build command
            cmd = [str(VENV_PYTHON), str(GENERATE_SCRIPT), "--prompt", job["prompt"]]

            # Add optional parameters
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
            # Handle LoRAs
            if job.get("lora_paths") and job.get("lora_weights"):
                cmd.extend(["--lora-paths"] + job["lora_paths"])
                cmd.extend(["--lora-weights"] + [str(w) for w in job["lora_weights"]])

            # Handle output path
            if job.get("output"):
                # Direct output path specified (e.g., for preview generation)
                cmd.extend(["--output", job["output"]])
            elif job.get("output_dir") and job.get("batch_item_name"):
                # For batch jobs, specify output directory
                safe_name = "".join(
                    c for c in job["batch_item_name"] if c.isalnum() or c in (" ", "_", "-")
                ).strip()
                safe_name = safe_name.replace(" ", "_")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = Path(job["output_dir"]) / f"{timestamp}_{safe_name}.png"
                cmd.extend(["--output", str(output_path)])

            # Run generation
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)

            if result.returncode == 0:
                job["status"] = "completed"
                job["output"] = result.stdout
                # Extract output path from stdout
                for line in result.stdout.split("\n"):
                    if "Image saved to:" in line:
                        job["output_path"] = line.split("Image saved to:")[1].strip()
            else:
                job["status"] = "failed"
                job["error"] = result.stderr

        except Exception as e:
            job["status"] = "failed"
            job["error"] = str(e)

        job["completed_at"] = datetime.now().isoformat()
        job_history.append(job)
        current_job = None
        job_queue.task_done()


# Start background worker
worker_thread = threading.Thread(target=process_jobs, daemon=True)
worker_thread.start()


@app.route("/")
def index():
    """Serve the web UI"""
    return send_from_directory("../public", "index.html")


@app.route("/api/config", methods=["GET"])
def get_config():
    """Get current configuration"""
    config = load_config()
    return jsonify(config)


@app.route("/api/config", methods=["PUT"])
def update_config():
    """Update configuration - DANGEROUS: Allows full config replacement"""
    try:
        new_config = request.json

        if not new_config or not isinstance(new_config, dict):
            return jsonify({"success": False, "error": "Invalid configuration"}), 400

        # Security: Validate required keys exist
        required_keys = ["model", "generation", "output"]
        for key in required_keys:
            if key not in new_config:
                return jsonify({"success": False, "error": f"Missing required key: {key}"}), 400

        # Validate paths don't escape project directory
        if "output" in new_config and "directory" in new_config["output"]:
            output_path = Path(new_config["output"]["directory"])
            # Only allow absolute paths or paths within reasonable locations
            if ".." in str(output_path):
                return jsonify({"success": False, "error": "Invalid output directory path"}), 400

        save_config(new_config)
        return jsonify({"success": True, "message": "Configuration updated"})
    except Exception:
        return jsonify({"success": False, "error": "Failed to update configuration"}), 400


@app.route("/api/config/generation", methods=["PUT"])
def update_generation_config():
    """Update just the generation settings"""
    try:
        updates = request.json

        if not updates or not isinstance(updates, dict):
            return jsonify({"success": False, "error": "Invalid data"}), 400

        # Security: Only allow specific generation parameters
        allowed_keys = [
            "width",
            "height",
            "steps",
            "guidance_scale",
            "negative_prompt",
            "batch_size",
            "num_images",
        ]
        for key in updates.keys():
            if key not in allowed_keys:
                return jsonify({"success": False, "error": f"Invalid parameter: {key}"}), 400

        config = load_config()
        config["generation"].update(updates)
        save_config(config)
        return jsonify({"success": True, "config": config["generation"]})
    except Exception:
        return jsonify({"success": False, "error": "Failed to update generation config"}), 400


@app.route("/api/generate", methods=["POST"])
@require_admin
def generate():  # noqa: C901
    """Submit a new image generation job"""
    try:
        data = request.json

        if not data or not data.get("prompt"):
            return jsonify({"success": False, "error": "Prompt is required"}), 400

        # Validate prompt length
        prompt = str(data["prompt"]).strip()
        if not prompt:
            return jsonify({"success": False, "error": "Prompt is required"}), 400
        if len(prompt) > 2000:
            return jsonify({"success": False, "error": "Prompt too long (max 2000 chars)"}), 400

        # Validate and sanitize integer parameters
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

        # Handle output path
        output = data.get("output")
        if output is not None:
            output = str(output).strip()
            # Security: Validate output path doesn't escape allowed directories
            if ".." in output or output.startswith("/"):
                if not Path(output).is_absolute():
                    return jsonify({"success": False, "error": "Invalid output path"}), 400

        # Handle LoRA paths and weights
        lora_paths = data.get("lora_paths")
        lora_weights = data.get("lora_weights")

        job = {
            "id": len(job_history) + job_queue.qsize() + 1,
            "prompt": prompt,
            "seed": seed,
            "steps": steps,
            "width": width,
            "height": height,
            "guidance_scale": guidance_scale,
            "negative_prompt": negative_prompt,
            "output": output,
            "lora_paths": lora_paths,
            "lora_weights": lora_weights,
            "status": "queued",
            "submitted_at": datetime.now().isoformat(),
        }

        rate_limit_response = _check_generation_rate_limit()
        if rate_limit_response:
            return rate_limit_response

        job_queue.put(job)

        # Return 201 Created with Location header pointing to job status
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

    except Exception:
        return jsonify({"error": "Invalid request"}), 400


@app.route("/api/themes/random", methods=["GET"])
def get_random_theme():
    """Generate a random art style theme for inspiration"""
    try:
        theme = generate_random_theme()
        return jsonify({"theme": theme})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/albums/<int:album_id>/generate/batch", methods=["POST"])
@require_admin
def generate_batch_from_album(album_id):
    """Generate all items from a set template album

    Request JSON:
        user_theme: User's art style theme (required)
        seed: Random seed (optional)
        steps: Number of steps (optional)
        width: Image width (optional, defaults to album config)
        height: Image height (optional, defaults to album config)
        guidance_scale: Guidance scale (optional)
        negative_prompt: Negative prompt (optional, appended to album's)

    Returns:
        JSON with queued job IDs and batch info
    """
    # Get album
    album = db.session.get(Album, album_id)
    if not album:
        return jsonify({"error": "Album not found"}), 404

    if not album.is_set_template:
        return jsonify({"error": "Album is not a set template"}), 400

    # Validate user_theme
    data = request.json or {}
    if "user_theme" not in data:
        return jsonify({"error": "user_theme is required"}), 400

    user_theme = str(data["user_theme"]).strip()
    if not user_theme:
        return jsonify({"error": "user_theme cannot be empty"}), 400
    if len(user_theme) > 500:
        return jsonify({"error": "user_theme too long (max 500 chars)"}), 400

    # Parse template items
    template_items = json.loads(album.csv_data or "[]")
    if not template_items:
        return jsonify({"error": "No template items in album"}), 400

    # Parse album configuration
    gen_config = json.loads(album.generation_config or "{}")
    loras = json.loads(album.lora_config or "[]")

    # Get optional parameters
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

    # Create batch ID and output subfolder
    batch_id = f"{album.name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    config = load_config()
    batch_output_dir = Path(config["output"]["directory"]) / batch_id
    batch_output_dir.mkdir(parents=True, exist_ok=True)

    # Check rate limit
    rate_limit_response = _check_generation_rate_limit()
    if rate_limit_response:
        return rate_limit_response

    # Queue generation jobs
    job_ids = []
    for item in template_items:
        # Build prompt from template
        prompt = construct_prompt(
            base_prompt=album.base_prompt or "",
            user_theme=user_theme,
            csv_data=item,
            prompt_template=album.prompt_template or "",
            style_suffix=album.style_suffix or "",
        )

        # Create item name from CSV data
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
            "seed": seed,
            "steps": steps,
            "width": width,
            "height": height,
            "guidance_scale": guidance_scale,
            "negative_prompt": negative_prompt,
            "status": "queued",
            "submitted_at": datetime.now().isoformat(),
            "batch_id": batch_id,
            "batch_item_name": item_name,
            "batch_item_data": item,
            "output_dir": str(batch_output_dir),
            "album_id": album.id,  # Link to source album
        }

        # Add LoRA configuration
        if loras:
            job["lora_paths"] = [lora["path"] for lora in loras]
            job["lora_weights"] = [lora["weight"] for lora in loras]

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


@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    """Get job history and current queue"""
    queue_list = list(job_queue.queue)

    return jsonify(
        {
            "current": current_job,
            "queue": queue_list,
            "history": job_history[-50:],  # Last 50 jobs
        }
    )


@app.route("/api/jobs/<int:job_id>", methods=["GET"])
def get_job(job_id):
    """Get specific job details"""
    # Check current job
    if current_job and current_job["id"] == job_id:
        job_response = {
            **current_job,
            "queue_position": 0,  # Currently running
            "estimated_time_remaining": None,  # Could calculate based on steps
        }
        return jsonify(job_response)

    # Check queue
    position = 1
    for job in list(job_queue.queue):
        if job["id"] == job_id:
            job_response = {
                **job,
                "queue_position": position,
                "estimated_time_remaining": None,  # Could estimate based on position
            }
            return jsonify(job_response)
        position += 1

    # Check history
    for job in job_history:
        if job["id"] == job_id:
            # Add duration if completed
            if job.get("started_at") and job.get("completed_at"):
                start = datetime.fromisoformat(job["started_at"])
                end = datetime.fromisoformat(job["completed_at"])
                job["duration_seconds"] = (end - start).total_seconds()
            return jsonify(job)

    return jsonify({"error": "Job not found"}), 404


@app.route("/api/jobs/<int:job_id>", methods=["DELETE"])
def cancel_job(job_id):
    """Cancel a queued job"""
    global job_queue

    # Cannot cancel currently running job
    if current_job and current_job["id"] == job_id:
        return jsonify({"error": "Cannot cancel job that is currently running"}), 409

    # Cannot cancel completed job
    for job in job_history:
        if job["id"] == job_id:
            return jsonify({"error": "Cannot cancel completed job"}), 410

    # Try to remove from queue
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
        # Rebuild queue without cancelled job
        new_queue = queue.Queue()
        for job in queue_list:
            if job["id"] != job_id:
                new_queue.put(job)

        # Replace the queue
        job_queue = new_queue

        return jsonify({"message": "Job cancelled successfully"}), 200

    return jsonify({"error": "Job not found"}), 404


@app.route("/api/batches", methods=["GET"])
def list_batches():
    """List all batch output directories"""
    try:
        config = load_config()
        output_dir = Path(config["output"]["directory"])

        batches = []
        if output_dir.exists():
            # Find all subdirectories (batches)
            for batch_dir in sorted(output_dir.iterdir(), key=os.path.getmtime, reverse=True):
                if batch_dir.is_dir():
                    # Count images in batch
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

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/batches/<batch_id>", methods=["GET"])
def get_batch(batch_id):
    """Get images from a specific batch"""
    try:
        # Security: Validate batch_id to prevent path traversal
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
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)

            images.append(
                {
                    "filename": img_file.name,
                    "path": str(img_file),
                    "relative_path": f"{batch_id}/{img_file.name}",
                    "size": img_file.stat().st_size,
                    "created": datetime.fromtimestamp(img_file.stat().st_mtime).isoformat(),
                    "metadata": metadata,
                }
            )

        return jsonify({"batch_id": batch_id, "image_count": len(images), "images": images})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify(
        {
            "status": "ok",
            "queue_size": job_queue.qsize(),
            "current_job": current_job is not None,
            "total_completed": len(job_history),
        }
    )


@app.route("/api/loras", methods=["GET"])
def list_loras():
    """List all organized LoRAs from index"""
    try:
        config = load_config()
        lora_base_dir = Path(config["model"].get("cache_dir", "/tmp/imagineer/models")) / "lora"
        index_path = lora_base_dir / "index.json"

        if not index_path.exists():
            return jsonify({"loras": []})

        with open(index_path, "r") as f:
            index = json.load(f)

        loras = []
        for folder_name, entry in index.items():
            lora_folder = lora_base_dir / folder_name
            preview_path = lora_folder / "preview.png"

            # Check for actual preview file existence instead of trusting the index
            has_preview = preview_path.exists()

            loras.append(
                {
                    "folder": folder_name,
                    "filename": entry.get("filename"),
                    "format": entry.get("format", "sd15"),
                    "compatible": entry.get("compatible", True),
                    "has_preview": has_preview,  # Use actual file existence
                    "has_config": entry.get("has_config", False),
                    "organized_at": entry.get("organized_at"),
                    "default_weight": entry.get("default_weight"),
                }
            )

        # Sort by most recently organized
        loras.sort(key=lambda x: x.get("organized_at", ""), reverse=True)

        return jsonify({"loras": loras})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/loras/<folder>/preview", methods=["GET"])
def serve_lora_preview(folder):
    """Serve LoRA preview image"""
    try:
        # Security: Validate folder name to prevent path traversal
        if ".." in folder or "/" in folder or "\\" in folder:
            return jsonify({"error": "Invalid folder name"}), 400

        config = load_config()
        lora_base_dir = Path(config["model"].get("cache_dir", "/tmp/imagineer/models")) / "lora"
        preview_path = lora_base_dir / folder / "preview.png"

        if not preview_path.exists():
            return jsonify({"error": "Preview not found"}), 404

        return send_from_directory(preview_path.parent, preview_path.name)

    except Exception:
        return jsonify({"error": "Invalid request"}), 400


@app.route("/api/loras/<folder>", methods=["GET"])
def get_lora_details(folder):
    """Get detailed information about a specific LoRA"""
    try:
        # Security: Validate folder name
        if ".." in folder or "/" in folder or "\\" in folder:
            return jsonify({"error": "Invalid folder name"}), 400

        config = load_config()
        lora_base_dir = Path(config["model"].get("cache_dir", "/tmp/imagineer/models")) / "lora"
        lora_folder = lora_base_dir / folder
        config_path = lora_folder / "config.yaml"

        if not lora_folder.exists():
            return jsonify({"error": "LoRA not found"}), 404

        details = {}

        # Load config if it exists
        if config_path.exists():
            with open(config_path, "r") as f:
                details = yaml.safe_load(f) or {}

        # Add index info
        index_path = lora_base_dir / "index.json"
        if index_path.exists():
            with open(index_path, "r") as f:
                index = json.load(f)
                if folder in index:
                    details.update(index[folder])

        return jsonify(details)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Database API Endpoints
# ============================================================================


@app.route("/api/albums", methods=["GET"])
def get_albums():
    """Get all albums (public endpoint with pagination)"""
    try:
        logger.info("Fetching public albums", extra={"operation": "get_albums"})

        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 50, type=int), 100)

        # Query public albums with pagination
        query = Album.query.filter_by(is_public=True).order_by(Album.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page)

        album_count = pagination.total
        logger.info(
            f"Retrieved {album_count} public albums",
            extra={"operation": "get_albums", "album_count": album_count},
        )

        return jsonify(
            {
                "albums": [album.to_dict() for album in pagination.items],
                "total": pagination.total,
                "page": page,
                "per_page": per_page,
                "pages": pagination.pages,
            }
        )
    except Exception as e:
        logger.error(
            f"Error getting albums: {e}",
            exc_info=True,
            extra={"operation": "get_albums", "error_type": type(e).__name__},
        )
        return jsonify({"error": "Failed to get albums"}), 500


@app.route("/api/albums/<int:album_id>", methods=["GET"])
def get_album(album_id):
    """Get specific album with images (public endpoint)"""
    try:
        album = Album.query.get(album_id)
        if not album:
            return jsonify({"error": "Album not found"}), 404
        if not album.is_public:
            return jsonify({"error": "Album not found"}), 404

        album_data = album.to_dict()

        # Get images in this album
        album_images = (
            AlbumImage.query.filter_by(album_id=album_id).order_by(AlbumImage.sort_order).all()
        )
        images = []
        for album_image in album_images:
            image_data = album_image.image.to_dict()
            images.append(image_data)

        album_data["images"] = images
        return jsonify(album_data)
    except Exception as e:
        logger.error(f"Error getting album {album_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to get album"}), 500


# Admin album endpoints
@app.route("/api/albums", methods=["POST"])
@require_admin
def create_album():
    """Create new album (admin only)"""
    try:
        data = request.json

        album = Album(
            name=data["name"],
            description=data.get("description", ""),
            album_type=data.get("album_type", "manual"),
            is_public=data.get("is_public", True),
            generation_prompt=data.get("generation_prompt"),
            generation_config=data.get("generation_config"),
        )

        db.session.add(album)
        db.session.commit()

        logger.info(
            f"Created album: {album.name}",
            extra={"operation": "create_album", "album_id": album.id},
        )
        return jsonify(album.to_dict()), 201
    except Exception as e:
        logger.error(f"Error creating album: {e}", exc_info=True)
        return jsonify({"error": "Failed to create album"}), 500


@app.route("/api/albums/<int:album_id>", methods=["PUT"])
@require_admin
def update_album(album_id):
    """Update album (admin only)"""
    try:
        album = Album.query.get_or_404(album_id)
        data = request.json

        if "name" in data:
            album.name = data["name"]
        if "description" in data:
            album.description = data["description"]
        if "album_type" in data:
            album.album_type = data["album_type"]
        if "is_public" in data:
            album.is_public = data["is_public"]
        if "generation_prompt" in data:
            album.generation_prompt = data["generation_prompt"]
        if "generation_config" in data:
            album.generation_config = data["generation_config"]

        db.session.commit()

        logger.info(
            f"Updated album: {album.name}",
            extra={"operation": "update_album", "album_id": album.id},
        )
        return jsonify(album.to_dict())
    except Exception as e:
        logger.error(f"Error updating album {album_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to update album"}), 500


@app.route("/api/albums/<int:album_id>", methods=["DELETE"])
@require_admin
def delete_album(album_id):
    """Delete album (admin only)"""
    try:
        album = Album.query.get_or_404(album_id)

        db.session.delete(album)
        db.session.commit()

        logger.info(
            f"Deleted album: {album.name}",
            extra={"operation": "delete_album", "album_id": album_id},
        )
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error deleting album {album_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to delete album"}), 500


@app.route("/api/albums/<int:album_id>/images", methods=["POST"])
@require_admin
def add_images_to_album(album_id):
    """Add images to album (admin only)"""
    try:
        album = Album.query.get_or_404(album_id)
        data = request.json

        image_ids = data.get("image_ids", [])

        for image_id in image_ids:
            # Check if already in album
            existing = AlbumImage.query.filter_by(album_id=album_id, image_id=image_id).first()

            if not existing:
                assoc = AlbumImage(
                    album_id=album_id, image_id=image_id, sort_order=len(album.album_images) + 1
                )
                db.session.add(assoc)

        db.session.commit()

        logger.info(
            f"Added {len(image_ids)} images to album {album.name}",
            extra={
                "operation": "add_images_to_album",
                "album_id": album_id,
                "image_count": len(image_ids),
            },
        )
        return jsonify({"success": True, "added_count": len(image_ids)})
    except Exception as e:
        logger.error(f"Error adding images to album {album_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to add images to album"}), 500


@app.route("/api/albums/<int:album_id>/images/<int:image_id>", methods=["DELETE"])
@require_admin
def remove_image_from_album(album_id, image_id):
    """Remove image from album (admin only)"""
    try:
        assoc = AlbumImage.query.filter_by(album_id=album_id, image_id=image_id).first_or_404()

        db.session.delete(assoc)
        db.session.commit()

        logger.info(
            f"Removed image {image_id} from album {album_id}",
            extra={
                "operation": "remove_image_from_album",
                "album_id": album_id,
                "image_id": image_id,
            },
        )
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error removing image {image_id} from album {album_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to remove image from album"}), 500


@app.route("/api/labeling/image/<int:image_id>", methods=["POST"])
@require_admin
def label_image(image_id):
    """Trigger AI labeling for single image (admin only)"""
    data = request.get_json(silent=True) or {}
    prompt_type = data.get("prompt_type", "default")

    # Ensure image exists before queuing task
    image = db.session.get(Image, image_id)
    if image is None:
        abort(404)

    task = label_image_task.delay(image_id=image_id, prompt_type=prompt_type)

    logger.info(
        "Queued labeling task for image %s",
        image_id,
        extra={
            "operation": "label_image",
            "image_id": image_id,
            "prompt_type": prompt_type,
            "task_id": task.id,
        },
    )

    return jsonify({"status": "queued", "task_id": task.id}), 202


@app.route("/api/labeling/album/<int:album_id>", methods=["POST"])
@require_admin
def label_album(album_id):
    """Trigger AI labeling for entire album (admin only)"""
    data = request.get_json(silent=True) or {}
    prompt_type = data.get("prompt_type", "sd_training")
    force = data.get("force", False)

    # Ensure album exists before queuing work
    album = db.session.get(Album, album_id)
    if album is None:
        abort(404)

    album_images = AlbumImage.query.filter_by(album_id=album_id).all()
    images = [assoc.image for assoc in album_images if assoc.image]

    if not images:
        return jsonify({"error": "Album is empty"}), 400

    if not force and all(image.labels for image in images):
        return jsonify({"error": "All images already labeled"}), 400

    task = label_album_task.delay(album_id=album_id, prompt_type=prompt_type, force=force)

    logger.info(
        "Queued album labeling task %s for album %s",
        task.id,
        album_id,
        extra={
            "operation": "label_album",
            "album_id": album_id,
            "prompt_type": prompt_type,
            "force": force,
            "task_id": task.id,
        },
    )

    return jsonify({"status": "queued", "task_id": task.id}), 202


@app.route("/api/labeling/tasks/<task_id>", methods=["GET"])
def get_labeling_task(task_id):
    """Check the status of a labeling task."""
    async_result = celery.AsyncResult(task_id)
    response = {"task_id": task_id, "state": async_result.state}

    if async_result.state == "PROGRESS":
        response["progress"] = async_result.info or {}
    elif async_result.state == "SUCCESS":
        response["result"] = async_result.info
    elif async_result.state in ("FAILURE", "REVOKED"):
        response["error"] = str(async_result.info)

    return jsonify(response)


@app.route("/api/database/stats", methods=["GET"])
def get_database_stats():
    """Get database statistics (public endpoint)"""
    try:
        stats = {
            "albums": Album.query.count(),
            "images": Image.query.count(),
            "public_images": Image.query.filter_by(is_public=True).count(),
            "labels": db.session.query(Label).count(),
            "scrape_jobs": db.session.query(ScrapeJob).count(),
            "training_runs": db.session.query(TrainingRun).count(),
        }
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting database stats: {e}", exc_info=True)
        return jsonify({"error": "Failed to get database stats"}), 500


# ============================================================================
# Admin-Only API Endpoints
# ============================================================================


@app.route("/api/admin/users", methods=["GET"])
@require_admin
def get_admin_users():
    """Get all users (admin only)"""
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
            f"Retrieved {user_count} users for admin",
            extra={"operation": "admin_get_users", "user_count": user_count},
        )

        return jsonify(users)
    except Exception as e:
        logger.error(
            f"Error getting users: {e}",
            exc_info=True,
            extra={"operation": "admin_get_users", "error_type": type(e).__name__},
        )
        return jsonify({"error": "Failed to get users"}), 500


@app.route("/api/admin/users/<email>", methods=["PUT"])
@require_admin
def update_user_role(email):
    """Update user role (admin only)"""
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
    except Exception as e:
        logger.error(f"Error updating user role: {e}", exc_info=True)
        return jsonify({"error": "Failed to update user role"}), 500


@app.route("/api/admin/images", methods=["GET"])
@require_admin
def get_admin_images():
    """Get all images including private ones (admin only)"""
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
    except Exception as e:
        logger.error(f"Error getting admin images: {e}", exc_info=True)
        return jsonify({"error": "Failed to get images"}), 500


@app.route("/api/admin/images/<int:image_id>/visibility", methods=["PUT"])
@require_admin
def update_image_visibility(image_id):
    """Update image visibility (admin only)"""
    try:
        data = request.json
        if not data or "is_public" not in data:
            return jsonify({"error": "is_public field is required"}), 400

        image = Image.query.get_or_404(image_id)
        image.is_public = bool(data["is_public"])
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Updated image visibility to "
                f"{'public' if image.is_public else 'private'}",
            }
        )
    except Exception as e:
        logger.error(f"Error updating image visibility: {e}", exc_info=True)
        return jsonify({"error": "Failed to update image visibility"}), 500


@app.route("/api/admin/albums", methods=["GET"])
@require_admin
def get_admin_albums():
    """Get all albums including private ones (admin only)"""
    try:
        albums = Album.query.order_by(Album.created_at.desc()).all()
        return jsonify([album.to_dict() for album in albums])
    except Exception as e:
        logger.error(f"Error getting admin albums: {e}", exc_info=True)
        return jsonify({"error": "Failed to get albums"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("FLASK_RUN_PORT", 10050))

    logger.info("=" * 50)
    logger.info("Imagineer API Server")
    logger.info("=" * 50)
    logger.info(f"Config: {CONFIG_PATH}")
    logger.info(f"Output: {load_config()['output']['directory']}")
    logger.info("")
    logger.info(f"Starting server on http://0.0.0.0:{port}")
    logger.info("Access from any device on your network!")
    logger.info("=" * 50)

    # Only enable debug mode in development
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
