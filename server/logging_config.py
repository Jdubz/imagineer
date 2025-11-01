"""
Structured logging configuration for Imagineer
"""

import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

from flask import g, has_request_context, request

from server.utils.logging_utils import scrub_log_args, scrub_sensitive_data


class RequestContextFilter(logging.Filter):
    """Attach request/user context and scrub PII before emission."""

    COMMON_FIELDS = {
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
    }

    def filter(self, record: logging.LogRecord) -> bool:
        if has_request_context():
            record.trace_id = getattr(g, "trace_id", None)
            record.request_method = request.method
            record.request_path = request.path
            record.request_url = request.url
            record.request_remote_addr = request.remote_addr
            record.request_user_agent = request.headers.get("User-Agent", "")

            user_email = getattr(g, "user_email", None)
            if user_email:
                record.user_email = user_email
            else:  # Fall back to flask-login if available
                try:
                    from flask_login import current_user

                    if current_user.is_authenticated:
                        record.user_email = getattr(current_user, "email", None)
                    else:
                        record.user_email = None
                except Exception:  # pragma: no cover - defensive
                    record.user_email = None
        else:
            record.trace_id = None
            record.request_method = None
            record.request_path = None
            record.request_url = None
            record.request_remote_addr = None
            record.request_user_agent = None
            record.user_email = None

        if getattr(record, "args", None):
            record.args = scrub_log_args(record.args)

        for key, value in list(vars(record).items()):
            if key in self.COMMON_FIELDS:
                continue
            vars(record)[key] = scrub_sensitive_data(value, key)

        return True


class SafeTextFormatter(logging.Formatter):
    """Plain-text formatter resilient to missing context attributes."""

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "trace_id"):
            record.trace_id = None
        if not hasattr(record, "user_email"):
            record.user_email = None
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging"""

    def format(self, record):
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
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
                "query": request.query_string.decode("utf-8", errors="ignore"),
                "ip": request.remote_addr,
                "user_agent": request.headers.get("User-Agent", ""),
                "referer": request.headers.get("Referer", ""),
                "content_type": request.headers.get("Content-Type", ""),
                "content_length": request.headers.get("Content-Length", ""),
            }

        if getattr(record, "trace_id", None):
            log_data["trace_id"] = record.trace_id

        if getattr(record, "user_email", None):
            log_data["user"] = {"email": record.user_email}

        if getattr(record, "request_method", None) and "request" not in log_data:
            log_data["request"] = {
                "method": record.request_method,
                "path": getattr(record, "request_path", None),
                "ip": getattr(record, "request_remote_addr", None),
            }

        # Attach any extra fields that remain after redaction
        extra_attrs = {
            key: value
            for key, value in record.__dict__.items()
            if key not in JSONFormatter._ignored_record_fields()
        }
        if extra_attrs:
            log_data["extra"] = scrub_sensitive_data(extra_attrs)

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

    @staticmethod
    def _ignored_record_fields() -> set[str]:
        """Fields that should not be mirrored in the `extra` payload."""
        return {
            "levelno",
            "levelname",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
            "trace_id",
            "request",
            "user",
            "user_email",
            "request_method",
            "request_path",
            "request_url",
            "request_remote_addr",
            "request_user_agent",
        }


def configure_logging(app):
    """Configure structured logging for the application"""

    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        if not hasattr(record, "trace_id"):
            record.trace_id = None
        return record

    logging.setLogRecordFactory(record_factory)

    # Create logs directory
    os.makedirs("logs", exist_ok=True)

    # Root logger
    root_logger = logging.getLogger()

    log_level = os.environ.get("IMAGINEER_LOG_LEVEL", "INFO").upper()
    console_level = os.environ.get("IMAGINEER_LOG_CONSOLE_LEVEL", log_level).upper()
    file_level = os.environ.get("IMAGINEER_LOG_FILE_LEVEL", log_level).upper()

    resolved_log_level = getattr(logging, log_level, logging.INFO)
    resolved_console_level = getattr(logging, console_level, resolved_log_level)
    resolved_file_level = getattr(logging, file_level, resolved_log_level)

    root_logger.setLevel(resolved_log_level)
    context_filter = RequestContextFilter()

    # Console handler - human readable for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(resolved_console_level)

    console_format = os.environ.get("IMAGINEER_LOG_CONSOLE_FORMAT", "text").lower()
    if console_format == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_formatter = SafeTextFormatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s "
            "[trace_id=%(trace_id)s user=%(user_email)s]"
        )
        console_handler.setFormatter(console_formatter)

    # File handler - JSON for production parsing
    file_handler = RotatingFileHandler(
        "logs/imagineer.log", maxBytes=10485760, backupCount=10  # 10MB
    )
    file_handler.setLevel(resolved_file_level)
    file_handler.setFormatter(JSONFormatter())

    # Security audit log - separate file
    security_handler = RotatingFileHandler(
        "logs/security_audit.log", maxBytes=10485760, backupCount=10  # 10MB
    )
    security_handler.setLevel(logging.WARNING)
    security_handler.setFormatter(JSONFormatter())

    root_logger.addFilter(context_filter)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Security logger
    security_logger = logging.getLogger("security")
    security_logger.addFilter(context_filter)
    security_logger.addHandler(security_handler)

    return root_logger
