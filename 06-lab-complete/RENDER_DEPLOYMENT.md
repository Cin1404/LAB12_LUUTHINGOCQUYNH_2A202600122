# Render Deployment Guide

This guide uses the root-level `render.yaml` so Render can deploy the whole LAB12 repository while building the service from `06-lab-complete/`.

## Prerequisites

- A GitHub repository containing this LAB12 project
- A Render account connected to GitHub
- Final code already committed and pushed

## Step 1. Push To GitHub

From the repository root:

```powershell
git add .
git commit -m "Prepare Lab 12 final deployment"
git push origin main
```

## Step 2. Create A Blueprint In Render

1. Open Render Dashboard
2. Click `New`
3. Choose `Blueprint`
4. Select your GitHub repository
5. Render will detect the root `render.yaml`

## Step 3. Check The Blueprint Services

The blueprint creates:

- one web service for the FastAPI app
- one Redis service named `agent-cache`

The web service builds from:

```text
06-lab-complete/Dockerfile
```

## Step 4. Confirm Environment Variables

Render sets most values from `render.yaml`.

You should still review:

- `AGENT_API_KEY`
- `OPENAI_API_KEY` if you switch from mock to real provider
- `REQUIRE_REDIS=true`

## Step 5. Wait For Healthy Startup

The health check path is:

```text
/health
```

If deployment succeeds, test:

```bash
curl https://YOUR_RENDER_URL/health
curl https://YOUR_RENDER_URL/ready
```

## Step 6. Test The Protected API

```bash
curl -X POST https://YOUR_RENDER_URL/ask \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"render-test","question":"Hello"}'
```

Expected: `200`

Without API key:

```bash
curl -X POST https://YOUR_RENDER_URL/ask \
  -H "Content-Type: application/json" \
  -d '{"user_id":"render-test","question":"Hello"}'
```

Expected: `401`

## Step 7. Final Submission Updates

After the service is live:

1. Put the real URL into the root `DEPLOYMENT.md`
2. Save `dashboard.png`, `running.png`, and `test.png` into `screenshots/`
3. Re-run the public curl checks from `DEPLOYMENT.md`
4. Push the final documentation updates to GitHub

## Troubleshooting

- If `/ready` returns `503`, check whether Redis started correctly
- If `401` happens with the correct key, copy the exact `AGENT_API_KEY` from Render
- If build fails, confirm `requirements.txt` and `06-lab-complete/Dockerfile` are unchanged in GitHub
