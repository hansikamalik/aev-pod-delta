# AEV Pod Delta (Module 4 Backend)
# Sprint Backlog & Priority Roadmap

> **Prepared for:** Engineering Team & Squad Leads  
> **Branch:** `develop` | **Last Synced:** October 24, 2026  
> **Overall Project Completion:** ~68% | Alpha / Staging Ready  
> **Estimated Time to Production:** 6–8 Weeks

---

## 📊 Overall Status Scorecard

```
┌───────────────────────────┬──────────────┬──────────────────┬────────────────────────┐
│ Squad / Domain            │ Completion % │ Production Ready │ Primary Focus          │
├───────────────────────────┼──────────────┼──────────────────┼────────────────────────┤
│ 1. AI Gateway             │ 85%          │ Amber (Staging)  │ Dynamic tool calling   │
│ 2. AI Context             │ 85%          │ Green (Verified) │ Freshness pipeline     │
│ 3. Connector SDK          │ 80%          │ Green (Verified) │ Package as wheel       │
│ 4. Integration Hub        │ 80%          │ Green (Verified) │ Hyphenated folder rename│
│ 5. Shared Infra & Ingress │ 50%          │ Amber (Staging)  │ Compose & Ingress      │
│ 6. Web Frontend           │ 0%           │ Not Started      │ External dependency    │
├───────────────────────────┼──────────────┼──────────────────┼────────────────────────┤
│ Overall Pod Delta Backend │ 76%          │ Staging Ready    │ ~4–5 Weeks to Prod     │
└───────────────────────────┴──────────────┴──────────────────┴────────────────────────┘
```

---

## Priority Legend

| Symbol | Priority Level | Meaning |
| :---: | :--- | :--- |
| 🔴 **P0** | Critical Blocker | Blocks MVP launch; must be done first |
| 🟡 **P1** | High / Architecture | Required for enterprise reliability & scale |
| 🟢 **P2** | Medium / Ops & Polish | Production packaging, CI/CD, Kubernetes |

---

## 🔴 P0 — Critical Blockers (Must-Do for MVP)

---

### P0-1 · Integrate AI Context into Multi-Service Container Architecture (Completed ✅)
- **Squad:** Squad 2 (AI Context) + Squad 1 (AI Gateway)
- **Effort:** 3–4 Days
- **Priority Rating:** ⭐⭐⭐⭐⭐ (5/5 — Blocks live semantic search)
- **Status:** **COMPLETED ✅** (pgvector PostgreSQL 15 live container, vector schema migrations, deterministic 384-dim dataset seeder `scripts/seed_database.py`, Gateway `AI_CONTEXT_TOKEN` authentication in `asset_search.py`, multi-service `docker-compose.yml` orchestration)

#### Problem
Squad 2 delivered a handover candidate in `backend/ai-context/CODES/AEV_AI_CONTEXT_Handover/`, but it currently runs in complete isolation and cannot be invoked from the AI Gateway. Specifically:
- Requires heavy dependencies: `torch`, `sentence-transformers`, `pgvector`, `sqlalchemy`.
- The running `aev_postgres` container is standard `postgres:15` **without** the `pgvector` extension installed.
- In the repository root, `import app` collides with AI Gateway's `app` module namespace.
- The AI Gateway's `asset_search` tool currently falls back to local JSON mocks because `AI_CONTEXT_URL` is not connected.

#### Work Required
1. Build and push a dedicated Docker image for `ai-context` exposing port `8002`.
2. Upgrade the database Docker image from `postgres:15` to `pgvector/pgvector:pg15` to enable vector similarity search (`vector(384)` column type).
3. Apply AI Context migration: `backend/ai-context/CODES/AEV_AI_CONTEXT_Handover/migrations/001_asset_embedding_freshness.sql`.
4. Run `python -m app.generate_asset_embeddings` inside the container to seed vector data.
5. Set `AI_CONTEXT_URL=http://ai-context:8002` in the AI Gateway environment and verify the `asset_search` tool dispatches HTTP requests to it.
6. Update root `docker-compose.yml` to include the `ai-context` service.

