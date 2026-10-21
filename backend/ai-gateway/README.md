# AI Gateway Service

## Overview
The AI Gateway Service is the core backend component of the AEV Platform. It is the secure entry point for all AI Copilot requests: it applies safety guardrails, enforces rate limits and RBAC permissions, routes questions to Gemma through the Google Cloud API first (with the Google Colab T4 GPU tunnel as secondary fallback and a mock safety mode), tracks token usage and running cost per org, guarantees every response carries verified citations, and returns a sanitized, enterprise-safe response.

---

## Features
- **FastAPI application with Swagger UI** (`/docs`) and ReDoc (`/redoc`)
- **Health check endpoint** (`/health`)
- **Main Copilot query endpoint** (`/copilot/query`) with header-based auth and tenant context
- **Citations router** (`/citations/`) for reference document matching and citation verification
- **Guaranteed citation response:** every response returned by `/copilot/query` is guaranteed to carry at least one structured citation
- **Tool-calling framework** (`app/tools.py`) with strict RBAC role enforcement (Admin, Analyst, ReadOnly, Auditor)
- **Tiered fallback architecture:**
  1. Google Gemma Cloud API (Primary — permanent, free tier)
  2. Colab Gemma T4 GPU API (Secondary — live remote GPU tunnel)
  3. Safe mock response mode (Safety Fallback with explicit warning metadata)
- **Structured fallback logging & rate-spike alerting:**
  - Structured JSON logging on every fallback event via `ai_gateway.fallback`
  - Sliding-window monitor that emits `CRITICAL: [ALERT]` if the fallback rate crosses the threshold (default $\ge 3$ in 60s)
- **Enterprise guardrails:**
  - Prompt-injection and jailbreak detection (DAN, developer mode, system prompt leaks, roleplay/hypothetical wrappers)
  - Tool and log dump blocking (prevents unauthorized extraction of raw tool outputs, audit logs, or database tables)
  - Blocked-topic detection (CBRN weapons, explosives, malware payloads, keyloggers, buffer overflow shellcode)
  - Input and output PII redaction (email, SSN, credit cards, phone numbers)
  - Maximum output length enforcement
- **Per-user rate limiting** (Redis-backed) with graceful in-memory degradation
- **Token usage and estimated cost tracking** per request (all models currently priced at `0.0`)
- **Audit log** (`ai_interactions` table) with filtering and a 1-year retention job

---

## Setup & Environment
- Copy `.env.example` to `.env`.
- **`POSTGRES_PASSWORD` must be explicitly set** (it is strictly required).
- **No secrets or `.env` files must ever go into git.**
- Optional AI Context settings (leave `AI_CONTEXT_URL` empty to use the local demo asset list):
  - `AI_CONTEXT_URL`: base URL of the AI Context service. The gateway calls `POST {AI_CONTEXT_URL}/copilot/asset-search`.
  - `AI_CONTEXT_TIMEOUT`: request timeout in seconds (default `3`).
- Run the services using Docker Compose:
  ```bash
  docker compose up --build
  ```

**Ports used (on your machine):**
- PostgreSQL: 5433
- Redis: 6380
- AI Gateway app: 8001

> Note: the AI Context service's own compose file also publishes port 8001. If you run both on one machine, change one of the host ports (for example `"8002:8001"` for AI Context). From inside the gateway container, `localhost` means the container itself, so point `AI_CONTEXT_URL` at an address the container can reach, such as `http://host.docker.internal:8002`.

---

## Endpoints (`app/main.py`)

| Method | Path | Description |
|---|---|---|
| GET | `/` | Welcome message and service status. |
| GET | `/health` | Health check. Returns `{"status": "healthy", "service": "AI Gateway Service"}`. |
| POST | `/copilot/query` | Processes a question with guardrails, tools, citations, and tracking. |
| POST | `/citations/` | Matches reference documents against text and returns verified citations. |
| GET | `/copilot/audit-log` | Fetches audit log rows. Query filters: `user_id`, `model`, `start_date`, `end_date`, `limit` (default 50). Admin and auditor roles only. |
| POST | `/copilot/citations/flag` | Flags a citation as inaccurate with reason and user identity. |
| POST | `/webhooks/fact-check` | Records a fact-check result sent by AI Context for an interaction. |
| POST | `/admin/retention-cleanup` | Starts the expired audit log cleanup job in the background. |
| GET | `/metrics/fallback` | Fallback counts, fallback rate, and reason breakdown. |

**Request headers for `/copilot/query`** (all optional, with defaults):

| Header | Purpose | Default |
|---|---|---|
| `X-User-ID` | Caller identity, used for rate limiting and the audit log | `anonymous` |
| `X-User-Role` | Role used for RBAC (Admin, Analyst, ReadOnly, Auditor) | `anonymous` |
| `X-Org-Tier` | Org tier for rate limits (`free`, `pro`, `enterprise`) | `free` |
| `X-Org-ID` | Organization used for running spend and budget alerts | none |
| `X-Budget-Cap` | Per-request cost cap only. It never overrides an org's configured cap. | none |

---

## Tools

The gateway exposes 8 specialized tools. Every tool call is checked against the caller's role permissions. Today, `/copilot/query` automatically runs `risk_score_get` when an asset ID appears in the question; the other tools are called through the dispatcher in `app/tools.py`.

