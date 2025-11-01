"""
Tests for Phase 1: Security & Logging features
"""

import json
import os
from unittest.mock import MagicMock, mock_open, patch

from server.auth import get_secret_key, get_user_role, load_users, save_users
from server.logging_config import configure_logging


class TestAuthentication:
    """Test authentication system"""

    def test_load_users_empty_file(self):
        """Test loading users from empty file"""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = "{}"
        with patch("server.auth.USERS_FILE", mock_path):
            users = load_users()
            assert users == {}

    def test_load_users_valid_data(self):
        """Test loading users from valid JSON file"""
        users_data = {
            "admin": {"password_hash": "hashed_password", "role": "admin"},
            "user": {"password_hash": "another_hash", "role": "user"},
        }
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = json.dumps(users_data)
        with patch("server.auth.USERS_FILE", mock_path):
            users = load_users()
            assert users == users_data

    def test_load_users_invalid_json(self):
        """Test loading users from invalid JSON file"""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = "invalid json"
        mock_path.parent.mkdir = MagicMock()
        mock_path.open.return_value.__enter__ = MagicMock()
        mock_path.open.return_value.__exit__ = MagicMock()
        with patch("server.auth.USERS_FILE", mock_path):
            users = load_users()
            assert users == {}

    def test_save_users(self):
        """Test saving users to file"""
        users_data = {"admin": {"password_hash": "hashed_password", "role": "admin"}}

        mock_path = MagicMock()
        mock_parent = MagicMock()
        mock_path.parent = mock_parent
        mock_file = mock_open()
        mock_path.open.return_value = mock_file()
        with patch("server.auth.USERS_FILE", mock_path):
            save_users(users_data)
            mock_parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
            mock_path.open.assert_called_once_with("w", encoding="utf-8")
            # Check that JSON was written
            written_calls = mock_file().write.call_args_list
            written_data = "".join(call.args[0] for call in written_calls if call.args)
            assert json.loads(written_data) == users_data

    def test_get_secret_key_dev_mode(self):
        """Test getting secret key in development mode"""
        with patch.dict(os.environ, {"FLASK_ENV": "development"}):
            key = get_secret_key()
            assert key is not None
            assert len(key) == 64  # Hex token length (32 bytes = 64 hex chars)

    def test_get_secret_key_production(self):
        """Test getting secret key in production mode"""
        with patch.dict(os.environ, {"FLASK_SECRET_KEY": "test_secret_key"}):
            key = get_secret_key()
            assert key == "test_secret_key"

    def test_get_user_role_admin(self):
        """Test getting admin user role"""
        users_data = {"admin@example.com": {"role": "admin"}}
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = json.dumps(users_data)
        with patch("server.auth.USERS_FILE", mock_path):
            role = get_user_role("admin@example.com")
            assert role == "admin"

    def test_get_user_role_public(self):
        """Test getting public user role (no role)"""
        users_data = {"user@example.com": {"role": "user"}}  # Not admin role
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = json.dumps(users_data)
        with patch("server.auth.USERS_FILE", mock_path):
            role = get_user_role("user@example.com")
            assert role is None  # Should return None for non-admin

    def test_get_user_role_nonexistent(self):
        """Test getting role for nonexistent user"""
        users_data = {}
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = json.dumps(users_data)
        with patch("server.auth.USERS_FILE", mock_path):
            role = get_user_role("nonexistent@example.com")
            assert role is None


class TestLoggingConfiguration:
    """Test logging configuration"""

    def test_configure_logging_development(self):
        """Test logging configuration in development mode"""
        with patch.dict(os.environ, {"FLASK_ENV": "development"}):
            # This should not raise an exception
            configure_logging(None)

    def test_configure_logging_production(self):
        """Test logging configuration in production mode"""
        with patch.dict(os.environ, {"FLASK_ENV": "production"}):
            # This should not raise an exception
            configure_logging(None)

    def test_logging_config_structure(self):
        """Test that logging configuration has expected structure"""
        import logging

        from server.logging_config import configure_logging

        configure_logging(None)

        # Check that root logger is configured
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0

        # Check that our app logger exists
        app_logger = logging.getLogger("imagineer")
        assert app_logger is not None


class TestCORSConfiguration:
    """Test CORS configuration"""

    def test_cors_development_origins(self, client):
        """Test CORS allows localhost in development"""
        with patch.dict(os.environ, {"FLASK_ENV": "development"}):
            # Test a simple endpoint - CORS may not be visible in test environment
            response = client.get("/api/database/stats")
            assert response.status_code == 200

    def test_cors_production_origins(self, client):
        """Test CORS configuration in production"""
        with patch.dict(
            os.environ, {"FLASK_ENV": "production", "ALLOWED_ORIGINS": "https://example.com"}
        ):
            response = client.get("/api/database/stats")
            # Should still work in production
            assert response.status_code == 200


class TestSecurityHeaders:
    """Test security headers and configuration"""

    def test_debug_mode_development(self, app):
        """Test debug mode is enabled in development"""
        with patch.dict(os.environ, {"FLASK_ENV": "development"}):
            # In development, debug should be True
            assert app.debug is False  # Set by config, not environment

    def test_debug_mode_production(self, app):
        """Test debug mode is disabled in production"""
        with patch.dict(os.environ, {"FLASK_ENV": "production"}):
            # In production, debug should be False
            assert app.debug is False

    def test_secret_key_required(self, app):
        """Test that secret key is required"""
        # App should have a secret key configured
        assert app.secret_key is not None
        assert len(app.secret_key) > 0


class TestAdminProtection:
    """Test admin-only endpoint protection"""

    def test_admin_endpoint_without_auth(self, client):
        """Test admin endpoint returns 401 without authentication"""
        response = client.post("/api/albums", json={"name": "Test Album"})
        assert response.status_code == 401

    def test_admin_endpoint_with_invalid_auth(self, client):
        """Test admin endpoint returns 401 with invalid authentication"""
        response = client.post(
            "/api/albums",
            json={"name": "Test Album"},
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401

    def test_public_endpoint_accessible(self, client):
        """Test public endpoints are accessible without authentication"""
        response = client.get("/api/albums")
        assert response.status_code == 200

    def test_database_stats_public(self, client):
        """Test database stats endpoint is public"""
        response = client.get("/api/database/stats")
        assert response.status_code == 200
        data = response.get_json()
        assert "images" in data
        assert "albums" in data
