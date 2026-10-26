# AEV Pod Delta — Project Explainer
### What We Built, How It Works, and Why Each Part Exists

> This document explains every component of the AEV Pod Delta project in plain language
> without losing technical accuracy. Use it to understand and explain the system in the handover meeting.

---

## The Big Picture

**AEV** stands for **Adversarial Exposure Validation** — it's a platform that helps enterprise
security teams find and act on weaknesses across their entire IT environment. Think of it as
a security analyst's AI-powered command center.

**Pod Delta (Module 4)** is the backend layer responsible for:
1. Connecting to cloud platforms and security tools to discover assets
2. Running AI-powered analysis on those assets
3. Providing a smart Copilot that answers security questions in natural language

Pod Delta is one module inside a larger platform. Other pods (Alpha, Beta, etc.) handle
identity, vulnerability scanning, and risk scoring. Pod Delta's job is the
**experience layer** — the AI brains and the integration pipeline.

---

## System Architecture

```
                            Internet / Frontend / Pod Alpha
                                          │
                                          ▼
                              ┌─────────────────────┐
                              │   NGINX Ingress :80  │
                              │   Reverse Proxy      │
                              └──────┬──────┬────────┘
                                     │      │        \
                        /copilot     │      │ /context \  /integrations
                                     ▼      ▼           ▼
                          ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
                          │ AI Gateway   │  │ AI Context   │  │ Integration Svc  │
                          │  :8001       │◄─►  :8002        │  │  :8003           │
                          └──────────────┘  └──────────────┘  └──────────────────┘
                                     │              │                   │
                                     └──────────────┼───────────────────┘
                                                    ▼
                                     ┌──────────────────────────┐
                                     │   PostgreSQL :5432       │
                                     │   (pgvector extension)   │
                                     │                          │
                                     │   Redis :6379            │
                                     └──────────────────────────┘
```

> **Port note:** `:8001`, `:8002`, `:8003` are the **host ports** exposed in `docker-compose.yml` for local development. In the production stack (`docker-compose.prod.yml`), these services are not exposed directly — NGINX listens on `:80` and reverse-proxies to the internal container ports (`ai-gateway:8000`, `ai-context:8001`, `integration-service:8000`) over the private `aev-internal` Docker network.

All traffic enters through NGINX, which routes requests to the right service.
All three services share the same PostgreSQL database and Redis instance.

---

## The Five Components

---

### Component 1: AI Gateway (Port 8001)
**Directory:** `backend/ai-gateway/`
**Lead:** Hansika Malik

#### What it does
The AI Gateway is the main entry point for the Copilot feature. When a security analyst types
a natural language question — like *"What is the risk on our S3 bucket?"* — this service:

1. Validates and cleans the input
2. Routes to the right internal tool
3. Sends the data + question to Google's Gemma LLM
4. Returns a cited, audited answer

#### Key Features

**Guardrails (app/guardrails.py)**
Every input goes through a security filter before hitting the LLM:
- Blocks prompt injection attacks (`"ignore all previous instructions"`)
- Blocks jailbreak attempts (DAN roleplay, Unicode lookalike characters like `\u0456gnore`)
- Redacts PII from both inputs and outputs (emails, phone numbers, SSNs, credit cards replaced with `[REDACTED_...]`)
- Enforces a maximum output length

**Dynamic Tool Router (app/tool_router.py)**
Instead of hardcoding logic, the gateway uses natural language understanding to decide which
tool to call. The `resolve_dynamic_tool_intent()` function reads the question and maps it to one of 8 tools:

| Tool | What it fetches | Example trigger phrase |
|---|---|---|
| `risk_score_get` | Risk score for a specific asset | *"risk score of asset-001"* |
| `exposure_query` | Vulnerability and CVE data | *"critical vulnerabilities"* |
| `asset_search` | Semantic vector search for assets | *"find exposed storage buckets"* |
| `policy_check` | Compliance rule evaluation | *"is this bucket policy compliant"* |
| `workflow_assist` | Security playbooks and remediations | *"run remediation workflow"* |
| `report_generate` | Security reports | *"generate security report for asset-001"* |
| `audit_query` | Past interaction logs | *"audit log for last 7 days"* |
| `integration_list` | Status of connected systems | *"show active integrations"* |

