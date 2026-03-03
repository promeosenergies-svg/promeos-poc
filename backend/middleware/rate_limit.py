"""
PROMEOS — Lightweight in-memory rate limiter (no external dependency).
Sliding-window counter per IP. Suitable for single-process / POC.
For production multi-process: use slowapi + Redis.
"""
import os
import time
import logging
from collections import defaultdict
from typing import Optional

from fastapi import HTTPException, Request, status

_logger = logging.getLogger("promeos.rate_limit")

# {key: [(timestamp, ...),]}
_buckets: dict[str, list[float]] = defaultdict(list)


def _cleanup(bucket: list[float], window: float) -> list[float]:
    cutoff = time.monotonic() - window
    return [t for t in bucket if t > cutoff]


def check_rate_limit(
    request: Request,
    *,
    key_prefix: str = "global",
    max_requests: int = 10,
    window_seconds: float = 60.0,
    extra_key: Optional[str] = None,
):
    """Raise 429 if rate limit exceeded for this IP + key_prefix.

    Usage in endpoint:
        check_rate_limit(request, key_prefix="login", max_requests=5, window_seconds=60)
    """
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return

    client_ip = request.client.host if request.client else "unknown"
    key = f"{key_prefix}:{extra_key or client_ip}"

    bucket = _cleanup(_buckets[key], window_seconds)
    _buckets[key] = bucket

    if len(bucket) >= max_requests:
        _logger.warning("Rate limit exceeded: %s (%d/%d in %.0fs)", key, len(bucket), max_requests, window_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Max {max_requests} per {int(window_seconds)}s.",
        )

    bucket.append(time.monotonic())
