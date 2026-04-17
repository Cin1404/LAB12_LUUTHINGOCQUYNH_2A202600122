"""Sliding-window rate limiter with Redis-first storage."""
from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque

from fastapi import HTTPException

from app.config import settings
from app.storage_backend import get_redis_client, storage_backend_name


WINDOW_SECONDS = 60
_memory_windows: dict[str, deque[float]] = defaultdict(deque)


def _check_memory(user_id: str) -> dict:
    now = time.time()
    window = _memory_windows[user_id]
    while window and window[0] <= now - WINDOW_SECONDS:
        window.popleft()

    if len(window) >= settings.rate_limit_per_minute:
        retry_after = max(1, int(window[0] + WINDOW_SECONDS - now) + 1)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit": settings.rate_limit_per_minute,
                "window_seconds": WINDOW_SECONDS,
                "retry_after_seconds": retry_after,
                "backend": "memory",
            },
            headers={"Retry-After": str(retry_after)},
        )

    window.append(now)
    return {
        "limit": settings.rate_limit_per_minute,
        "remaining": settings.rate_limit_per_minute - len(window),
        "window_seconds": WINDOW_SECONDS,
        "backend": "memory",
    }


def _check_redis(user_id: str) -> dict:
    client = get_redis_client()
    if client is None:
        return _check_memory(user_id)

    key = f"ratelimit:{user_id}"
    now = time.time()
    window_start = now - WINDOW_SECONDS

    client.zremrangebyscore(key, 0, window_start)
    current = client.zcard(key)

    if current >= settings.rate_limit_per_minute:
        oldest = client.zrange(key, 0, 0, withscores=True)
        retry_after = 1
        if oldest:
            retry_after = max(1, int(oldest[0][1] + WINDOW_SECONDS - now) + 1)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit": settings.rate_limit_per_minute,
                "window_seconds": WINDOW_SECONDS,
                "retry_after_seconds": retry_after,
                "backend": "redis",
            },
            headers={"Retry-After": str(retry_after)},
        )

    member = f"{now:.6f}:{uuid.uuid4().hex}"
    client.zadd(key, {member: now})
    client.expire(key, WINDOW_SECONDS * 2)

    return {
        "limit": settings.rate_limit_per_minute,
        "remaining": settings.rate_limit_per_minute - current - 1,
        "window_seconds": WINDOW_SECONDS,
        "backend": "redis",
    }


def check_rate_limit(user_id: str) -> dict:
    """Validate per-user quota and return remaining quota metadata."""
    if storage_backend_name() == "redis":
        return _check_redis(user_id)
    return _check_memory(user_id)