Once the tool runs and returns data, that data gets injected into the prompt sent to Gemma —
so the LLM answers with real, current data rather than hallucinating.

**JWT Authentication (app/jwt_auth.py)**
Every request that comes in must carry a signed JWT (JSON Web Token). The gateway verifies:
- Cryptographic signature (tamper detection)
- Token expiry
- Issuer must be `aev-pod-alpha`
- Audience must be `aev-pod-delta`

From the token, it extracts: `user_id`, `role`, `tenant_id`, `org_tier`, and `budget_cap`.
Header spoofing (someone claiming to be admin via `X-User-Role: admin`) is rejected when
strict JWT mode is on (`JWT_AUTH_REQUIRED=true`). In dev mode (`JWT_AUTH_REQUIRED=false`,
the default), plain `X-User-ID`/`X-User-Role` headers are accepted as a fallback — this
is how the demo curl commands work without needing a real token.

**RBAC (app/permissions.py)**
Role-based access control. Not every role can call every tool:
- `admin` — full access to all tools
- `analyst` — `asset_search`, `exposure_query`, `risk_score_get`, `report_generate`, `policy_check`, `integration_list`, `citation_flag`
- `viewer` — `asset_search`, `integration_list`, `citation_flag` only
- `auditor` — `audit_query` only
- `anonymous` — blocked from all tools

**Cost Tracking (app/cost_tracker.py)**
Every LLM call tracks token usage and estimates cost per organization. Thresholds (80%, 100%
of budget cap) trigger Slack or PagerDuty alerts via webhook.

**Audit Log (app/audit_log.py)**
Every Copilot interaction is persisted to PostgreSQL — question, answer, model used, token
count, cost, citations, and a fact-check status. This creates a full traceable history.

**Rate Limiter (app/rate_limiter.py)**
Backed by Redis. Limits how many requests a user or org can make per minute based on their
subscription tier (`free`, `pro`, `enterprise`).

**Citations (app/citations.py)**
Every answer includes structured citations pointing to the source data (risk scores,
exposures, audit entries). This prevents the LLM from inventing facts.

#### Main Endpoint
```
POST /copilot/query
Body: {"question": "What are the critical vulnerabilities on asset-001?"}
Headers: Authorization: Bearer <jwt-token>
         X-User-Role: analyst (fallback in dev mode)
```

---

### Component 2: AI Context Service (Port 8002)
**Directory:** `backend/ai-context/CODES/AEV_AI_CONTEXT_Handover/`
**Lead:** Shanmukha Satya Yandra

#### What it does
The AI Context service is the knowledge and memory layer. It stores security assets as
384-dimensional vector embeddings in PostgreSQL (using the `pgvector` extension), which
enables semantic similarity search — find assets by meaning, not just keyword match.

#### Key Features

**Semantic Vector Search (POST /copilot/asset-search)**
Converts a natural language query into a 384-dim vector and finds the most similar assets
using cosine distance. "Exposed customer storage bucket" will find the S3 bucket asset even
if the word "S3" doesn't appear in the query.

This is what powers the `asset_search` tool in the AI Gateway.

**Vector Embeddings**
Assets are stored not just as text but as mathematical vectors — lists of 384 numbers that
represent the meaning of the asset's name, type, OS, and description. Similar concepts end
up close in vector space. The `pgvector` extension adds a `vector(384)` column type to
PostgreSQL and an HNSW index for fast similarity queries.

**User Memory Store (POST/GET /memory)**
The service stores per-user contextual memory — things the Copilot should remember about
a user's preferences or past findings. Memory is isolated: `analyst_sarah` cannot read
`admin_marcus`'s memories. This is enforced at the database query level.

**Tenant Isolation**
Assets are tagged with `owner_user_id` and `tenant_id`. When a non-admin API key queries
assets, the database query automatically filters by those fields before any ranking or
results are returned. Cross-tenant data leakage is impossible.

**Prompt Template Versioning (POST/GET /templates)**
The service manages versioned prompt templates. Multiple versions of a template can be
active at once and traffic is split between them deterministically (using a SHA-256 hash
of the request ID as a bucket selector). This enables A/B testing of prompt strategies
without breaking production.

