"""
Structured logging configuration for Imagineer
"""

import json
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

from flask import has_request_context, request


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging"""

    def format(self, record):
        log_data = {
            "timestamp": datetime.now(datetime.UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request context if available
        if has_request_context():
            log_data["request"] = {
                "method": request.method,
                "path": request.path,
                "ip": request.remote_addr,
                "user_agent": request.headers.get("User-Agent", ""),
                "referer": request.headers.get("Referer", ""),
                "content_type": request.headers.get("Content-Type", ""),
                "content_length": request.headers.get("Content-Length", ""),
            }

        # Add custom fields from record
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "session_id"):
            log_data["session_id"] = record.session_id
        if hasattr(record, "operation"):
            log_data["operation"] = record.operation
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def configure_logging(app):
    """Configure structured logging for the application"""

    # Create logs directory
    os.makedirs("logs", exist_ok=True)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Console handler - human readable for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)

    # File handler - JSON for production parsing
    file_handler = RotatingFileHandler(
        "logs/imagineer.log", maxBytes=10485760, backupCount=10  # 10MB
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(JSONFormatter())

    # Security audit log - separate file
    security_handler = RotatingFileHandler(
        "logs/security_audit.log", maxBytes=10485760, backupCount=10  # 10MB
    )
    security_handler.setLevel(logging.WARNING)
    security_handler.setFormatter(JSONFormatter())

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Security logger
    security_logger = logging.getLogger("security")
    security_logger.addHandler(security_handler)

    return root_logger
