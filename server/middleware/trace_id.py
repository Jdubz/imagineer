"""
Trace ID middleware for request correlation across frontend/backend.

Generates unique trace IDs for each request and attaches them to responses
to enable error tracing and debugging.
"""

import uuid

from flask import g, request


def generate_trace_id() -> str:
    """Generate unique trace ID for request"""
    return str(uuid.uuid4())


def trace_id_middleware(app):
    """
    Add trace ID middleware to Flask app.

    Attaches trace IDs to every request/response for correlation.
    """

    @app.before_request
    def before_request():
        """Set trace ID before processing request"""
        # Check if trace ID provided by client (for correlation)
        client_trace_id = request.headers.get("X-Trace-Id")
        g.trace_id = client_trace_id if client_trace_id else generate_trace_id()

    @app.after_request
    def after_request(response):
        """Attach trace ID to response headers"""
        if hasattr(g, "trace_id"):
            response.headers["X-Trace-Id"] = g.trace_id
        return response

    return app