| Tool | What it does | Data source |
|---|---|---|
| `asset_search` | Searches infrastructure assets. | AI Context `/copilot/asset-search` when `AI_CONTEXT_URL` is set, otherwise the local demo asset list |
| `exposure_query` | Queries vulnerability and exposure data. | Shared mock layer (`app/mock_data.py`) |
| `risk_score_get` | Retrieves current risk scores for assets. | Shared mock layer (`app/mock_data.py`) |
| `report_generate` | Generates summaries of security and audit reports. | Shared mock layer |
| `workflow_assist` | Assists with automated workflow steps. | Shared mock data (`app/mock_data.py`) |
| `policy_check` | Validates compliance against organizational policies. | Security policy rules (`app/copilot_tools.py`) |
| `audit_query` | Queries historical audit events. | Real `ai_interactions` audit table |
| `integration_list` | Lists active third-party integrations. | Shared mock data (`app/mock_data.py`) |

---

## Citations

- **What a citation contains:** `id`, `type`, `id_ref`, and `url`.
- **Supported source types:** Asset, Exposure, Risk Score, Report, Policy, Audit Log. (KB Article is planned; no knowledge-base tool exists yet).
- **Guarantee:** Every response returned by `/copilot/query` carries at least one structured citation. Citations are attached to tool results and responses, and are stored with each interaction in the audit log.

---

## Guardrails

- **PII redaction:** automatically detects and redacts sensitive personal data on input and output.
- **Prompt-injection blocking:** identifies and blocks malicious prompt override attempts, including Unicode lookalike, fullwidth obfuscation, zero-width characters, and roleplay/hypothetical jailbreak wrappers.
- **Tool and log dump blocking:** prevents unauthorized extraction of raw tool outputs or system logs.
- **Output length limit:** enforces strict limits on generated response length.

---

## Rate Limiting & Cost Management

- **Rate limits:** enforced per user, based on org tier (`free`, `pro`, `enterprise`).
- **Budget caps and alerts:** 80% and 100% alerts fire when an org reaches those thresholds. The org cap comes from `ORG_BUDGET_CAPS` in `app/cost_tracker.py` or can be adjusted via `CostTracker.set_org_budget_cap()`.
- **Model pricing (D1):** all models (`gemma-4-31b-it`, `gemma-4-26b-a4b-it`, `gemma-colab-gpu`) are currently priced at `0.0` (free tier). In real use spend remains `$0.00`; tests use synthetic pricing to validate threshold crossings. When transitioning to paid LLM providers, configure actual per-1k token rates in `MODEL_PRICING` in `app/cost_tracker.py`.
- **In-memory spend tracking (D2):** spend is currently accumulated in-memory (`CostTracker._org_spend`), which resets upon application restarts. For production persistence across container reboots, spend will be computed directly from `ai_interactions` (which stores per-row `cost`) grouped by organization ID (planned post-go-live migration to add `org_id` column).
- **Alert destinations (D3):** budget alerts and fallback rate-spike alerts currently emit structured logs only (`WARNING` / `CRITICAL` via Python loggers). Post-go-live alerting will support dispatching webhook notifications to external notification targets (e.g. Slack, PagerDuty) via an optional `ALERT_WEBHOOK_URL` environment configuration.

---

## Fallback Mechanism

- When the primary Google API fails or times out, the Colab tunnel takes over. If the Colab tunnel also fails, a clearly marked mock response is returned.
- Fallback events and states are logged, and a spike alert fires when the fallback rate crosses the threshold.
- Current fallback metrics are available at `GET /metrics/fallback`.

---

## Audit Log & Retention

- **Storage:** stores request metadata, user details, tool calls, and guardrail triggers per request in the `ai_interactions` table, including citations and the model used.
- **Retention policy:** rows are kept for 1 year.
- **Cleanup:** run `POST /admin/retention-cleanup`, or call `cleanup_expired_rows()` from `app/audit_log.py`.

---

## Project Structure

```
ai-gateway/
├── app/
│   ├── __init__.py
│   ├── asset_search.py       # asset_search tool (AI Context call + local fallback)
│   ├── audit_log.py          # ai_interactions storage, query, retention cleanup
│   ├── citations.py          # Citations router, formatting, and response guarantee
│   ├── client.py             # Gemma client (Google Cloud + Colab GPU + fallback monitor)
│   ├── config.py             # App settings
│   ├── copilot_tools.py      # workflow_assist, policy_check, audit_query, integration_list
│   ├── cost_tracker.py       # Per-model cost estimation, org budget caps and alerts
│   ├── exposure_query.py     # exposure_query tool
│   ├── guardrails.py         # Prompt-injection / PII / blocked-topic checks
│   ├── load_generator.py     # Synthetic load-test harness
│   ├── main.py               # FastAPI app + routes
│   ├── mock_data.py          # Shared mock data layer
│   ├── mock_tools.py         # risk_score_get and related mock-backed tools
│   ├── permissions.py        # Role-based access control (RBAC)
│   ├── rate_limiter.py       # Redis-backed per-user rate limiting
│   ├── report_generate.py    # report_generate tool
│   ├── token_tracker.py      # Token usage extraction
│   └── tools.py              # Tool-calling registry and dispatcher
├── docs/
│   └── RUNBOOK_AND_SECURITY_REVIEW.md
├── migrations/
│   ├── 001_create_ai_interactions.sql
│   └── 002_add_model_to_ai_interactions.sql
├── tests/                    # Comprehensive unit tests with >90% coverage
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── pytest.ini
├── README.md
└── requirements.txt
```

---

## Local Development & Testing

Before pushing any changes, make sure all checks pass:

```bash
# 1. Lint check (must return 0 errors)
python -m flake8 app --max-line-length=100

# 2. Run all unit tests with coverage
pytest --cov=app -v
```

**CI rule:** the CI pipeline automatically fails if test coverage drops below 70%.
