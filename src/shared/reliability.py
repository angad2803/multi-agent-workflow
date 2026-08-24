"""Redis-backed API controls and shared retry classification."""

import os
import json
from typing import Any

from src.shared.metrics import increment
from src.shared.redis_client import get_redis_client


def rate_limit(subject: str) -> tuple[bool, int]:
    """Increment a fixed window counter and return (allowed, retry_after)."""
    limit = int(os.getenv("TASK_RATE_LIMIT_REQUESTS", "30"))
    window = int(os.getenv("TASK_RATE_LIMIT_WINDOW_SECONDS", "60"))
    key = f"rate-limit:{subject}"
    client = get_redis_client()
    count = client.incr(key)
    if count == 1:
        client.expire(key, window)
    ttl = max(client.ttl(key), 1)
    if count > limit:
        increment("rate_limit_events")
        return False, ttl
    return True, ttl


def get_idempotent_response(key: str) -> dict[str, Any] | None:
    value = get_redis_client().get(f"idempotency:{key}")
    if value is None:
        return None
    response = json.loads(value)
    return None if response.get("pending") else response


def claim_idempotency_key(key: str) -> bool:
    """Reserve a key atomically while the first request is being processed."""
    return bool(
        get_redis_client().set(
            f"idempotency:{key}", json.dumps({"pending": True}), ex=300, nx=True
        )
    )


def claim_workflow_execution(task_id: str) -> bool:
    """Claim a workflow thread for one Celery delivery at a time."""
    return bool(
        get_redis_client().set(
            f"workflow-execution:{task_id}", "1", ex=900, nx=True
        )
    )


def release_workflow_execution(task_id: str) -> None:
    get_redis_client().delete(f"workflow-execution:{task_id}")


def store_idempotent_response(key: str, response: dict[str, Any]) -> None:
    get_redis_client().setex(
        f"idempotency:{key}",
        int(os.getenv("TASK_IDEMPOTENCY_TTL_SECONDS", "86400")),
        json.dumps(response, default=str),
    )


def is_retryable_error(error: Exception) -> bool:
    """Treat network, timeout, and service-unavailable failures as transient.
    
    Non-retryable (permanent) failures:
    - 401 Unauthorized (authentication)
    - 413 Payload Too Large (token limit, request size)
    - Configuration errors
    - Invalid API keys
    """
    if isinstance(error, (ValueError, KeyError, TypeError)):
        return False
    text = str(error).lower()
    permanent_markers = (
        "api key", 
        "authentication", 
        "invalid provider", 
        "configuration",
        "413",
        "payload too large",
        "token limit",
        "requested.*tokens",
    )
    return not any(marker in text for marker in permanent_markers)