---

### P0-2 · Build Integration Service Management REST API
- **Squad:** Squad 4 (Integrations) — Lead: Harshal Sahare
- **Effort:** 4–5 Days
- **Priority Rating:** ⭐⭐⭐⭐⭐ (5/5 — No way to manage connectors through the platform)

#### Problem
`backend/integration/integration-service/` only contains a `/health` endpoint stub. There is no orchestration API for the platform to register, configure, trigger, or monitor connectors.

#### Work Required
1. Implement the following REST endpoints backed by PostgreSQL:

   | Endpoint | Description |
   | :--- | :--- |
   | `POST /api/v1/integrations` | Register & configure a connector |
   | `GET /api/v1/integrations` | List all active connectors + status |
   | `GET /api/v1/integrations/{id}` | Get connector details, health, stats |
   | `POST /api/v1/integrations/{id}/sync` | Trigger immediate on-demand sync |
   | `POST /api/v1/integrations/{id}/test` | Verify credentials & run health check |
   | `PATCH /api/v1/integrations/{id}/disable` | Pause scheduled sync jobs |
   | `GET /api/v1/integrations/{id}/history` | View past sync runs & asset delta counts |

2. Write SQL schema migrations for:
   - `integrations` table: config, encrypted credentials, schedule, status, connector_type.
   - `sync_jobs` table: execution runs, asset counts, error logs, timestamps.
3. Wire existing connector implementations to be triggered through this API.

---

### P0-3 · Enable Dynamic Tool Calling via Gemma LLM Reasoning
- **Squad:** Squad 1 (AI Gateway) — Lead: Hansika Malik
- **Effort:** 3 Days
- **Priority Rating:** ⭐⭐⭐⭐⭐ (5/5 — AI Copilot cannot autonomously decide what to do)

#### Problem
The AI Gateway's Copilot only calls one tool automatically (`risk_score_get`), and only when the pattern `asset-XXX` appears in the user's prompt via a hardcoded regex check. The remaining 6 registered tools — `exposure_query`, `policy_check`, `workflow_assist`, `integration_list`, `report_generate`, `audit_query` — can only be triggered by manually constructing dispatcher calls in code, not by user natural language.

#### Work Required
1. Define function-calling schemas for all 7 registered tools in Gemma / Gemini format (name, description, parameter JSON schema).
2. Implement a routing loop: send tool schemas to the model → receive tool invocation decision → execute the tool → feed structured JSON result back into the model context → generate cited response.
3. Allow multi-turn tool chaining (e.g., query `integration_list` then `exposure_query` in a single conversation turn).
4. Bind actual tool output as dynamic citation sources (replacing placeholder `doc_123` / `example.com` citations).

---

### P0-4 · Build Three Missing Enterprise Connectors
- **Squad:** Squad 4 (Integrations) — Lead: Harshal Sahare
- **Effort:** 5–6 Days
- **Priority Rating:** ⭐⭐⭐⭐⭐ (5/5 — Critical enterprise targets not yet covered)

#### Problem
19 of 22 planned connectors are written. The 3 missing are the highest-priority enterprise platforms:

| Missing Connector | Scope | Why Critical |
| :--- | :--- | :--- |
| **AWS Connector** | EC2, S3, IAM, RDS, Lambda asset discovery | Most common cloud for enterprise targets |
| **GCP Connector** | Compute Engine, Cloud Storage, IAM, Cloud SQL | Second-largest cloud platform |
| **CrowdStrike Falcon** | Endpoint threat detections & EDR telemetry | Most widely deployed EDR in enterprises |

#### Work Required
1. Implement each connector adhering to the canonical `ConnectorSDK` base class interface (`async def sync()`).
2. Implement `discover()`, `ingest()`, `check_health()`, `describe_config()`, `describe_credentials()` methods.
3. Normalize discovered assets into standard `Asset` model schemas.
4. Write unit test suites (minimum 10 tests per connector).
5. Integrate each into the connector registry.

