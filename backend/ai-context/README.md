# AEV AI Context Service

The **AI Context Service** (Squad Lead: Shanmukha Satya Yandra) serves as the persistent memory, template repository, and vector-embedded research assistant for the AEV Platform and AI Gateway Copilot.

---

## Capabilities

1. **Semantic Vector Search (`/copilot/asset-search`):**
   - Natural language search over infrastructure assets using pgvector (PostgreSQL).
   - Generates 384-dimensional dense embeddings with `all-MiniLM-L6-v2`.
   - Accelerated with an HNSW vector index for low-latency lookups.

2. **Multi-Tenant User Memory Store (`/memory`):**
   - Four specialized memory types: `preference`, `workflow`, `role_context`, `recent_topic`.
   - Strict tenant isolation: users can only read, update, or delete their own memories.
   - 90-day automatic retention and expiry job (`app/expiry_job.py`).

3. **Versioned Prompt Templates (`/templates`):**
   - Reusable system prompt repository (`asset_security_summary`, `incident_remediation_plan`).
   - Append-only versioning: new versions are created (v1, v2) while preserving complete history.

---

## API Endpoints

| Method | Path | Description | Access |
|---|---|---|---|
| `GET` | `/health` | Service health status | Public |
| `POST` | `/copilot/asset-search` | Semantic meaning-based search over assets | Internal / Copilot |
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

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the service (Port 8002 to avoid clash with AI Gateway :8001)
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```
