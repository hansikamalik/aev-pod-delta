# AI Gateway Service

## Overview

The AI Gateway Service is the backend component of the AEV Platform. It is the
entry point for all AI Copilot requests: it applies safety guardrails, enforces
rate limits, forwards questions to Gemma 4, tracks token usage and cost, provides
citations, and returns a sanitized, enterprise-safe response.

---

## Features

- **FastAPI Application with Swagger UI** (`/docs`)
- **Health Check Endpoint** (`/health`)
- **Main Copilot Query Endpoint** (`/copilot/query`)
- **Citations Endpoint** (`/citations/`) for matching source documents
- **Tool-Calling Framework** (`/tools/`) with RBAC role enforcement (Admin, Analyst, ReadOnly, Auditor)
- **Gemma 4 Dedicated Support** (`gemma-4-31b-it`) — strictly open-weights Google Gemma
- **Tiered Fallback Architecture**:
  1. Google Gemma Cloud API (Primary — permanent, free tier)
  2. Colab Gemma T4 GPU API (Secondary — live remote GPU tunnel)
  3. Safe Mock Response (Safety Fallback — for local development and CI testing)
- **Structured Fallback Logging & Rate-Spike Alerting**:
  - Structured JSON logging on every fallback event
  - Sliding-window monitor that emits `[ALERT]` if fallback rate exceeds threshold (e.g., >= 3 in 60s)
- **Enterprise Guardrails**:
  - Prompt-injection & jailbreak detection (DAN, developer mode, system prompt leaks)
  - Blocked-topic detection (weapons, malware, explosives)
  - Input & output PII redaction (email, hyphenated/spaced SSN, credit cards, international phone numbers)
  - Regression-tested space preservation for masked credit cards
  - "AI-generated, verify before acting" disclaimer on every response
  - Maximum output length enforcement
- **Per-User Rate Limiting** (Redis-backed, 5 requests / 60 seconds), with
  graceful degradation if Redis is unreachable
- **Token Usage + Estimated Cost Tracking** per request

---

## Project Structure

```
ai-gateway/
│
├── app/
│   ├── __init__.py
│   ├── citations.py       # Citations matching and verification router
│   ├── client.py          # Gemma 4 client (Google Cloud + Colab GPU + Fallback monitor)
│   ├── config.py          # App settings
│   ├── cost_tracker.py    # Per-model cost estimation
│   ├── guardrails.py      # Prompt-injection / PII / blocked-topic checks
│   ├── main.py            # FastAPI app + routes
│   ├── permissions.py     # Role-based access control (RBAC) definitions
│   ├── rate_limiter.py    # Redis-backed per-user rate limiting
│   ├── token_tracker.py   # Token usage extraction
│   └── tools.py           # Tool-calling registry and dispatcher
│
├── migrations/
│   └── 001_create_ai_interactions.sql
│
├── tests/
│   ├── test_citations.py      # Unit tests for citation endpoints
│   ├── test_copilot_query.py  # End-to-end copilot query tests
│   ├── test_fallback.py       # Unit tests for fallback logging & spike alerting
│   ├── test_guardrails.py     # Comprehensive prompt-injection & PII tests
│   ├── test_health.py         # Health check tests
│   ├── test_rate_limiter.py   # Rate limit boundary tests
│   ├── test_tools.py          # Tool dispatch & RBAC tests
│   └── test_tracker.py        # Token & cost tracker tests
│
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── pytest.ini
└── requirements.txt
```

---

## Local Development & Testing

Before pushing any changes to the repository, ensure all checks pass:

```powershell
# 1. Run flake8 lint check (must return 0 errors)
python -m flake8 app --max-line-length=100

# 2. Run all unit tests (64 tests must pass)
python -m pytest -v

# 3. Start local development server
uvicorn app.main:app --reload
```