---

### P0-5 · Fix Hyphenated Directory Names in Integration Connectors
- **Squad:** Squad 4 (Integrations)
- **Effort:** 1 Day
- **Priority Rating:** ⭐⭐⭐⭐⭐ (5/5 — Blocks Python import and test suite execution)

#### Problem
Several connector directories use hyphens in their names, which makes them invalid Python package identifiers:

| Current (Broken) | Fix (Valid Python) |
| :--- | :--- |
| `backend/integration/microsoft365-connector/` | `microsoft365_connector/` |
| `backend/integration/active-directory-connector/` | `active_directory_connector/` |
| `backend/integration/microsoft-defender-connector/` | `microsoft_defender_connector/` |
| `backend/integration/google-workspace-auth/` | `google_workspace_auth/` |
| `backend/integration/cyberark-discovery-integration/` | `cyberark_discovery_integration/` |

#### Work Required
1. Rename directories using underscores.
2. Update all internal `import` statements, `pytest.ini` test paths, and `__init__.py` references.
3. Verify full test suite passes after rename.

---

## 🟡 P1 — High Priority: Enterprise Hardening & Scalability

---

### P1-1 · JWT Authentication Middleware & Cryptographic Trust Boundaries
- **Squad:** Squad 1 (AI Gateway) + Shared Infra
- **Effort:** 2–3 Days
- **Priority Rating:** ⭐⭐⭐⭐ (4/5 — Cannot launch in production without this)

#### Problem
The AI Gateway trusts raw HTTP headers `X-User-ID` and `X-User-Role` completely. Any client that knows the header names can claim to be an admin.

#### Work Required
1. Add FastAPI JWT validation middleware that verifies tokens issued by Pod Alpha (Identity & Auth).
2. Extract `user_id`, `role`, and `tenant_id` from the signed token payload.
3. Remove header-based trust; reject all requests without a valid bearer token.
4. Document the token format contract for Pod Alpha integration.

---

### P1-2 · Redis Distributed Locking & PostgreSQL-Backed Sync Checkpoints
- **Squad:** Squad 4 (Integrations)
- **Effort:** 3 Days
- **Priority Rating:** ⭐⭐⭐⭐ (4/5 — Required before horizontal scaling)

#### Problem
- `HardenedSyncEngine` uses an in-memory `threading.Lock`. When scaled to multiple containers, concurrent syncs on the same connector will collide.
- Sync checkpoints are saved to local JSON files — these are lost on container restart or pod migration.

#### Work Required
1. Replace `threading.Lock` with the existing `shared_infra/src/distributed_lock.py` backed by Redis.
2. Store sync checkpoints (`last_sync_at`, pagination cursor, retry count) in the `sync_jobs` PostgreSQL table.
3. Add `REDIS_URL` to the Integration Service environment configuration.

---

### P1-3 · Persistent Spend Tracking & External Alert Webhooks
- **Squad:** Squad 1 (AI Gateway)
- **Effort:** 2 Days
- **Priority Rating:** ⭐⭐⭐⭐ (4/5 — Required for multi-tenant billing and enterprise ops)

#### Problem
- `CostTracker._org_spend` is an in-memory Python dictionary. Every service restart resets all org budgets to $0.00.
- Budget breach alerts (80%, 100% threshold) only print to console — no real notification fires.

#### Work Required
1. Aggregate spend live from PostgreSQL: `SELECT SUM(cost) FROM ai_interactions WHERE org_id = :org_id`.
2. Cache aggregates in Redis for high-frequency checks.
3. Add `org_id` column to the `ai_interactions` table migration.
4. Wire `ALERT_WEBHOOK_URL` to POST budget breach and error spike JSON payloads to Slack / PagerDuty / Microsoft Teams.

---

