# AEV Platform – Pod Delta (Module 4 Backend)
# Master Setup & Operations Guide

Welcome to the **AEV Pod Delta** repository. This guide provides comprehensive, step-by-step instructions to configure, run, and test all backend microservices locally and within Docker container environments.

---

## 1. System Architecture & Port Allocation

The Pod Delta backend consists of three core FastAPI microservices backed by PostgreSQL 15 (with `pgvector`) and Redis 7:

```
                      ┌────────────────────────────────────────┐
                      │             Pod Alpha Ingress          │
                      └───────────────────┬────────────────────┘
                                          │ (JWT Bearer Token)
                                          ▼
                      ┌────────────────────────────────────────┐
                      │    AI Gateway Service (:8001)          │
                      │    Gemma LLM • Guardrails • Citations  │
                      └───────┬────────────────────────┬───────┘
                              │                        │
               (Vector Search)│                        │(Sync Triggers)
                              ▼                        ▼
┌──────────────────────────────────────┐     ┌──────────────────────────────────────┐
│       AI Context Service (:8002)     │     │      Integration Service (:8003)     │
│ pgvector RAG • Memory • Freshness SLA│     │ Redis Mutex Locks • Connectors • DB  │
└──────────────────┬───────────────────┘     └──────────────────┬───────────────────┘
                   │                                            │
                   ▼                                            ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│               Shared Infrastructure: PostgreSQL 15 (pgvector) & Redis 7           │
└───────────────────────────────────────────────────────────────────────────────────┘
```

| Service | Host Port | Container Port | Technology | Primary Purpose |
|---|---|---|---|---|
| **PostgreSQL** | `5432` | `5432` | `pgvector/pgvector:pg15` | Audit logging, memory, vector embeddings, sync checkpoints |
| **Redis** | `6379` | `6379` | `redis:7` | Distributed locking, rate limiting, pub/sub events |
| **AI Gateway** | `8001` | `8000` | FastAPI / Gemma LLM | Copilot reasoning, guardrails, citations, spend tracking |
| **AI Context** | `8002` | `8001` | FastAPI / pgvector | Semantic asset vector search, memories, 60s freshness pipeline |
| **Integration Service** | `8003` | `8000` | FastAPI / Connector SDK | Multi-cloud connectors, sync engine, Redis mutex locking |

---

## 2. Quickstart Options

### Option A: Complete Multi-Container Stack (Docker Compose)

Starts all services, provisions pgvector, and links internal communication:

```bash
# 1. Start all containers in the background
docker compose up --build -d

# 2. Seed database with canonical dataset and 384-dimensional pgvector embeddings
python3 scripts/seed_database.py

# 3. Verify health across all microservices
curl http://localhost:8001/health  # AI Gateway: {"status": "healthy"}
curl http://localhost:8002/health  # AI Context: {"status": "Healthy"}
curl http://localhost:8003/health  # Integration Service: {"status": "ok"}
```

---

### Option B: Local Standalone Development (Without Docker)

You can run each service directly with Python 3.12:

#### 1. AI Gateway Service (Port 8001)
```bash
cd backend/ai-gateway
pip install -r requirements.txt
export DATABASE_URL="postgresql://aev:secret@localhost:5432/aevdb"
export REDIS_URL="redis://localhost:6379"
export AI_CONTEXT_URL="http://localhost:8002"
export AI_CONTEXT_TOKEN="aev-internal-service-token-32chars-min"
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

#### 2. AI Context Service (Port 8002)
```bash
cd backend/ai-context/CODES/AEV_AI_CONTEXT_Handover
pip install -r requirements.txt
export DATABASE_URL="postgresql+psycopg2://aev:secret@localhost:5432/aevdb"
export AEV_API_KEYS_JSON='{"aev-internal-service-token-32chars-min":{"user_id":"admin","role":"admin"}}'
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

#### 3. Integration Service (Port 8003)
```bash
cd backend/integration/integration-service
pip install -r requirements.txt
export DATABASE_URL="postgresql://aev:secret@localhost:5432/aevdb"
export REDIS_URL="redis://localhost:6379"
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

---

### Option C: Zero-Dependency Master Handover Demo Runner

To run a complete terminal demonstration across all five subsystems using the single unified dataset without starting external servers or Docker:

```bash
python3 run_unified_handover_demo.py
```

---

## 3. Running the Test Suite (419 Tests)

All services maintain unit and integration test coverage:

```bash
# 1. Root Suite (370 tests: AI Gateway, AWS, GCP, CrowdStrike, Jira, Canonical SDK)
python3 -m pytest -c pytest.ini

# 2. Integration Suite (36 tests: Integration API, Redis locks, checkpoints, Jira)
cd backend/integration && python3 -m pytest -c pytest.ini

# 3. AI Context Suite (13 tests: Freshness 60s SLA pipeline, mock data E2E, isolation)
cd backend/ai-context/CODES/AEV_AI_CONTEXT_Handover && PYTHONPATH=. python3 -m pytest app/tests/ -o pythonpath=.
```

---

## 4. Environment Variables Reference

| Variable | Service | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | All | `postgresql://aev:secret@postgres:5432/aevdb` | PostgreSQL connection string |
| `REDIS_URL` | Gateway, Integration | `redis://redis:6379` | Redis host for mutex locks and rate limits |
| `JWT_SECRET_KEY` | Gateway | `aev-pod-delta-jwt-secret-shared-key-32chars-min` | Secret key for JWT cryptographic validation |
| `JWT_AUTH_REQUIRED` | Gateway | `false` (dev) / `true` (prod) | Strict JWT enforcement toggle |
| `SLACK_ALERT_WEBHOOK_URL` | Gateway | `""` | Incoming webhook for Block Kit budget alerts |
| `PAGERDUTY_ALERT_WEBHOOK_URL`| Gateway | `""` | PagerDuty Events API v2 routing key/endpoint |
| `AI_CONTEXT_URL` | Gateway | `http://ai-context:8001` | Base URL to call AI Context vector search |
| `AEV_API_KEYS_JSON` | Context | `{"token":{"user_id":"admin","role":"admin"}}` | API key authentication mapping |
| `AEV_DATA_SOURCE` | Context | `database` (`mock` for standalone) | Storage backend toggle |
| `REDIS_EVENTS_CHANNEL` | Context | `aev:events:asset_changes` | Redis Pub/Sub channel for asset freshness events |
