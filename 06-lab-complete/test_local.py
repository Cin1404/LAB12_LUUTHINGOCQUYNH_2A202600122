#!/usr/bin/env python3
"""Local smoke tests for the Lab 6 API."""

from __future__ import annotations

import json
import os
import sys

import requests


BASE_URL = os.getenv("AGENT_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_KEY = os.getenv("AGENT_API_KEY", "change-me-before-production")
USER_ID = os.getenv("AGENT_TEST_USER", "student-local")


def dump_response(label: str, response: requests.Response) -> None:
    print(f"\n{label}")
    print(f"Status: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except ValueError:
        print(response.text)


def expect(condition: bool, message: str) -> None:
    if not condition:
        print(f"\nFAILED: {message}")
        sys.exit(1)


def main() -> None:
    ask_body = {"user_id": USER_ID, "question": "What is deployment?"}

    health = requests.get(f"{BASE_URL}/health", timeout=10)
    dump_response("1. GET /health", health)
    expect(health.status_code == 200, "/health should return 200")

    ready = requests.get(f"{BASE_URL}/ready", timeout=10)
    dump_response("2. GET /ready", ready)
    expect(ready.status_code in {200, 503}, "/ready should return 200 or 503")

    unauthorized = requests.post(f"{BASE_URL}/ask", json=ask_body, timeout=10)
    dump_response("3. POST /ask without API key", unauthorized)
    expect(unauthorized.status_code == 401, "/ask without API key should return 401")

    headers = {"X-API-Key": API_KEY}

    ask = requests.post(f"{BASE_URL}/ask", headers=headers, json=ask_body, timeout=10)
    dump_response("4. POST /ask with API key", ask)
    expect(ask.status_code == 200, "/ask with API key should return 200")

    history = requests.get(f"{BASE_URL}/history/{USER_ID}", headers=headers, timeout=10)
    dump_response("5. GET /history/{user_id}", history)
    expect(history.status_code == 200, "/history should return 200")

    usage = requests.get(f"{BASE_URL}/usage/{USER_ID}", headers=headers, timeout=10)
    dump_response("6. GET /usage/{user_id}", usage)
    expect(usage.status_code == 200, "/usage should return 200")

    metrics = requests.get(f"{BASE_URL}/metrics", headers=headers, timeout=10)
    dump_response("7. GET /metrics", metrics)
    expect(metrics.status_code == 200, "/metrics should return 200")

    print("\nAll local smoke tests passed.")


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as exc:
        print(f"\nFAILED: could not reach {BASE_URL}: {exc}")
        sys.exit(1)
