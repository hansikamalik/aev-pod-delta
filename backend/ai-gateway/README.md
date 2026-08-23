# AI Gateway Service

## Overview

The AI Gateway Service is the backend component of the AEV Platform. It is the
entry point for all AI Copilot requests: it applies safety guardrails, enforces
rate limits, forwards the question to Gemma 4, tracks token usage and cost, and
returns a sanitized, cited-safe response.

---

## Features

- FastAPI application with Swagger UI
- `/health` check endpoint
- `/copilot/query` — the main AI Copilot endpoint
- **Gemma 4 only** (`gemma-4-31b-it`), per supervisor directive — no OpenAI,
  no other providers
- Two hosting paths for Gemma 4, tried in order:
  1. Google Gemma Cloud API (current default — doesn't expire)
  2. Colab Gemma T4 GPU API (kept as a fallback for anyone running a live
     notebook; free-tier Colab sessions time out after ~90 min, which is why
     Google API is tried first)
  3. Falls back to a mock response if neither is configured (used for local
     dev / CI so tests don't need real credentials)
- Guardrails:
  - Prompt-injection detection
  - Blocked-topic detection
  - Input and output PII redaction (email, SSN, credit card)
  - "AI-generated, verify before acting" disclaimer on every response
  - Maximum output length enforcement
- Per-user rate limiting (Redis-backed, 5 requests / 60 seconds), with
  graceful fallback if Redis is unreachable
- Token usage + estimated cost tracking per request

---

## Project Structure

```
ai-gateway/
│
├── app/
│   ├── __init__.py
│   ├── client.py          # Gemma 4 integration (Google API + Colab fallback)
│   ├── config.py          # App settings
│   ├── cost_tracker.py    # Per-model cost estimation
│   ├── guardrails.py      # Prompt-injection / PII / blocked-topic checks
│   ├── main.py            # FastAPI app + routes
│   ├── rate_limiter.py    # Redis-backed per-user rate limiting
│   └── token_tracker.py   # Token usage extraction
│
├── migrations/
│   └── 001_create_ai_interactions.sql
│
├── tests/
│
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── README.md
└── requirements.txt
```

---

## Installation

Clone the repository:

```bash
git clone https://github.com/hansikamalik/aev-pod-delta.git
```

Move into the project:

```bash
cd backend/ai-gateway
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Copy the environment template and fill in your own values:

```bash
cp .env.example .env
```

See [Environment Variables](#environment-variables) below for what to put in it.

---

## Run the Application

### Option 1 — directly with uvicorn

```bash
uvicorn app.main:app --reload
```

### Option 2 — with docker-compose (also starts Postgres + Redis)

```bash
docker-compose up
```

Server:

```
http://127.0.0.1:8000
```

Swagger Documentation:

```
http://127.0.0.1:8000/docs
```

---

## Environment Variables

Set these in your own local `.env` file (never commit real values — this
file is gitignored on purpose):

| Variable | Required | Notes |
|---|---|---|
| `GOOGLE_API_KEY` | Yes (for real responses) | Free key from [Google AI Studio](https://aistudio.google.com/app/apikey). This is the active hosting method. |
| `COLAB_GEMMA_URL` | Optional | Only needed if you're running your own Colab notebook as a fallback. This link is temporary and expires roughly every 90 minutes — get a fresh one from whoever's notebook is live rather than relying on an old committed value. |
| `REDIS_URL` | No (has a default) | Defaults to `redis://localhost:6379` |
| `DATABASE_URL` | No (has a default) | Defaults to local Postgres |

If neither `GOOGLE_API_KEY` nor `COLAB_GEMMA_URL` is set, `/copilot/query`
still works — it just returns a mock response instead of a real model answer.
This is intentional, so local dev and CI don't need real credentials.

---

## API Endpoints

### Root

```
GET /
```

Response:

```json
{
  "message": "Welcome to AI Gateway Service"
}
```

---

### Health Check

```
GET /health
```

Response:

```json
{
  "status": "healthy",
  "service": "AI Gateway Service"
}
```

---

### AI Copilot Query

```
POST /copilot/query
```

Headers:

```
X-User-Id: <string>   (optional, defaults to "anonymous" — used for rate limiting)
```

Request body:

```json
{
  "question": "What are our top risks this week?"
}
```

Response:

```json
{
  "question": "What are our top risks this week?",
  "answer": "...AI-generated answer...\n\nAI-generated, verify before acting.",
  "model": "gemma-4-31b-it",
  "usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0
  },
  "cost": { "...": "..." },
  "rate_limit": {
    "requests_made": 1,
    "requests_remaining": 4,
    "resets_in_seconds": 60
  },
  "guardrails": {
    "input_pii_redacted": false,
    "output_pii_redacted": true,
    "disclaimer_added": true,
    "max_output_length": 4000
  }
}
```

If the question trips a guardrail (prompt injection or a blocked topic), the
request is rejected with a `400`:

```json
{
  "error": "Request blocked by guardrails",
  "reason": "prompt_injection"
}
```

If the per-user rate limit is exceeded, the request is rejected with a `429`.

---

## Testing

```bash
python -m flake8 app --max-line-length=100
python -m pytest -v
```

---

## Technology Stack

- Python 3.12
- FastAPI
- Uvicorn
- Pydantic
- Redis (rate limiting)
- Google Gemma 4 (`gemma-4-31b-it`)

---

## Version

Current Version:

```
2.0.0
```