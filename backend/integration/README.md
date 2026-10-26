# Integration Hub & Integration Service

The **Integration Service** (Squad Lead: Harshal Sahare / Vatsal Thummar) manages third-party cloud and endpoint connectors (AWS, GCP, CrowdStrike, Jira, Azure, etc.), coordinates distributed synchronization schedules, enforces distributed concurrency mutexes, and persists ingestion checkpoints.

---

## Architecture & Core Features

1. **Connector Registry & Orchestration:**
   - Registers third-party connectors conforming to the canonical `connector-sdk v1.0.0` interface.
   - Provides standardized health checks, configuration validation, credential verification, and automated discovery-to-ingest lifecycles.

2. **Distributed Concurrency Control (P1-2):**
   - Employs Redis distributed mutexes (`SET lock:sync:{id} {uuid} NX EX 300`) to prevent concurrent sync executions.
   - Immediately returns `HTTP 409 Conflict` (`{"error": "sync_in_progress"}`) if an integration is already running a sync job.
   - Releases locks atomically using safe Lua script comparisons, with thread-safe in-memory fallback.

3. **Persistent Sync Checkpoints (P1-2):**
   - Automatically writes cursor progress and execution status to PostgreSQL table `sync_checkpoints`.
   - Records `last_sync_time`, `records_synced`, `status` (`success`, `partial`, `failed`), and `error_message`.
   - Exposes inspection endpoint at `GET /integrations/{id}/checkpoint`.

4. **Integration CRUD & Execution API:**
   - Full RESTful lifecycle for creating, updating, listing, and triggering integrations.

---

## API Endpoints (`integration-service`)

| Method | Path | Description | Access |
|---|---|---|---|
| `GET` | `/health` | Service health status | Public |
| `GET` | `/integrations` | List all configured connectors | Authenticated |
| `POST` | `/integrations` | Register a new integration connector | Authenticated |
| `GET` | `/integrations/{id}` | Retrieve details of a specific integration | Authenticated |
| `PUT` | `/integrations/{id}` | Update integration configuration / credentials | Authenticated |
| `DELETE` | `/integrations/{id}` | Delete an integration | Authenticated |
| `POST` | `/integrations/{id}/sync` | Trigger an ingestion sync run (Redis locked) | Authenticated |
| `GET` | `/integrations/{id}/checkpoint`| Retrieve persistent sync checkpoint state | Authenticated |
| `GET` | `/integrations/{id}/health` | Perform real-time connectivity health check | Authenticated |

---

## Local Setup & Run

### Option 1: Docker Compose (Recommended)
Run as part of the multi-container stack on port `8003`:

```bash
docker compose up integration-service --build -d
```

### Option 2: Local Python Execution

```bash
# 1. Navigate to integration service directory
cd backend/integration/integration-service

# 2. Install dependencies
pip install -r requirements.txt

# 3. Environment configuration
export DATABASE_URL="postgresql://aev:secret@localhost:5432/aevdb"
export REDIS_URL="redis://localhost:6379"

# 4. Start service (Port 8003 to prevent port collision with Gateway :8001 / Context :8002)
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

---

## Running Integration Tests

Run the dedicated integration test suite from `backend/integration`:

```bash
cd backend/integration
python3 -m pytest -c pytest.ini
```
All 36 tests (API endpoints, Redis distributed locking, PostgreSQL checkpoints, and connector contract tests) will execute.