**Real-Time Vector Freshness Pipeline (app/freshness_pipeline.py)**
When asset data changes (new exposure detected, risk score updated), the service listens
for events via Redis Pub/Sub and re-computes the vector embedding within 60 seconds.
The 60-second SLA is tracked and exposed via `GET /copilot/freshness-metrics`.

**Copilot Helper Endpoints**
Beyond search, the service provides structured responses for:
- `GET /copilot/asset-summary/{id}` — plain language summary of an asset
- `GET /copilot/exposure-explain/{id}` — explanation of asset's exposure
- `GET /copilot/remediation-plan/{id}` — prioritized remediation steps
- `GET /copilot/executive-summary` — portfolio-level risk overview
- `GET /copilot/recommendations` — list of prioritized actions

**Authentication**
The AI Context service uses API key authentication (not JWT). Keys are configured via
the `AEV_API_KEYS_JSON` environment variable. The AI Gateway uses the internal key
`aev-internal-service-token-32chars-min` to call this service.

---

### Component 3: Integration Service (Port 8003)
**Directory:** `backend/integration/integration-service/`
**Lead:** Harshal Sahare

#### What it does
The Integration Service is the connector management hub. It provides a REST API to register,
configure, trigger, and monitor the 19+ cloud and SaaS connectors that bring asset data
into the platform.

#### Key Features

**Connector Registry (app/registry.py)**
A catalog of all supported connector types. Each entry describes what the connector does,
what configuration it needs, and what credentials it requires. When you register a new
integration, the service validates your connector type against this catalog.

**Integration CRUD API (app/routes/integrations.py)**
Full REST API to manage connector instances:

| Endpoint | What it does |
|---|---|
| `POST /api/v1/integrations` | Register a new connector (e.g., "our AWS account") |
| `GET /api/v1/integrations` | List all registered connectors and their status |
| `GET /api/v1/integrations/{id}` | Get details of one connector |
| `PUT /api/v1/integrations/{id}` | Update config or rotate credentials |
| `DELETE /api/v1/integrations/{id}` | Remove a connector |
| `POST /api/v1/integrations/{id}/sync` | Trigger an immediate sync |
| `POST /api/v1/integrations/{id}/test` | Run a health check against the vendor API |
| `PATCH /api/v1/integrations/{id}/enable` | Enable a connector |
| `PATCH /api/v1/integrations/{id}/disable` | Disable/pause a connector |
| `GET /api/v1/integrations/{id}/history` | View past sync job results |
| `GET /api/v1/integrations/{id}/checkpoint` | Get the high-watermark sync cursor |

**Distributed Locking (app/locking.py)**
When a sync is triggered, the service acquires a Redis mutex lock for that connector.
If another sync for the same connector is already running, the second request gets a
`409 Conflict` response. This prevents duplicate work and data corruption when
the service is scaled horizontally.

**Sync Checkpoints (app/storage.py)**
After each sync, a checkpoint is recorded with the last successful timestamp and a cursor
(high-watermark for incremental sync). On the next sync, connectors pick up from the
last cursor instead of re-fetching everything from scratch.

**Sync Jobs and History**
Every sync execution (triggered manually or by schedule) is recorded as a job entry with:
- Status (success/failed)
- Assets discovered and pushed
- Duration in seconds
- Any errors encountered

---

### Component 4: Connector SDK
**Directory:** `backend/connector-sdk/`
**Lead:** Likith TV

#### What it does
The Connector SDK is the shared contract that all 19+ connectors must follow. It defines
the base classes, data models, and lifecycle methods that every connector implements.
It's packaged as an installable Python wheel (`aev-connector-sdk` v1.0.0).

#### Key Concepts

**The Connector Contract**
The canonical base class is `Connector` (in `connector_sdk/connector.py`). Subclasses implement two abstract methods and the rest is handled by the framework:

```python
def discover()   → returns assets from the vendor API (sync or async)
def ingest(assets) → pushes normalized assets to the platform, returns pushed count
```

The base class provides these automatically:
```python
def sync()         → runs discover() + ingest() and returns SyncResult
async def async_sync() → same, but fully async
def check_health() → verifies API reachability (override to customize)
def describe_config()      → returns JSON schema for config fields
def describe_credentials() → returns JSON schema for credential fields
```