### P1-4 · Real-Time Vector Freshness Event Pipeline (60s SLA)
- **Squad:** Squad 2 (AI Context) — Lead: Shanmukha Satya Yandra
- **Effort:** 3 Days
- **Priority Rating:** ⭐⭐⭐⭐ (4/5 — Core SLA from design doc; code not yet committed)

#### Problem
Squad 2's Week 4 progress report outlines an event-driven pipeline that reacts to `AssetUpdated`, `ExposureDetected`, and `RiskCalculated` events within 60 seconds and re-computes vector embeddings. **This pipeline code has not yet been committed to the repository.**

#### Work Required
1. Implement a Redis Pub/Sub listener or webhook consumer inside the AI Context service.
2. On event receipt: parse asset payload, regenerate embedding via `generate_asset_embeddings.py`, update `embedding_updated_at` and `updated_at` columns.
3. Verify measured lag stays under 60 seconds under normal load.
4. Expose the freshness SLA status at `GET /copilot/freshness-metrics`.

---

### P1-5 · Canonical Connector SDK Single-Version Reconciliation
- **Squad:** Squad 3 (Connector SDK) — Lead: Likith TV
- **Effort:** 2 Days
- **Priority Rating:** ⭐⭐⭐⭐ (4/5 — Tech debt causing divergence across 19 connectors)

#### Problem
Two parallel implementations of the base SDK exist:
- **Version A:** `backend/connector-sdk/connector_sdk/` — synchronous `def sync()`.
- **Version B:** `backend/integration/` local copies — `async def sync()` with camelCase vs snake_case mismatches (`discovered_at` vs `discoveredAt`).

#### Work Required
1. Formally adopt `async def sync()` as the single canonical standard.
2. Deprecate Version A synchronous SDK.
3. Migrate all 19+ connectors to the canonical async contract.
4. Freeze the interface with a version tag in `pyproject.toml`.

---

## 🟢 P2 — Medium Priority: Production Ops, Packaging & Deployment

---

### P2-1 · Unified Root Docker Compose & NGINX Ingress Reverse Proxy
- **Squad:** Shared Infrastructure
- **Effort:** 2 Days
- **Priority Rating:** ⭐⭐⭐ (3/5)

#### Problem
Individual sub-services have separate Dockerfiles and docker-compose files with port conflicts. There is no reverse proxy routing public traffic across microservices.

#### Work Required
1. Create `docker-compose.prod.yml` at the repository root orchestrating all services:

   | Service | Port | Image |
   | :--- | :--- | :--- |
   | `ingress` (NGINX) | 80 / 443 | `nginx:alpine` |
   | `ai-gateway` | 8001 | Built from `backend/ai-gateway/` |
   | `ai-context` | 8002 | Built from `backend/ai-context/` |
   | `integration-service` | 8000 | Built from `backend/integration/integration-service/` |
   | `postgres` | 5432 | `pgvector/pgvector:pg15` |
   | `redis` | 6379 | `redis:7` |

2. Write NGINX config routing:
   - `/api/v1/copilot` → AI Gateway `:8001`
   - `/api/v1/context` → AI Context `:8002`
   - `/api/v1/integrations` → Integration Service `:8000`

---

### P2-2 · Package Connector SDK as Installable Python Wheel
- **Squad:** Squad 3 (Connector SDK)
- **Effort:** 1 Day
- **Priority Rating:** ⭐⭐⭐ (3/5)

#### Problem
Connectors rely on local `PYTHONPATH` tricks and copy-pasted base classes. No installable distribution exists.

#### Work Required
1. Add `pyproject.toml` to `backend/connector-sdk/`.
2. Configure the package as `aev-connector-sdk` so any service can run:
   ```bash
   pip install -e backend/connector-sdk
   ```
3. Move public interface classes to a clean `connector_sdk/__init__.py` export.

---

### P2-3 · Live Vendor Sandbox Validation Trials
- **Squad:** Squad 4 (Integrations)
- **Effort:** 3–4 Days
- **Priority Rating:** ⭐⭐⭐ (3/5)

