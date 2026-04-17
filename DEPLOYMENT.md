# Deployment Information

## Student

- Name: Luu Thi Ngoc Quynh
- Student ID: 2A202600122
- Date: 2026-04-17

## Current Status

- Local source code for Lab 6 has been completed and reviewed.
- `06-lab-complete/check_production_ready.py` passes locally.
- Local API smoke tests pass in development mode.
- Public cloud deployment has not been completed from this environment yet.

## Public URL

Pending deployment

Update this section after deploying:

```text
https://your-agent.railway.app
```

## Platform

Recommended: Railway

Alternative: Render

## Deployment Folder

Use the final project inside:

```text
06-lab-complete/
```

## Local Validation Commands

Run from `06-lab-complete/`:

### Static Check

```powershell
$env:PYTHONUTF8="1"
python check_production_ready.py
```

### Run Locally

```powershell
Copy-Item .env.example .env.local
$env:PYTHONUTF8="1"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Health Check

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/health"
```

### API Test

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/ask" `
  -Headers @{ "X-API-Key" = "change-me-before-production" } `
  -ContentType "application/json" `
  -Body '{"user_id":"test-user","question":"Hello"}'
```

## Public Test Commands

Replace `YOUR_PUBLIC_URL` and `YOUR_API_KEY` after deployment:

### Health Check

```bash
curl https://YOUR_PUBLIC_URL/health
```

Expected:

```json
{"status":"ok", ...}
```

### Ready Check

```bash
curl https://YOUR_PUBLIC_URL/ready
```

### Auth Required Check

```bash
curl -X POST https://YOUR_PUBLIC_URL/ask \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test-user","question":"Hello"}'
```

Expected: `401`

### API Test With Authentication

```bash
curl -X POST https://YOUR_PUBLIC_URL/ask \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test-user","question":"Hello"}'
```

### Rate Limiting Test

```bash
for i in {1..15}; do
  curl -X POST https://YOUR_PUBLIC_URL/ask \
    -H "X-API-Key: YOUR_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"user_id":"rate-test","question":"test"}'
done
```

Expected: eventually returns `429`

## Environment Variables To Set On Cloud

- `HOST=0.0.0.0`
- `PORT=8000`
- `ENVIRONMENT=production`
- `DEBUG=false`
- `LOG_LEVEL=INFO`
- `APP_NAME=Production AI Agent`
- `APP_VERSION=1.0.0`
- `OPENAI_API_KEY=` if using real LLM provider
- `LLM_MODEL=gpt-4o-mini`
- `AGENT_API_KEY=<your-secret-key>`
- `ALLOWED_ORIGINS=*`
- `RATE_LIMIT_PER_MINUTE=10`
- `MONTHLY_BUDGET_USD=10.0`
- `ESTIMATED_OUTPUT_TOKENS=120`
- `GRACEFUL_SHUTDOWN_TIMEOUT=30`
- `HISTORY_TTL_SECONDS=604800`
- `HISTORY_MAX_MESSAGES=20`
- `REQUIRE_REDIS=true`
- `REDIS_URL=<cloud-redis-url>`

## Screenshots

Place screenshots inside `screenshots/` with these names:

- `screenshots/dashboard.png`
- `screenshots/running.png`
- `screenshots/test.png`

## What To Update Before Submission

1. Deploy `06-lab-complete` to Railway or Render.
2. Replace `Pending deployment` with the real public URL.
3. Replace `YOUR_PUBLIC_URL` and `YOUR_API_KEY` in the test command examples if you want the file to be fully submission-ready.
4. Capture and save the three required screenshots.
5. Test the public URL from a browser or another device.