`AsyncConnector` is a subclass of `Connector` for connectors that need
`async def discover()` and `async def ingest()`. Its `async def sync()` is the
primary entry point for async-first connectors.

**The Asset Model**
All connectors normalize discovered assets into the same standard `Asset` shape (defined in `connector_sdk/models.py`):
- `id` — stable unique identifier scoped to the source system
- `name` — human-readable resource name
- `source` — which connector produced it (e.g. `"aws"`, `"jira"`)
- `type` — asset category (`AssetType` enum: `COMPUTE`, `STORAGE`, `DATABASE`, `NETWORK`, `IDENTITY`, `DETECTION`, `TICKET`, `APPLICATION`, `OTHER`)
- `discovered_at` (also `discoveredAt` as a camelCase property alias)
- `raw` / `raw_payload` — the original vendor API payload
- `tags`, `metadata` — additional key-value data

> Note: The PostgreSQL `assets` table in the AI Context service has different column names (`asset_name`, `ip_address`, `operating_system`, etc.) — that is a separate database model, not the SDK `Asset`.

**SyncResult Model**
Every sync returns a `SyncResult` with:
- `status` — `SyncStatus` enum: `"success"`, `"partial"` (some assets failed), or `"failed"`
- `assets_discovered` — total assets found by `discover()`
- `assets_pushed` — assets successfully pushed by `ingest()`
- `records_synced` — alias property for `assets_discovered` (legacy compatibility)
- `success` — boolean property: `True` only when status is `success` and no errors
- `duration_seconds` — computed property: elapsed time of the sync
- `errors` — list of error strings

**The 19+ Connectors**
All connectors live under `backend/integration/`:

| Cloud & Infrastructure | Security & EDR | Identity & SaaS |
|---|---|---|
| AWS | CrowdStrike Falcon | Okta |
| GCP | Microsoft Defender | Azure Active Directory |
| Azure | SentinelOne | Microsoft 365 |
| | Microsoft Sentinel | Google Workspace |
| | CyberArk | ServiceNow |
| | | Jira |
| | | GitHub |
| | | GitLab |
| | | Webhook receiver |

**TypeScript Connector Sandbox**
A parallel TypeScript implementation of the SDK exists in
`backend/connector-sdk/connector_sandbox/` for teams building connectors in Node.js.

---

### Component 5: Shared Infrastructure
**Directory:** `deploy/`, `nginx/`, `backend/integration/shared_infra/`

#### What it does
The shared infrastructure ties everything together for deployment.

**Docker Compose (`docker-compose.yml`)**
Development orchestration: builds and starts all services, PostgreSQL (with pgvector),
and Redis together. Services communicate over an internal Docker network using service
names (`postgres`, `redis`, `ai-context`, etc.).

**Production Docker Compose (`docker-compose.prod.yml`)**
Same as above, but adds:
- Separate internal (`aev-internal`) and public (`aev-public`) Docker networks
- NGINX ingress container that routes external traffic
- Service isolation (backend services only on the internal network)

**NGINX Ingress (`nginx/nginx.conf`)**
Single entry point for all traffic on port 80:
- `/api/v1/copilot` → AI Gateway at `ai-gateway:8000`
- `/api/v1/context` → AI Context at `ai-context:8001`
- `/api/v1/integrations` → Integration Service at `integration-service:8000`
- `/health` → returns 200 directly from NGINX

**Kubernetes & Helm (`deploy/k8s/`, `deploy/helm/`)**
For production cloud deployment:
- Raw Kubernetes manifests for each service (Deployment, Service, ConfigMap, Secret, PVC, HPA)
- Helm v3 chart with parameterized values for secrets and scaling
- Kubernetes Ingress routing matching the NGINX config

**Shared Infra Utilities (`backend/integration/shared_infra/src/`)**
Utilities used by all connectors:
- `secrets_vault.py` — generic credential retrieval (never hardcoded in connectors)
- `distributed_lock.py` — Redis TTL-based mutex (used by the Integration Service)
- `scheduler.py` — cron-style job scheduler with lock integration

---

## The Data Flow — End to End

Here's how a full request works, start to finish:

