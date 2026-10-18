# AI Gateway Service

## Overview
The AI Gateway Service is the backend component of the AEV Platform. It is the secure entry point for all AI Copilot requests: it applies safety guardrails, enforces rate limits, forwards questions to Gemma through the Google API first (with the Colab tunnel as fallback), tracks token usage and cost, provides citations, and returns a sanitized, enterprise-safe response.

---

## Features
- **FastAPI Application with Swagger UI** (`/docs`)
- **Health Check Endpoint** (`/health`)
- **Main Copilot Query Endpoint** (`/copilot/query`) with header-based auth/context (`user`, `org`, `org tier`, `budget cap`)
- **Citations Endpoint** (`/citations/`) for matching source types (Asset, Exposure, Risk Score, Policy, Report, Audit Log, KB Article)
- **Tool-Calling Framework** (`/tools/`) with RBAC role enforcement (Admin, Analyst, ReadOnly, Auditor)
- **Tiered Fallback Architecture:**
  1. Google Gemma Cloud API (Primary — permanent, free tier)
  2. Colab Gemma T4 GPU API (Secondary — live remote GPU tunnel)
- **Structured Fallback Logging & Rate-Spike Alerting:**
  - Structured JSON logging on every fallback event
  - Sliding-window monitor that emits `[ALERT]` if fallback rate exceeds threshold
- **Enterprise Guardrails:**
  - Prompt-injection & jailbreak detection (DAN, developer mode, system prompt leaks)
  - Blocked-topic detection (weapons, malware, explosives)
  - Input & output PII redaction (email, SSN, credit cards, phone numbers)
  - Maximum output length enforcement
- **Per-User Rate Limiting** (Redis-backed) with graceful degradation
- **Token Usage + Estimated Cost Tracking** per request (priced at `0.0`)

---

## Setup & Environment
- Copy `.env.example` to `.env`.
- **`POSTGRES_PASSWORD` must be explicitly set** (it is strictly required now).
- **No secrets or `.env` files must ever go into git.**
- Run the services using Docker Compose:
  ```bash
  docker compose up --build

  Ports Used:

PostgreSQL: 5433

Redis: 6380

AI Gateway App: 8001

# Endpoints (main.py)

GET / — Welcome message and service status.

GET /health — Health check endpoint.

POST /copilot/query — Processes queries. Required headers: user, org, org tier, budget cap.

GET /copilot/audit-log — Fetches audit logs. Query filters: user, model, date_range.

POST /copilot/audit-log/cleanup — Manual cleanup endpoint for expired audit logs.

# TOOLS 

The gateway exposes 8 specialized tools. Every single tool call is strictly checked against the caller’s permissions.

asset_search — Searches internal infrastructure and system assets.

exposure_query — Queries vulnerability and exposure databases.

risk_score_lookup — Retrieves current risk scores for assets/components.

report_summary — Generates summaries of security and audit reports.

workflow_assist (Returns Mock Data) — Assists with automated workflow steps.

policy_check (Returns Mock Data) — Validates compliance against organizational policies.

audit_query (Returns Mock Data) — Queries historical audit logs and events.

integration_list (Returns Mock Data) — Lists active third-party integrations.

# Citations

What a citation contains: Source type, reference ID, title, and metadata link.

Supported Source Types: Asset, Exposure, Risk Score, Policy, Report, Audit Log, and KB Article.

# Guardrails

PII Redaction: Automatically detects and redacts sensitive personal data.

Prompt-Injection Blocking: Identifies and blocks malicious prompt override attempts.

Tool & Log Dump Blocking: Prevents unauthorized extraction of raw tool outputs or system logs.

Output Length Limit: Enforces strict limits on generated response length.

# Rate Limiting & Cost Management

Enforces request limits per org tier.

Budget Caps & Alerts: 80% and 100% budget alerts fire when thresholds are reached (alerts currently only go to the log).

Spend Tracking: Spend is held entirely in-memory and resets upon application restart.

Pricing: All models are priced at 0.0.

# Fallback Mechanism

When the primary Google API fails or times out, the Colab tunnel takes over.

Fallback events and states are fully logged, and a spike alert fire when unusual traffic surges or fallback activation spikes are detected.

# Audit Log & Retention

Storage: Stores request metadata, user details, tool calls, and guardrail triggers per request.

Retention Policy: Maintained under a strict 1-year retention policy.

Cleanup: Includes a manual cleanup endpoint (/copilot/audit-log/cleanup).

---
# project structure 

ai-gateway/
├── app/
│   ├── __init__.py
│   ├── citations.py          # Citations matching and verification router
│   ├── client.py             # Gemma client (Google Cloud + Colab GPU + Fallback monitor)
│   ├── config.py             # App settings
│   ├── cost_tracker.py       # Per-model cost estimation
│   ├── guardrails.py         # Prompt-injection / PII / blocked-topic checks
│   ├── main.py               # FastAPI app + routes
│   ├── permissions.py        # Role-based access control (RBAC)
│   ├── rate_limiter.py       # Redis-backed per-user rate limiting
│   ├── token_tracker.py      # Token usage extraction
│   └── tools.py              # Tool-calling registry and dispatcher
├── migrations/
│   └── 001_create_ai_interactions.sql
├── tests/
│   └── test_citations.py
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── pytest.ini
├── README.md
└── requirements.txt

# Local Development & Testing
Before pushing any changes to the repository, ensure all checks pass:

# 1. Run flake8 lint check (must return 0 errors)
python -m flake8 app --max-line-length=100

# 2. Run all unit tests with coverage
pytest --cov=app -v

# Current Test Metrics: 199 tests passing with 92% code coverage.

CI Rule: The CI pipeline automatically fails if test coverage drops below 70%.