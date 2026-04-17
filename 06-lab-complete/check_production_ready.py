"""Static checker for the Lab 6 deliverable."""
from __future__ import annotations

import os
import sys


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def check(name: str, passed: bool, detail: str = "") -> dict:
    icon = "✅" if passed else "❌"
    print(f"  {icon} {name}" + (f" - {detail}" if detail else ""))
    return {"name": name, "passed": passed}


def file_exists(base: str, path: str) -> bool:
    return os.path.exists(os.path.join(base, path))


def file_contains(base: str, path: str, snippets: list[str]) -> bool:
    full_path = os.path.join(base, path)
    if not os.path.exists(full_path):
        return False
    content = open(full_path, encoding="utf-8").read()
    return all(snippet in content for snippet in snippets)


def run_checks() -> bool:
    base = os.path.dirname(__file__)
    results = []

    print("\n" + "=" * 55)
    print("  Production Readiness Check - Day 12 Lab")
    print("=" * 55)

    print("\nFiles")
    for path in [
        "Dockerfile",
        "docker-compose.yml",
        ".dockerignore",
        ".env.example",
        "requirements.txt",
        "README.md",
        "app/main.py",
        "app/config.py",
        "app/auth.py",
        "app/rate_limiter.py",
        "app/cost_guard.py",
        "utils/mock_llm.py",
        "nginx/nginx.conf",
    ]:
        results.append(check(f"{path} exists", file_exists(base, path)))

    print("\nSecurity")
    gitignore = os.path.join(base, "..", ".gitignore")
    ignored = os.path.exists(gitignore) and ".env.local" in open(gitignore, encoding="utf-8").read()
    results.append(check(".env.local ignored by git", ignored))
    results.append(
        check(
            "No obvious hardcoded secrets",
            not file_contains(base, "app/main.py", ["sk-hardcoded"]) and not file_contains(base, "app/config.py", ["password123"]),
        )
    )

    print("\nApplication")
    results.append(check("/health endpoint defined", file_contains(base, "app/main.py", ['@app.get("/health"'])))
    results.append(check("/ready endpoint defined", file_contains(base, "app/main.py", ['@app.get("/ready"'])))
    results.append(check("/ask endpoint defined", file_contains(base, "app/main.py", ['@app.post("/ask"'])))
    results.append(check("Conversation history supported", file_contains(base, "app/main.py", ["/history/{user_id}"])))
    results.append(check("API key auth module used", file_contains(base, "app/main.py", ["verify_api_key"])))
    results.append(check("Rate limiting module used", file_contains(base, "app/main.py", ["check_rate_limit"])))
    results.append(check("Cost guard module used", file_contains(base, "app/main.py", ["check_budget", "record_usage"])))
    results.append(check("Structured JSON logging", file_contains(base, "app/main.py", ["json.dumps", '"event"'])))
    results.append(check("Graceful shutdown signal handler", file_contains(base, "app/main.py", ["signal.signal(signal.SIGTERM"])))
    results.append(check("Redis-aware storage backend", file_contains(base, "app/storage_backend.py", ["get_redis_client", "storage_backend_name"])))

    print("\nDocker / Deploy")
    results.append(check("Multi-stage Dockerfile", file_contains(base, "Dockerfile", ["AS builder", "HEALTHCHECK", "USER agent"])))
    results.append(check("Compose includes Redis", file_contains(base, "docker-compose.yml", ["redis:", "REDIS_URL"])))
    results.append(check("Compose includes Nginx", file_contains(base, "docker-compose.yml", ["nginx:", "80:80"])))
    results.append(check("Railway config exists", file_exists(base, "railway.toml")))
    results.append(check("Render config exists", file_exists(base, "render.yaml")))

    passed = sum(1 for item in results if item["passed"])
    total = len(results)
    percent = round((passed / total) * 100)

    print("\n" + "=" * 55)
    print(f"  Result: {passed}/{total} checks passed ({percent}%)")
    if percent == 100:
        print("  ✅ Static checker passed")
    else:
        print("  ❌ Some required items are still missing")
    print("=" * 55 + "\n")

    return passed == total


if __name__ == "__main__":
    sys.exit(0 if run_checks() else 1)