```
1. Analyst opens the Copilot and types:
   "What are the critical vulnerabilities on our S3 bucket?"

2. AI Gateway receives the POST /copilot/query request
   - JWT is verified (user = analyst_sarah, tenant = fintech-global)
   - Rate limit checked via Redis
   - Input scanned by guardrails (no injections detected)
   - PII check: no PII in this query

3. Tool Router analyzes the question
   - Detects keywords: "vulnerabilities" → exposure_query tool
   - Detects keyword: "critical" → adds severity=critical filter
   - Calls exposure_query(severity="critical")

4. exposure_query tool runs
   - Reads from mock_data.py (static demo fixtures in the AI Gateway)
   - Returns: S3 bucket exposure with CVE-2024-21626, severity=critical
   - Note: in production this would call live data from Pod Beta's vulnerability store

5. AI Gateway sends to Gemma LLM
   - Prompt = original question + verified tool data
   - Gemma generates a natural language answer grounded in the data

6. Response processing
   - PII redaction pass on the answer
   - Citations added (pointing to the S3 asset record and CVE entry)
   - Disclaimer added: "AI-generated, verify before acting."

7. Audit Log
   - Interaction persisted to PostgreSQL: question, answer, tokens, cost, citations

8. Response returned to analyst:
   {
     "answer": "The S3 bucket asset-005 has a critical vulnerability CVE-2024-21626...",
     "citations": [{"id": "cit-exposure-asset-005", "type": "exposure", ...}],
     "cost": {"estimated_cost": 0.0012, "remaining_budget": 498.99},
     "guardrails": {"input_pii_redacted": false, "disclaimer_added": true}
   }
```

---

## The Unified Dataset

Located at `data/aev_unified_handover_dataset.json`, this is the single source of truth
for the demo. It models a fictional enterprise: **FinTech Global Technologies** with a
$500/month AI budget.

**9 Assets across 7 types:**

| ID | Name | Type | Risk Score |
|---|---|---|---|
| asset-001 | AI Gateway Web Core | Compute | 85 (Critical) |
| asset-002 | Redis Rate Limiter | Database/Cache | 35 (Medium) |
| asset-003 | PostgreSQL Primary DB | Database | 72 (High) |
| asset-004 | Kubernetes Worker Node | Compute | — |
| asset-005 | AWS S3 PII Vault | Storage | 94 (Critical) |
| asset-006 | Okta Root Admin Account | Identity | 81 (Critical) |
| asset-007 | Perimeter Edge Firewall | Network | 83 (Critical) |
| asset-008 | Jira Ticket SEC-4091 | Ticket | — |
| asset-009 | SentinelOne EDR Detection | Detection | — |

**Real CVEs and policy violations baked in:**
- `asset-005`: Public S3 bucket, unencrypted — violates `pol-no-public-access` and `pol-storage-encryption`
- `asset-006`: Okta admin with no MFA — violates `pol-user-mfa`
- `asset-007`: SSH port 22 open to internet — violates `pol-firewall-admin-ports`

**The database seeder (`scripts/seed_database.py`) populates PostgreSQL from this file.**

---

## The Zero-Dependency Demo Runner

**File:** `run_unified_handover_demo.py`

This Python script runs a complete demonstration of all 8 platform subsystems using only
Python's standard library — no running servers required. It reads the unified dataset
directly and exercises:

1. Connector SDK normalization and SyncResult
2. Policy engine (finds the 3 real violations)
3. Multi-factor risk scoring algorithm
4. AI Context vector search and user memory isolation
5. AI Gateway guardrails and anti-jailbreak
6. Copilot tool dispatch
7. LLM answering with citations
8. Audit logging and fact-check webhook

Run it with: `python3 run_unified_handover_demo.py`

---

## Test Coverage

**436 tests total, all passing:**

| Suite | Location | Tests | What it covers |
|---|---|---|---|
| AI Gateway | `backend/ai-gateway/tests/` | ~262 | Guardrails, tools, JWT, spend, citations |
| Connector SDK | `backend/connector-sdk/tests/` | ~70 | SDK contract, async lifecycle, models |
| AWS/GCP/CrowdStrike | `backend/connector-sdk/tests/` | ~38 | New enterprise connector tests |
| Integration Service | `backend/integration/` (pytest.ini) | 36 | API routes, Redis locking, checkpoints |
| AI Context | `backend/ai-context/CODES/.../app/tests/` | 30 | Vector freshness, mock E2E, isolation |

