"""
Shared rate limiting helpers with Redis support.

Falls back to in-process counters when Redis is unavailable so unit tests
and local development keep working.
"""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from typing import Optional

from flask import jsonify, request

# We import lazily inside functions to avoid circular dependencies when Flask
# initialises the application.

try:
    from redis import Redis
    from redis.exceptions import RedisError  # type: ignore
except Exception:  # pragma: no cover - redis is optional
    Redis = None  # type: ignore
    RedisError = Exception  # type: ignore


_redis_lock = threading.Lock()
_redis_client: Optional["Redis"] = None

# In-memory fallback store (per-process)
_local_counters: defaultdict[str, deque[float]] = defaultdict(deque)
_local_lock = threading.Lock()


def _get_redis_client() -> Optional["Redis"]:
    """Initialise a Redis client from environment variables, if available."""
    global _redis_client

    if Redis is None:
        return None

    if _redis_client is not None:
        return _redis_client

    candidate_url = (
        os.environ.get("IMAGINEER_REDIS_URL")
        or os.environ.get("REDIS_URL")
        or os.environ.get("CELERY_BROKER_URL")
        or os.environ.get("CELERY_RESULT_BACKEND")
    )

    if not candidate_url:
        return None

    with _redis_lock:
        if _redis_client is not None:
            return _redis_client

        try:
            client = Redis.from_url(candidate_url, decode_responses=True)
            client.ping()
        except RedisError:
            return None

        _redis_client = client
        return _redis_client


def is_rate_limit_exceeded(
    namespace: str,
    identifier: str,
    limit: int,
    window_seconds: int,
) -> bool:
    """
    Return True when the caller has exceeded the allowed number of requests.

    Uses Redis when available; otherwise falls back to in-process counters
    (suitable for tests and single-worker development).
    """
    if limit <= 0 or window_seconds <= 0:
        return False

    now = time.time()
    now_ns = time.time_ns()
    redis_client = _get_redis_client()

    if redis_client:
        key = f"rate:{namespace}:{identifier}"
        now_ms = int(now * 1000)
        member = f"{now_ns}"
        try:
            with redis_client.pipeline() as pipe:
                pipe.zadd(key, {member: now_ms})
                pipe.zremrangebyscore(key, 0, now_ms - window_seconds * 1000)
                pipe.zcard(key)
                pipe.expire(key, window_seconds)
                _, _, current_count, _ = pipe.execute()
            return int(current_count) > limit
        except RedisError:
            # Fall back to local counters
            pass

    with _local_lock:
        window_start = now - window_seconds
        queue = _local_counters[f"{namespace}:{identifier}"]
        queue.append(now)
        while queue and queue[0] < window_start:
            queue.popleft()
        return len(queue) > limit


def enforce_rate_limit(
    *,
    namespace: str,
    limit: int,
    window_seconds: int,
    identifier: Optional[str] = None,
    message: Optional[str] = None,
    logger=None,
):
    """
    Enforce a sliding-window rate limit for the current caller and return a
    429 response tuple when the limit is exceeded.

    Args:
        namespace: Logical operation name (e.g. "training:start").
        limit: Maximum allowed invocations within the window.
        window_seconds: Size of the rolling window in seconds.
        identifier: Optional identifier; defaults to the authenticated email or
            remote address.
        message: Optional custom error message for the response.
        logger: Optional logger to record limit events.

    Returns:
        None when under the limit, otherwise (Response, 429) suitable for
        returning from a Flask view.
    """

    if limit <= 0 or window_seconds <= 0:
        return None

    if identifier is None:
        try:
            from server.auth import current_user  # Imported lazily
        except Exception:  # pragma: no cover - happens during app init
            current_user = None  # type: ignore

        user_email = getattr(current_user, "email", None) if current_user else None
        identifier = user_email or request.remote_addr or "anonymous"

    exceeded = is_rate_limit_exceeded(namespace, identifier, limit, window_seconds)
    if not exceeded:
        return None

    if logger is not None:
        try:
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "operation": namespace,
                    "identifier": identifier,
                    "limit": limit,
                    "window_seconds": window_seconds,
                },
            )
        except Exception:  # pragma: no cover - defensive logging
            logger.warning("Rate limit exceeded for %s", namespace)

    response = jsonify(
        {
            "success": False,
            "error": message or "Rate limit exceeded. Please wait before trying again.",
            "limit": limit,
            "window_seconds": window_seconds,
        }
    )
    response.headers["Retry-After"] = str(max(1, window_seconds))
    return response, 429
