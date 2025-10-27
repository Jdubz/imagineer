"""
Authentication module for Imagineer API
Handles Google OAuth and role-based access control
"""

import json
import os
from functools import wraps
from pathlib import Path

from authlib.integrations.flask_client import OAuth
from flask import redirect, session, url_for, jsonify
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user

# Configuration
USERS_FILE = Path(__file__).parent / "users.json"

# User roles
ROLE_VIEWER = "viewer"
ROLE_EDITOR = "editor"
ROLE_ADMIN = "admin"


class User(UserMixin):
    """Simple user model for Flask-Login"""

    def __init__(self, email, name, picture, role=ROLE_VIEWER):
        self.id = email
        self.email = email
        self.name = name
        self.picture = picture
        self.role = role

    def is_editor(self):
        """Check if user has editor or admin role"""
        return self.role in [ROLE_EDITOR, ROLE_ADMIN]

    def is_admin(self):
        """Check if user has admin role"""
        return self.role == ROLE_ADMIN


def load_users():
    """Load user roles from JSON file"""
    if not USERS_FILE.exists():
        return {}
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading users: {e}")
        return {}


def save_users(users):
    """Save user roles to JSON file"""
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        print(f"Error saving users: {e}")


def get_user_role(email):
    """Get user role from users.json, default to viewer"""
    users = load_users()
    user_data = users.get(email, {})
    return user_data.get("role", ROLE_VIEWER)


def init_auth(app):
    """Initialize authentication for Flask app"""
    # Configure session
    app.config["SECRET_KEY"] = os.environ.get(
        "FLASK_SECRET_KEY", "dev-secret-key-change-in-production"
    )
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PERMANENT_SESSION_LIFETIME"] = 86400  # 24 hours

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth_login"

    @login_manager.user_loader
    def load_user(user_id):
        """Load user from session"""
        if "user" not in session:
            return None
        user_data = session["user"]
        return User(
            email=user_data["email"],
            name=user_data["name"],
            picture=user_data.get("picture", ""),
            role=user_data.get("role", ROLE_VIEWER),
        )

    # Initialize OAuth
    oauth = OAuth(app)
    google = oauth.register(
        name="google",
        client_id=os.environ.get("GOOGLE_CLIENT_ID"),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    return oauth, google


def require_auth(f):
    """Decorator to require authentication"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)

    return decorated_function


def require_role(role):
    """Decorator to require specific role"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"error": "Authentication required"}), 401

            if role == ROLE_EDITOR and not current_user.is_editor():
                return jsonify({"error": "Editor role required"}), 403

            if role == ROLE_ADMIN and not current_user.is_admin():
                return jsonify({"error": "Admin role required"}), 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator
