"""
Imagineer API Server
Flask-based REST API for managing image generation
"""

import logging
import mimetypes
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

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
from server.auth import User, get_user_role, init_auth, require_admin  # noqa: E402
from server.config_loader import CONFIG_PATH as _CONFIG_PATH  # noqa: E402
from server.config_loader import load_config, save_config  # noqa: E402
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

# Configure logging early so subsequent imports can rely on it
logger = configure_logging(app)

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

# Initialize database
init_database(app)

# Initialize trace ID middleware
from server.middleware.trace_id import trace_id_middleware  # noqa: E402

trace_id_middleware(app)

# Initialize Celery
from server.celery_app import make_celery  # noqa: E402

celery = make_celery(app)

# Register blueprints
from server.routes.admin import admin_bp  # noqa: E402
from server.routes.albums import albums_bp  # noqa: E402
from server.routes.bug_reports import bug_reports_bp  # noqa: E402
from server.routes.generation import generation_bp, get_generation_health  # noqa: E402
from server.routes.images import images_bp, outputs_bp  # noqa: E402
from server.routes.labels import labels_bp  # noqa: E402
from server.routes.scraping import scraping_bp  # noqa: E402
from server.routes.training import training_bp  # noqa: E402

app.register_blueprint(images_bp)
app.register_blueprint(albums_bp)
app.register_blueprint(outputs_bp)
app.register_blueprint(scraping_bp)
app.register_blueprint(training_bp)
app.register_blueprint(bug_reports_bp)
app.register_blueprint(labels_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(generation_bp)

# ============================================================================
# Build / Version Metadata
# ============================================================================

REPO_ROOT = Path(__file__).resolve().parent.parent

try:
    APP_VERSION = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
except FileNotFoundError:
    APP_VERSION = "0.0.0"

try:
    GIT_COMMIT = (
        subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            stderr=subprocess.DEVNULL,
        )
        .decode()
        .strip()
    )
except Exception:  # pragma: no cover - git metadata optional in production
    GIT_COMMIT = None

SERVER_START_TIME = datetime.now(timezone.utc).isoformat()


# Add request timing and performance logging
@app.before_request
def before_request():
    """Log request start and set timing"""
    from flask import g

    g.start_time = time.time()
    g.request_id = getattr(g, "trace_id", None)

    if current_user.is_authenticated:
        g.user_email = current_user.email
    else:
        g.user_email = None


@app.after_request
def after_request(response):
    """Log request completion with timing and status"""
    import time

    from flask import g

    # Calculate request duration
    duration_ms = 0
    if hasattr(g, "start_time"):
        duration_ms = int((time.time() - g.start_time) * 1000)

    # Log request completion
    logger.info(
        "request.completed", extra={"status_code": response.status_code, "duration_ms": duration_ms}
    )

    return response


# Add specific error handlers
@app.errorhandler(404)
def handle_404(e):
    """Handle 404 errors"""
    logger.warning(
        "error.404",
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
    logger.error("error.500", exc_info=True, extra={"operation": "error_500", "error": str(e)})
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


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    snapshot = get_generation_health()
    return jsonify(
        {
            "status": "ok",
            **snapshot,
            "version": APP_VERSION,
            "git_commit": GIT_COMMIT,
            "started_at": SERVER_START_TIME,
        }
    )


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


CONFIG_PATH = _CONFIG_PATH