---

## Environment Variables Reference

| Variable | Service | Default | What it does |
|---|---|---|---|
| `GOOGLE_API_KEY` | AI Gateway | — | **Required.** Google AI Studio key for Gemma LLM |
| `GOOGLE_MODEL` | AI Gateway | `gemma-4-31b-it` | Gemma model version |
| `JWT_SECRET_KEY` | AI Gateway | dev default | Signs/verifies JWT tokens (read by `config.py`). Also set `JWT_SECRET` to the same value — `docker-compose.prod.yml` reads `JWT_SECRET` |
| `JWT_AUTH_REQUIRED` | AI Gateway | `false` | Set `true` to enforce JWT in production |
| `DATABASE_URL` | All services | `postgresql://aev:secret@postgres:5432/aevdb` | PostgreSQL connection |
| `REDIS_URL` | Gateway, Integration | `redis://redis:6379` | Redis connection |
| `AI_CONTEXT_URL` | AI Gateway | `http://ai-context:8001` | Gateway → Context internal call |
| `AI_CONTEXT_TOKEN` | AI Gateway | `aev-internal-service-token-32chars-min` | Auth token for that call |
| `AEV_API_KEYS_JSON` | AI Context | (see .env.example) | API keys allowed to call the Context service |
| `AEV_DATA_SOURCE` | AI Context | `database` | `database` for live data, `mock` for fixtures |
| `SLACK_ALERT_WEBHOOK_URL` | AI Gateway | (empty) | Slack webhook for budget breach alerts |
| `PAGERDUTY_ALERT_WEBHOOK_URL` | AI Gateway | (empty) | PagerDuty routing key for critical alerts |

---

## What Each File Does (Key Files Quick Reference)

### AI Gateway
| File | Purpose |
|---|---|
| `app/main.py` | FastAPI app, all route definitions, startup event |
| `app/guardrails.py` | Input validation, injection blocking, PII redaction |
| `app/tool_router.py` | Natural language → tool name + arguments mapping |
| `app/tools.py` | Tool dispatcher and tool schema definitions |
| `app/jwt_auth.py` | JWT verification, RBAC dependency, token minting |
| `app/cost_tracker.py` | Per-org spend aggregation with PostgreSQL persistence |
| `app/alerts.py` | Slack Block Kit and PagerDuty webhook dispatchers |
| `app/audit_log.py` | Interaction persistence and query endpoints |
| `app/rate_limiter.py` | Redis-backed per-user/org rate limiting |
| `app/client.py` | Google Gemma API client wrapper |

### AI Context
| File | Purpose |
|---|---|
| `app/main.py` | All routes: memory, search, templates, freshness, events |
| `app/models.py` | SQLAlchemy models: Asset, AIMemory, PromptTemplate |
| `app/embedding.py` | Vector embedding generation (384-dim deterministic) |
| `app/freshness_pipeline.py` | Redis event listener, 60s SLA enforcement, re-embedding |
| `app/database.py` | SQLAlchemy engine and session factory |

### Integration Service
| File | Purpose |
|---|---|
| `app/main.py` | FastAPI app setup, router registration |
| `app/routes/integrations.py` | All connector management endpoints |
| `app/registry.py` | Connector catalog and instantiation |
| `app/locking.py` | Redis distributed mutex lock manager |
| `app/storage.py` | In-memory + checkpoint storage (PostgreSQL-backed) |
| `app/models.py` | Pydantic models for API request/response schemas |

### Infrastructure
| File | Purpose |
|---|---|
| `docker-compose.yml` | Development multi-service orchestration |
| `docker-compose.prod.yml` | Production stack with NGINX and isolated networks |
| `nginx/nginx.conf` | NGINX ingress routing rules |
| `scripts/seed_database.py` | Seeds PostgreSQL with unified dataset + embeddings |
| `data/aev_unified_handover_dataset.json` | The canonical demo dataset |
| `run_unified_handover_demo.py` | Zero-dependency full platform demo runner |
| `deploy/k8s/` | Kubernetes raw manifests |
| `deploy/helm/` | Helm v3 chart for production cluster |
