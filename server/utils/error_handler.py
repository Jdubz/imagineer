"""
Structured error response handling for API endpoints.

Provides consistent error format across all API responses with trace IDs.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from flask import g, jsonify


class APIError(Exception):
    """
    Base API error with structured format.

    Attributes:
        message: User-friendly error message
        error_code: Machine-readable error code
        status_code: HTTP status code
        details: Additional error context
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "GENERIC_ERROR"
        self.status_code = status_code
        self.details = details or {}


def format_error_response(
    error: Exception, trace_id: Optional[str] = None, status_code: Optional[int] = None
) -> tuple:
    """
    Format error as structured JSON response.

    Args:
        error: Exception to format
        trace_id: Optional trace ID (defaults to g.trace_id)
        status_code: Optional HTTP status code override

    Returns:
        Tuple of (response_dict, status_code)
    """
    # Get trace ID from request context or parameter
    request_trace_id = trace_id or getattr(g, "trace_id", None)

    # Determine error details
    if isinstance(error, APIError):
        error_message = error.message
        error_code = error.error_code
        http_status = status_code or error.status_code
        error_details = error.details
    else:
        error_message = str(error)
        error_code = "INTERNAL_ERROR"
        http_status = status_code or 500
        error_details = {}

    response = {
        "error": error_message,
        "error_code": error_code,
        "trace_id": request_trace_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": error_details,
    }

    return jsonify(response), http_status


# Common error factories
def not_found_error(resource: str, resource_id: Any = None) -> APIError:
    """Create a 404 not found error"""
    details = {"resource": resource}
    if resource_id is not None:
        details["resource_id"] = resource_id

    return APIError(
        message=f"{resource} not found",
        error_code=f"{resource.upper()}_NOT_FOUND",
        status_code=404,
        details=details,
    )


def validation_error(message: str, field: Optional[str] = None) -> APIError:
    """Create a 400 validation error"""
    details = {}
    if field:
        details["field"] = field

    return APIError(
        message=message,
        error_code="VALIDATION_ERROR",
        status_code=400,
        details=details,
    )


def unauthorized_error(message: str = "Unauthorized") -> APIError:
    """Create a 401 unauthorized error"""
    return APIError(message=message, error_code="UNAUTHORIZED", status_code=401, details={})


def forbidden_error(message: str = "Forbidden") -> APIError:
    """Create a 403 forbidden error"""
    return APIError(message=message, error_code="FORBIDDEN", status_code=403, details={})


def internal_error(message: str = "Internal server error") -> APIError:
    """Create a 500 internal server error"""
    return APIError(message=message, error_code="INTERNAL_ERROR", status_code=500, details={})
