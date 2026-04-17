# Lab 12 - Complete Production Agent

This project is the final Lab 6 deliverable for Day 12. It combines:

- environment-based config
- API key authentication
- per-user rate limiting
- per-user monthly cost guard
- conversation history
- Redis-backed stateless storage
- health and readiness probes
- graceful shutdown
- structured JSON logging
- Docker multi-stage build
- Docker Compose stack with Nginx + Redis

## Project Structure

```text
06-lab-complete/
|-- app/
|   |-- __init__.py
|   |-- auth.py
|   |-- config.py
|   |-- cost_guard.py
|   |-- history_store.py
|   |-- main.py
|   |-- rate_limiter.py
|   `-- storage_backend.py
|-- nginx/
|   `-- nginx.conf
|-- utils/
|   |-- __init__.py
|   `-- mock_llm.py
|-- Dockerfile
|-- docker-compose.yml
|-- requirements.txt
|-- .env.example
|-- .dockerignore
|-- railway.toml
`-- check_production_ready.py
```

Root repository:

```text
render.yaml
```

## Local Development

1. Copy the example env file:

```powershell
Copy-Item .env.example .env.local
```

2. Run the API directly:

```powershell
$env:PYTHONUTF8="1"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

3. Test the API:

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/health"
```

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/ask" `
  -Headers @{ "X-API-Key" = "change-me-before-production" } `
  -ContentType "application/json" `
  -Body '{"user_id":"student-1","question":"What is deployment?"}'
```

## Docker Compose Stack

The Docker stack matches the Part 6 architecture:

```text
Client -> Nginx -> Agent replicas -> Redis
```

Run it with:

```powershell
docker compose --env-file .env.local up --build --scale agent=3
```

Then test through Nginx:

```powershell
curl.exe http://localhost/health
```

```powershell
curl.exe -X POST http://localhost/ask ^
  -H "X-API-Key: your-key" ^
  -H "Content-Type: application/json" ^
  -d "{\"user_id\":\"student-1\",\"question\":\"Explain Redis\"}"
```

## Deployment

### Railway

- Use `railway.toml`
- Set environment variables:
  - `AGENT_API_KEY`
  - `REDIS_URL`
  - `RATE_LIMIT_PER_MINUTE`
  - `MONTHLY_BUDGET_USD`
  - `OPENAI_API_KEY` if using a real provider

### Render

- Use the root `render.yaml`
- The blueprint defines both the web service and a Redis service
- For a full GitHub-to-Render flow, see `RENDER_DEPLOYMENT.md`

## Validation

Run the checker:

```powershell
$env:PYTHONUTF8="1"
python check_production_ready.py
```

It performs a static validation of the Lab 6 deliverable and confirms the expected files and features are present.

For a quick local smoke test after the API is running:

```powershell
$env:AGENT_API_KEY="change-me-before-production"
python test_local.py
```

## Keep It Simple

Use these files as the main reference:

- `README.md`: local setup, Docker, validation
- `RENDER_DEPLOYMENT.md`: Render deployment steps
- `../DEPLOYMENT.md`: final public URL and submission proof
- `.env.example`: source of truth for environment variables

If you deploy the whole repository to Render, use the root-level `render.yaml`.
