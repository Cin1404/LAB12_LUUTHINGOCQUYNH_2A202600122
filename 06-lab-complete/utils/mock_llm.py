"""Local mock LLM used by Lab 6."""
from __future__ import annotations

import random
import time


MOCK_RESPONSES = {
    "default": [
        "Day 12 agent is running with a mock LLM response.",
        "The production-ready agent received your question successfully.",
        "This is a mock answer so we can focus on deployment and reliability.",
    ],
    "docker": [
        "Docker packages the application and its dependencies into a reproducible container."
    ],
    "deploy": [
        "Deployment moves your application from local development into a hosted runtime."
    ],
    "redis": [
        "Redis is being used as external state so multiple agent instances can share data."
    ],
}


def ask(question: str, delay: float = 0.08) -> str:
    time.sleep(delay + random.uniform(0, 0.03))
    question_lower = question.lower()
    for keyword, responses in MOCK_RESPONSES.items():
        if keyword in question_lower:
            return random.choice(responses)
    return random.choice(MOCK_RESPONSES["default"])


def ask_stream(question: str):
    response = ask(question)
    for word in response.split():
        time.sleep(0.04)
        yield word + " "
