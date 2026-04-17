"""Monthly per-user cost guard backed by Redis when available."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException

from app.config import settings
from app.storage_backend import get_redis_client


PRICE_PER_1K_INPUT_TOKENS = 0.00015
PRICE_PER_1K_OUTPUT_TOKENS = 0.0006

_memory_usage: dict[str, dict[str, float | int | str]] = defaultdict(dict)


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()) * 2)


def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    input_cost = (input_tokens / 1000) * PRICE_PER_1K_INPUT_TOKENS
    output_cost = (output_tokens / 1000) * PRICE_PER_1K_OUTPUT_TOKENS
    return round(input_cost + output_cost, 6)


def _redis_key(user_id: str) -> str:
    return f"budget:{user_id}:{_month_key()}"


def _ensure_memory_month(user_id: str) -> dict[str, float | int | str]:
    current_month = _month_key()
    record = _memory_usage.get(user_id)
    if not record or record.get("month") != current_month:
        record = {
            "month": current_month,
            "cost_usd": 0.0,
            "request_count": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        }
        _memory_usage[user_id] = record
    return record


def check_budget(user_id: str, estimated_cost: float = 0.0) -> dict:
    """Raise 402 when the monthly budget would be exceeded."""
    client = get_redis_client()
    if client is not None:
        key = _redis_key(user_id)
        current = float(client.hget(key, "cost_usd") or 0.0)
    else:
        current = float(_ensure_memory_month(user_id)["cost_usd"])

    remaining = round(settings.monthly_budget_usd - current, 6)
    if current + estimated_cost > settings.monthly_budget_usd:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Monthly budget exceeded",
                "budget_usd": settings.monthly_budget_usd,
                "used_usd": round(current, 6),
                "remaining_usd": max(0.0, remaining),
            },
        )

    return {
        "used_usd": round(current, 6),
        "remaining_usd": round(max(0.0, remaining), 6),
        "budget_usd": settings.monthly_budget_usd,
    }


def record_usage(user_id: str, input_text: str, output_text: str) -> dict:
    """Persist usage after a successful model call."""
    input_tokens = estimate_tokens(input_text)
    output_tokens = estimate_tokens(output_text)
    delta_cost = calculate_cost(input_tokens, output_tokens)
    client = get_redis_client()

    if client is not None:
        key = _redis_key(user_id)
        pipeline = client.pipeline()
        pipeline.hincrbyfloat(key, "cost_usd", delta_cost)
        pipeline.hincrby(key, "request_count", 1)
        pipeline.hincrby(key, "input_tokens", input_tokens)
        pipeline.hincrby(key, "output_tokens", output_tokens)
        pipeline.hset(key, "month", _month_key())
        pipeline.expire(key, 32 * 24 * 3600)
        pipeline.execute()

        usage = {
            "month": _month_key(),
            "cost_usd": float(client.hget(key, "cost_usd") or 0.0),
            "request_count": int(client.hget(key, "request_count") or 0),
            "input_tokens": int(client.hget(key, "input_tokens") or 0),
            "output_tokens": int(client.hget(key, "output_tokens") or 0),
        }
    else:
        usage = _ensure_memory_month(user_id)
        usage["cost_usd"] = round(float(usage["cost_usd"]) + delta_cost, 6)
        usage["request_count"] = int(usage["request_count"]) + 1
        usage["input_tokens"] = int(usage["input_tokens"]) + input_tokens
        usage["output_tokens"] = int(usage["output_tokens"]) + output_tokens

    return {
        "month": usage["month"],
        "request_count": int(usage["request_count"]),
        "input_tokens": int(usage["input_tokens"]),
        "output_tokens": int(usage["output_tokens"]),
        "cost_usd": round(float(usage["cost_usd"]), 6),
        "budget_usd": settings.monthly_budget_usd,
        "remaining_budget_usd": round(
            max(0.0, settings.monthly_budget_usd - float(usage["cost_usd"])), 6
        ),
    }


def get_usage(user_id: str) -> dict:
    client = get_redis_client()
    if client is not None:
        key = _redis_key(user_id)
        usage = {
            "month": client.hget(key, "month") or _month_key(),
            "request_count": int(client.hget(key, "request_count") or 0),
            "input_tokens": int(client.hget(key, "input_tokens") or 0),
            "output_tokens": int(client.hget(key, "output_tokens") or 0),
            "cost_usd": float(client.hget(key, "cost_usd") or 0.0),
        }
    else:
        usage = _ensure_memory_month(user_id)

    cost = round(float(usage["cost_usd"]), 6)
    return {
        "user_id": user_id,
        "month": usage["month"],
        "request_count": int(usage["request_count"]),
        "input_tokens": int(usage["input_tokens"]),
        "output_tokens": int(usage["output_tokens"]),
        "cost_usd": cost,
        "budget_usd": settings.monthly_budget_usd,
        "remaining_budget_usd": round(max(0.0, settings.monthly_budget_usd - cost), 6),
    }
