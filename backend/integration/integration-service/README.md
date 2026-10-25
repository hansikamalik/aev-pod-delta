# Integration Service

The **Integration Service** is the central management and execution engine for third-party cloud and endpoint connectors within the AEV Platform.

---

## Capabilities & Architecture

1. **Connector Lifecycle Management:**
   - Registers and manages third-party connectors conforming to the canonical `aev-connector-sdk` v1.0.0 contract (`Connector` and `AsyncConnector`).
   - Supports 19+ platforms including AWS, GCP, CrowdStrike Falcon, Azure, Jira Cloud, GitHub, GitLab, Okta, and Microsoft 365.

2. **Distributed Concurrency Mutex (P1-2):**
   - Implements `SyncLockManager` backed by Redis (`SET lock:sync:{id} {uuid} NX EX 300`).
   - Automatically returns `HTTP 409 Conflict` (`{"error": "sync_in_progress"}`) if an integration is already running a sync job.
   - Releases locks atomically using Lua scripts with thread-safe in-memory fallback.

3. **Persistent Sync Checkpoints (P1-2):**
   - Automatically writes sync progress, pagination cursors, and execution status to PostgreSQL table `sync_checkpoints`.
   - Accessible via `GET /api/v1/integrations/{id}/checkpoint`.

4. **Canonical Connector SDK v1.0.0 (P1-5):**
   - Uses the unified canonical SDK (`connector_sdk`) with dual snake_case / camelCase property serialization and structured domain exceptions.

---

## API Endpoints

| Method | Path | Description | Access |
|---|---|---|---|
| `GET` | `/health` | Service health status | Public |
| `GET` | `/api/v1/integrations` | List all configured connectors | Authenticated |
| `POST` | `/api/v1/integrations` | Register a new integration connector | Authenticated |
| `GET` | `/api/v1/integrations/{id}` | Retrieve details of a specific integration | Authenticated |
| `PUT` | `/api/v1/integrations/{id}` | Update integration configuration or credentials | Authenticated |
| `DELETE` | `/api/v1/integrations/{id}` | Delete an integration | Authenticated |
| `POST` | `/api/v1/integrations/{id}/sync` | Trigger an ingestion sync run (Redis locked) | Authenticated |
| `GET` | `/api/v1/integrations/{id}/checkpoint` | Retrieve persistent sync checkpoint state | Authenticated |
| `GET` | `/api/v1/integrations/{id}/health` | Perform real-time connectivity health check | Authenticated |

---

## Setup & Local Run

### Option 1: Docker Compose (Port 8003)
Run as part of the multi-container stack:
```bash
docker compose up integration-service --build -d
```

### Option 2: Local Python Execution
```bash
# 1. Install dependencies
pip install -r requirements.txt
pip install -e ../../connector-sdk

# 2. Configure environment
export DATABASE_URL="postgresql://aev:secret@localhost:5432/aevdb"
export REDIS_URL="redis://localhost:6379"

# 3. Start service
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

---

## Running Tests

Run the full integration test suite:
```bash
pytest -c ../pytest.ini -v
```
All 36 tests (API endpoints, Redis distributed locking, PostgreSQL checkpoints, and connector contract tests) will execute and pass.
