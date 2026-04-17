"""Production-ready AI agent for Lab 6."""
from __future__ import annotations

import json
import logging
import signal
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import (
    calculate_cost,
    check_budget,
    estimate_tokens,
    get_usage,
    record_usage,
)
from app.history_store import append_turn, clear_history, get_history, history_backend_name
from app.rate_limiter import check_rate_limit
from app.storage_backend import redis_required_but_missing, storage_backend_name
from utils.mock_llm import ask as llm_ask
from utils.mock_llm import ask_stream as llm_ask_stream


logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_shutdown_requested = False
_in_flight_requests = 0
_request_count = 0
_error_count = 0


def _log_event(event: str, **fields) -> None:
    payload = {"event": event, **fields}
    logger.info(json.dumps(payload, ensure_ascii=False))


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready

    _log_event(
        "startup",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        storage=storage_backend_name(),
        require_redis=settings.require_redis,
    )

    time.sleep(0.1)
    _is_ready = True
    _log_event("ready", storage=storage_backend_name())

    yield

    await _drain_in_flight_requests()
    _is_ready = False
    _log_event("shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


class AskRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100, description="Stable caller identity")
    question: str = Field(..., min_length=1, max_length=2000)


class AskResponse(BaseModel):
    user_id: str
    question: str
    answer: str
    model: str
    timestamp: str
    history_messages: int
    requests_remaining: int
    monthly_budget_remaining_usd: float
    storage: str


async def _drain_in_flight_requests() -> None:
    global _is_ready

    _is_ready = False
    started = time.time()
    while _in_flight_requests > 0 and (time.time() - started) < settings.graceful_shutdown_timeout:
        await _sleep_briefly()


async def _sleep_briefly() -> None:
    import asyncio

    await asyncio.sleep(0.1)


def _ensure_serving() -> None:
    if _shutdown_requested or not _is_ready:
        raise HTTPException(status_code=503, detail="Agent is not accepting new requests.")


def _projected_cost(question: str) -> float:
    input_tokens = estimate_tokens(question)
    return calculate_cost(input_tokens, settings.estimated_output_tokens)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _error_count, _in_flight_requests, _request_count

    _request_count += 1
    _in_flight_requests += 1
    started = time.time()

    try:
        response: Response = await call_next(request)
    except Exception:
        _error_count += 1
        _log_event("request_error", method=request.method, path=request.url.path)
        raise
    finally:
        _in_flight_requests -= 1

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if "server" in response.headers:
        del response.headers["server"]

    _log_event(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round((time.time() - started) * 1000, 1),
    )
    return response


@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "storage": storage_backend_name(),
        "endpoints": {
            "ask": "POST /ask",
            "history": "GET /history/{user_id}",
            "health": "GET /health",
            "ready": "GET /ready",
            "metrics": "GET /metrics",
        },
    }


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(body: AskRequest, request: Request, _api_key: str = Depends(verify_api_key)):
    _ensure_serving()

    history = get_history(body.user_id)
    rate_info = check_rate_limit(body.user_id)
    check_budget(body.user_id, estimated_cost=_projected_cost(body.question))

    _log_event(
        "agent_request",
        user_id=body.user_id,
        history_messages=len(history),
        client_ip=request.client.host if request.client else "unknown",
        storage=storage_backend_name(),
    )

    answer = llm_ask(body.question)
    usage = record_usage(body.user_id, body.question, answer)
    updated_history = append_turn(body.user_id, body.question, answer)

    return AskResponse(
        user_id=body.user_id,
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        timestamp=datetime.now(timezone.utc).isoformat(),
        history_messages=len(updated_history),
        requests_remaining=rate_info["remaining"],
        monthly_budget_remaining_usd=usage["remaining_budget_usd"],
        storage=history_backend_name(),
    )


@app.post("/ask/stream", tags=["Agent"])
async def ask_agent_stream(body: AskRequest, _api_key: str = Depends(verify_api_key)):
    _ensure_serving()

    check_rate_limit(body.user_id)
    check_budget(body.user_id, estimated_cost=_projected_cost(body.question))

    def stream_chunks():
        chunks: list[str] = []
        for chunk in llm_ask_stream(body.question):
            chunks.append(chunk)
            yield chunk

        answer = "".join(chunks).strip()
        if answer:
            record_usage(body.user_id, body.question, answer)
            append_turn(body.user_id, body.question, answer)

    return StreamingResponse(stream_chunks(), media_type="text/plain; charset=utf-8")


@app.get("/history/{user_id}", tags=["Agent"])
def history(user_id: str, _api_key: str = Depends(verify_api_key)):
    messages = get_history(user_id)
    return {
        "user_id": user_id,
        "count": len(messages),
        "messages": messages,
        "storage": history_backend_name(),
    }


@app.delete("/history/{user_id}", tags=["Agent"])
def delete_history(user_id: str, _api_key: str = Depends(verify_api_key)):
    clear_history(user_id)
    return {"deleted": user_id}


@app.get("/usage/{user_id}", tags=["Agent"])
def usage(user_id: str, _api_key: str = Depends(verify_api_key)):
    return get_usage(user_id)


@app.get("/health", tags=["Operations"])
def health():
    """Liveness probe: process is alive even if dependencies are degraded."""
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "storage": storage_backend_name(),
        "redis_required": settings.require_redis,
        "request_count": _request_count,
        "error_count": _error_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    """Readiness probe: safe to receive traffic."""
    if not _is_ready or _shutdown_requested:
        raise HTTPException(status_code=503, detail="Agent not ready.")
    if redis_required_but_missing():
        raise HTTPException(status_code=503, detail="Redis is required but unavailable.")
    return {
        "ready": True,
        "storage": storage_backend_name(),
        "in_flight_requests": _in_flight_requests,
    }


@app.get("/metrics", tags=["Operations"])
def metrics(_api_key: str = Depends(verify_api_key)):
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "error_count": _error_count,
        "in_flight_requests": _in_flight_requests,
        "storage": storage_backend_name(),
    }


def _handle_signal(signum, _frame):
    global _shutdown_requested, _is_ready
    _shutdown_requested = True
    _is_ready = False
    _log_event("signal", signum=signum)


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


if __name__ == "__main__":
    _log_event("bootstrap", host=settings.host, port=settings.port)
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=settings.graceful_shutdown_timeout,
    )
