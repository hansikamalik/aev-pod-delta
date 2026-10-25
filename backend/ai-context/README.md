# AEV AI Context Service

The **AI Context Service** (Squad Lead: Shanmukha Satya Yandra) serves as the persistent memory, template repository, vector-embedded research assistant, and real-time freshness pipeline for the AEV Platform and AI Gateway Copilot.

---

## Capabilities

1. **Semantic Vector Search (`/copilot/asset-search`):**
   - Natural language search over infrastructure assets using pgvector (PostgreSQL 15).
   - Generates 384-dimensional dense embeddings (`all-MiniLM-L6-v2`) with deterministic unit vector fallback in lightweight environments.
   - Accelerated with an HNSW vector index for low-latency lookups.

2. **Real-Time Vector Freshness Pipeline (P1-4 - 60s SLA):**
   - Event-driven pipeline consuming `AssetUpdated`, `ExposureDetected`, and `RiskCalculated` events.
   - Ingests via Redis Pub/Sub (`aev:events:asset_changes`) and synchronous webhook (`POST /events/ingest`).
   - Automatically regenerates embeddings, updates `updated_at` and `embedding_updated_at`, measures lag, and enforces the 60-second Freshness SLA.
   - Monitors real-time SLA metrics via `GET /copilot/freshness-metrics` and `GET /events/metrics`.

3. **Multi-Tenant User Memory Store (`/memory`):**
   - Four specialized memory types: `preference`, `workflow`, `role_context`, `recent_topic`.
   - Strict tenant isolation: users can only read, update, or delete their own memories.
   - 90-day automatic retention and expiry job (`app/expiry_job.py`).

4. **Versioned Prompt Templates (`/templates`):**
   - Reusable system prompt repository (`asset_security_summary`, `incident_remediation_plan`).
   - Append-only versioning: new versions are created (v1, v2) while preserving complete history.

---

## API Endpoints

| Method | Path | Description | Access |
|---|---|---|---|
| `GET` | `/health` | Service health status | Public |
| `POST` | `/copilot/asset-search` | Semantic meaning-based search over assets | Internal / Copilot |
| `POST` | `/events/ingest` | Ingest asset change event & re-embed (P1-4) | Admin / Service |
| `GET` | `/events/metrics` | Real-time Freshness SLA metrics report (P1-4) | Internal / Admin |
| `GET` | `/copilot/freshness-metrics` | Persisted snapshot & pipeline freshness SLA stats | Internal / Copilot |
| `POST` | `/memory` | Create a new user memory with vector embedding | Authenticated User |
| `GET` | `/memory/user/{user_id}` | Retrieve memories for a specific user | Resource Owner |
| `PUT` | `/memory/{id}` | Update memory text | Resource Owner |
| `DELETE` | `/memory/{id}` | Delete memory | Resource Owner |
| `GET` | `/memory` | Query all platform memories | Admin Role Only |
| `POST` | `/templates` | Register a new prompt template (v1) | Admin / Analyst |
| `PUT` | `/templates/{name}` | Increment template version (v2, v3...) | Admin / Analyst |
| `GET` | `/templates/{name}/versions` | View full version history of a template | Admin / Analyst |

---

## Setup & Local Run

### Option 1: Docker Compose (Port 8002)

```bash
docker compose up ai-context --build -d
```

### Option 2: Local Python Execution

```bash
# 1. Navigate to handover service directory
cd backend/ai-context/CODES/AEV_AI_CONTEXT_Handover

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
export DATABASE_URL="postgresql+psycopg2://aev:secret@localhost:5432/aevdb"
export AEV_API_KEYS_JSON='{"aev-internal-service-token-32chars-min":{"user_id":"admin","role":"admin"}}'
export AEV_DATA_SOURCE="database" # or "mock"

# 4. Run service on port 8002
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

---

## Testing

Run the isolated AI Context test suite:

```bash
cd backend/ai-context/CODES/AEV_AI_CONTEXT_Handover
PYTHONPATH=. python3 -m pytest app/tests/test_freshness_pipeline.py app/tests/test_mock_data.py -o pythonpath=.
```
