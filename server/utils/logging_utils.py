"""
Logging utilities for structured context and PII redaction.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

REDACTED = "[REDACTED]"

# Keywords that should always be redacted whenever they appear as field names.
SENSITIVE_FIELD_KEYWORDS = {
    "prompt",
    "negative_prompt",
    "raw_prompt",
    "user_prompt",
    "input",
    "input_text",
    "payload",
    "request_body",
    "body",
    "authorization",
    "cookie",
    "headers",
    "token",
    "password",
    "secret",
    "api_key",
    "url_params",
    "metadata",
    "context",
}


def is_sensitive_field(field_name: str | None) -> bool:
    """Return True if the field name should be redacted."""
    if not field_name:
        return False
    lowered = str(field_name).lower()
    return any(keyword in lowered for keyword in SENSITIVE_FIELD_KEYWORDS)


def scrub_sensitive_data(value: Any, field_name: str | None = None) -> Any:
    """Recursively scrub sensitive payloads from logs."""
    if is_sensitive_field(field_name):
        return REDACTED

    if isinstance(value, Mapping):
        return {
            key: (REDACTED if is_sensitive_field(key) else scrub_sensitive_data(val, str(key)))
            for key, val in value.items()
        }

    if isinstance(value, (list, tuple, set, frozenset)):
        scrubbed = [scrub_sensitive_data(item) for item in value]
        if isinstance(value, tuple):
            return tuple(scrubbed)
        if isinstance(value, set):
            return set(scrubbed)
        if isinstance(value, frozenset):
            return frozenset(scrubbed)
        return scrubbed

    # Fallback: redact exceptionally long strings when no explicit field name is available.
    if isinstance(value, str) and len(value) > 512:
        return REDACTED

    return value


def scrub_log_args(args: Any) -> Any:
    """Scrub log arguments passed to logging statements."""
    if isinstance(args, Mapping):
        return {key: scrub_sensitive_data(val, str(key)) for key, val in args.items()}

    if isinstance(args, Sequence) and not isinstance(args, (str, bytes, bytearray)):
        scrubbed = [scrub_sensitive_data(item) for item in args]
        if isinstance(args, tuple):
            return tuple(scrubbed)
        return scrubbed

    return scrub_sensitive_data(args)
