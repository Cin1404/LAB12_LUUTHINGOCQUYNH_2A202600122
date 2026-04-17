"""Conversation history storage with Redis fallback."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone

from app.config import settings
from app.storage_backend import get_redis_client, storage_backend_name


_memory_history: dict[str, list[dict[str, str]]] = defaultdict(list)


def _history_key(user_id: str) -> str:
    return f"history:{user_id}"


def get_history(user_id: str) -> list[dict[str, str]]:
    client = get_redis_client()
    if client is not None:
        raw_items = client.lrange(_history_key(user_id), 0, -1)
        return [json.loads(item) for item in raw_items]
    return list(_memory_history[user_id])


def append_turn(user_id: str, question: str, answer: str) -> list[dict[str, str]]:
    entries = [
        {
            "role": "user",
            "content": question,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        {
            "role": "assistant",
            "content": answer,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    ]

    client = get_redis_client()
    if client is not None:
        key = _history_key(user_id)
        serialized = [json.dumps(item) for item in entries]
        client.rpush(key, *serialized)
        client.ltrim(key, -settings.history_max_messages, -1)
        client.expire(key, settings.history_ttl_seconds)
        return get_history(user_id)

    history = _memory_history[user_id]
    history.extend(entries)
    _memory_history[user_id] = history[-settings.history_max_messages :]
    return list(_memory_history[user_id])


def clear_history(user_id: str) -> None:
    client = get_redis_client()
    if client is not None:
        client.delete(_history_key(user_id))
        return
    _memory_history.pop(user_id, None)


def history_backend_name() -> str:
    return storage_backend_name()