#### Problem
All 19 connectors have only been validated against local mocks and simulated fixtures. No connector has been tested against a real third-party developer account.

#### Work Required
1. Obtain developer / sandbox credentials for at least 3 high-value platforms (Jira Cloud, Azure Sandbox, GitHub App).
2. Run live end-to-end discovery syncs in a controlled staging environment.
3. Document connector-specific edge cases and API rate limits encountered.

---

### P2-4 · Kubernetes Manifests & Helm Charts
- **Squad:** Shared Infrastructure
- **Effort:** 2–3 Days
- **Priority Rating:** ⭐⭐ (2/5 — Not urgent until P0/P1 complete)

#### Problem
Only Docker configurations exist. No Kubernetes deployment specifications for staging or production cluster deployment.

#### Work Required
1. Write Helm templates or K8s manifests: `Deployment`, `Service`, `ConfigMap`, `Secret`, `HorizontalPodAutoscaler`.
2. Write a root `Ingress` resource for external traffic routing.
3. Document secrets management approach (Vault integration or K8s Secret Store CSI).

---

## 🗓️ Recommended Sprint Plan

```
Phase 1 — Foundation Fixes (Days 1–3)
  ├── P0-5  Rename hyphenated directories → valid Python packages
  ├── P1-5  Reconcile Connector SDK to single async version
  └── P0-3  Wire dynamic tool calling schema definitions (Gemma)

Phase 2 — Core Feature Delivery (Days 4–10)
  ├── P0-1  Build AI Context Docker container + pgvector + wire to Gateway
  ├── P0-2  Build Integration Service CRUD & sync APIs + DB migrations
  └── P1-4  Commit & test real-time vector freshness event pipeline

Phase 3 — New Connectors (Days 11–16)
  └── P0-4  Implement AWS, GCP & CrowdStrike Falcon connectors

Phase 4 — Enterprise Hardening (Days 17–22)
  ├── P1-1  JWT authentication middleware
  ├── P1-2  Redis distributed lock + PostgreSQL sync checkpoints
  └── P1-3  Persistent spend tracking + Slack/PagerDuty alerts

Phase 5 — Deployment & Ops (Days 23–28)
  ├── P2-1  Unified Docker Compose + NGINX ingress
  ├── P2-2  Package Connector SDK as installable wheel
  ├── P2-3  Live vendor sandbox trials (Azure, Jira, GitHub)
  └── P2-4  Kubernetes Helm charts
```

---

## 📋 Quick Checklist Summary

### 🔴 P0 — Do First
- [x] **P0-1** Build `ai-context` Docker container with `pgvector`; wire Gateway `AI_CONTEXT_URL` & auth (Completed ✅)
- [x] **P0-2** Implement Integration Service REST API (~20 endpoints) + DB migrations (Completed ✅)
- [ ] **P0-3** Enable Gemma dynamic tool calling (all 7 tools, multi-turn, real citations)
- [x] **P0-4** Build AWS, GCP & CrowdStrike Falcon connectors (Completed ✅)
- [ ] **P0-5** Rename hyphenated connector directories to valid Python package names

### 🟡 P1 — Do Second
- [ ] **P1-1** Add JWT validation middleware; remove plain-header trust
- [ ] **P1-2** Redis distributed lock + PostgreSQL-backed sync checkpoints
- [ ] **P1-3** DB-backed cost aggregation + external alert webhook (Slack / PagerDuty)
- [ ] **P1-4** Real-time vector freshness event pipeline (60s SLA)
- [ ] **P1-5** Canonical async Connector SDK reconciliation across all 19+ connectors

### 🟢 P2 — Do Third
- [ ] **P2-1** Unified root `docker-compose.prod.yml` + NGINX ingress proxy
- [ ] **P2-2** Package `aev-connector-sdk` as installable Python wheel
- [ ] **P2-3** Live vendor sandbox trials (Jira Cloud, Azure, GitHub App)
- [ ] **P2-4** Kubernetes Helm charts for staging cluster deployment
