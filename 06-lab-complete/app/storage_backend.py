"""Redis connection helper with development fallback."""
from __future__ import annotations

import logging

from app.config import settings

try:
    import redis as redis_lib
except ModuleNotFoundError:  # pragma: no cover - optional in local env
    redis_lib = None


logger = logging.getLogger(__name__)
_cached_client = None
_missing_package_logged = False
_unavailable_logged = False


def get_redis_client():
    global _cached_client, _missing_package_logged, _unavailable_logged

    if _cached_client is not None:
        try:
            _cached_client.ping()
            return _cached_client
        except Exception:
            _cached_client = None

    if redis_lib is None:
        if not _missing_package_logged:
            logger.warning("redis package not installed - falling back to in-memory storage")
            _missing_package_logged = True
        return None

    try:
        client = redis_lib.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        _cached_client = client
        return client
    except Exception as exc:  # pragma: no cover - depends on environment
        if not _unavailable_logged:
            logger.warning("Redis unavailable at %s - using in-memory storage (%s)", settings.redis_url, exc)
            _unavailable_logged = True
        return None


def storage_backend_name() -> str:
    return "redis" if get_redis_client() is not None else "memory"


def redis_required_but_missing() -> bool:
    return settings.require_redis and get_redis_client() is None
