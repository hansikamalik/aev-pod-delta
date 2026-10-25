# AEV Platform – Pod Delta (Module 4 Backend)

[![CI](https://github.com/hansikamalik/aev-pod-delta/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/hansikamalik/aev-pod-delta/actions/workflows/ci.yml)
[![Branch](https://img.shields.io/badge/branch-develop-blue.svg)](https://github.com/hansikamalik/aev-pod-delta/tree/develop)
[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)](https://github.com/hansikamalik/aev-pod-delta)
[![Status](https://img.shields.io/badge/status-100%25%20Production%20Ready-brightgreen.svg)](SPRINT_BACKLOG_AND_PRIORITY_ROADMAP.md)

Welcome to **Pod Delta (Module 4 Backend)** of the Adversarial Exposure Validation (AEV) Platform. Pod Delta provides the user experience layer, AI-powered security investigation Copilot, semantic vector context retrieval, and enterprise connector integration hub.

---

## 🏛️ System Architecture

Pod Delta orchestrates three specialized FastAPI microservices backed by PostgreSQL 15 (`pgvector`) and Redis 7, fronted by an NGINX ingress reverse proxy:

```
                            ┌────────────────────────────────────────┐
                            │            External Traffic            │
                            └───────────────────┬────────────────────┘
                                                │ (HTTP :80 / :443)
                                                ▼
                            ┌────────────────────────────────────────┐
                            │        NGINX Ingress Reverse Proxy     │
                            └───────┬───────────┬────────────┬───────┘
                                    │           │            │
            /api/v1/copilot         │           │            │ /api/v1/integrations
    ┌───────────────────────────────┘           │            └──────────────────────────────┐
    ▼                                           ▼ /api/v1/context                           ▼
┌──────────────────────────┐       ┌──────────────────────────┐       ┌──────────────────────────┐
│    AI Gateway (:8001)    │       │    AI Context (:8002)    │       │ Integration Svc (:8003)  │
│  FastAPI / Gemma 4 LLM   │       │   FastAPI / pgvector     │       │  FastAPI / Connector SDK │
│  • JWT Auth & Trust      │◄─────►│   • 384-dim HNSW Vector  │       │  • Redis Mutex Locks     │
│  • Dynamic Tool Router   │       │   • 60s Freshness SLA    │       │  • Postgres Checkpoints  │
│  • Enterprise Guardrails │       │   • Multi-Tenant Memory  │       │  • 19+ Cloud Connectors  │
│  • Spend & Webhooks      │       │   • Versioned Templates  │       │  • Canonical SDK v1.0.0  │
└────────────┬─────────────┘       └────────────┬─────────────┘       └────────────┬─────────────┘
             │                                  │                                  │
             └──────────────────────────────────┼──────────────────────────────────┘
                                                │
                                                ▼
                     ┌─────────────────────────────────────────────────────┐
                     │            Shared Infrastructure Layer              │
                     │  • PostgreSQL 15 (pgvector extension) :5432         │
                     │  • Redis 7 In-Memory Cache & Pub/Sub :6379          │
                     └─────────────────────────────────────────────────────┘
```

---

## 📦 Squad & Service Breakdown

| Squad | Directory | Technology | Key Capabilities |
|---|---|---|---|
| **1. AI Gateway** | [`backend/ai-gateway/`](backend/ai-gateway/) | FastAPI, Google Gemma LLM | Dynamic tool reasoning, prompt guardrails, PII redaction, JWT dual-mode auth, persistent spend tracking with Slack/PagerDuty webhooks |
| **2. AI Context** | [`backend/ai-context/`](backend/ai-context/) | FastAPI, pgvector, SQLAlchemy | 384-dim semantic vector search (`/copilot/asset-search`), real-time event freshness pipeline (<60s SLA), isolated user memory store |
| **3. Connector SDK** | [`backend/connector-sdk/`](backend/connector-sdk/) | Python 3.12, Pydantic v2 | Canonical `Connector` and `AsyncConnector` base contracts v1.0.0, packaged as installable Python wheel `aev-connector-sdk` |
| **4. Integration Hub** | [`backend/integration/`](backend/integration/) | FastAPI, Redis, PostgreSQL | 19+ cloud/SaaS/EDR connectors (AWS, GCP, CrowdStrike, Azure, Jira, etc.), Redis distributed locking, persistent PostgreSQL checkpoints |
| **5. Shared Infra** | [`deploy/`](deploy/), [`nginx/`](nginx/) | Docker Compose, NGINX, K8s, Helm | Unified production compose, NGINX reverse proxy, Kubernetes manifests, and production Helm chart |

---

## 🚀 Quickstart

### 1. Unified Handover Demo (< 1 second)
Run the self-contained end-to-end demonstration walking through all 8 platform subsystems using the unified dataset:
```bash
python3 run_unified_handover_demo.py
```

### 2. Multi-Container Stack (Development)
Spin up PostgreSQL (pgvector), Redis, and all three services with hot reload:
```bash
docker compose up --build
```
- AI Gateway: `http://localhost:8001` (Docs: `/docs`)
- AI Context: `http://localhost:8002` (Docs: `/docs`)
- Integration Service: `http://localhost:8003` (Docs: `/docs`)

### 3. Production Stack with NGINX Ingress Reverse Proxy
Spin up the production architecture with internal service isolation and unified NGINX ingress on port 80:
```bash
# 1. Prepare environment
cp .env.example .env

# 2. Launch production stack
docker-compose -f docker-compose.prod.yml up -d
```
Traffic is unified under `http://localhost:80`:
- `/api/v1/copilot` ➔ AI Gateway
- `/api/v1/context` ➔ AI Context
- `/api/v1/integrations` ➔ Integration Service
- `/health` ➔ Ingress health status

### 4. Kubernetes & Helm Staging/Production Deployment
Deploy to Kubernetes using Helm v3:
```bash
helm install aev-pod-delta deploy/helm/aev-pod-delta \
  --namespace aev-system \
  --create-namespace \
  --set secrets.postgresPassword="your_strong_password" \
  --set secrets.googleApiKey="your_google_api_key" \
  --set secrets.jwtSecret="your_jwt_secret_min_32_chars"
```
Or apply raw manifests directly:
```bash
kubectl apply -f deploy/k8s/
```
See [`deploy/README.md`](deploy/README.md) for full deployment instructions.

---

## 🧪 Testing & Verification

The repository contains 436 automated unit and integration tests across all microservices:

```bash
# 1. Run root suite (AI Gateway & Connector SDK) — 370 tests
python3 -m pytest -c pytest.ini

# 2. Run Integration Service suite — 36 tests
cd backend/integration && python3 -m pytest -c pytest.ini

# 3. Run AI Context suite — 30 tests
cd backend/ai-context/CODES/AEV_AI_CONTEXT_Handover && PYTHONPATH=. python3 -m pytest app/tests/ -o pythonpath=.
```

**Total:** **436 passed, 0 failures, 100% green.**

Automated CI executes on every push and pull request via [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

---

## 📚 Documentation Index

| Guide | Description |
|---|---|
| [`SETUP.md`](SETUP.md) | Master step-by-step setup guide for all services, environment variables, and local execution |
| [`HANDOVER_EXECUTIVE_GUIDE.md`](HANDOVER_EXECUTIVE_GUIDE.md) | Executive presentation runbook and unified dataset verification walkthrough |
| [`DEVELOPER_HANDOVER_QUICKSTART.md`](DEVELOPER_HANDOVER_QUICKSTART.md) | Engineering deep-dive into unified datasets, demo runner, and cross-service data models |
| [`SPRINT_BACKLOG_AND_PRIORITY_ROADMAP.md`](SPRINT_BACKLOG_AND_PRIORITY_ROADMAP.md) | Complete priority roadmap tracking all P0, P1, and P2 deliverables |
| [`backend/ai-gateway/README.md`](backend/ai-gateway/README.md) | AI Gateway architecture, dynamic tools, guardrails, JWT auth, and spend alerts |
| [`backend/ai-context/README.md`](backend/ai-context/README.md) | AI Context pgvector setup, memory store, templates, and 60s freshness pipeline |
| [`backend/connector-sdk/CONNECTOR_SDK_GUIDE.md`](backend/connector-sdk/CONNECTOR_SDK_GUIDE.md) | Connector SDK v1.0.0 developer contract, async lifecycle, wheel build & install |
| [`backend/integration/README.md`](backend/integration/README.md) | Integration Service APIs, Redis distributed mutexes, and PostgreSQL sync checkpoints |
| [`docs/VENDOR_SANDBOX_TRIALS.md`](docs/VENDOR_SANDBOX_TRIALS.md) | Operational runbook for live vendor sandbox testing (Jira, Azure, GitHub) |
| [`docs/AUTH_CONTRACT_POD_ALPHA.md`](docs/AUTH_CONTRACT_POD_ALPHA.md) | Pod Alpha cryptographic JWT trust boundary & token schema |
| [`deploy/README.md`](deploy/README.md) | Kubernetes and Helm cluster operations and secrets management guide |
