# AEV AI Context Service

FastAPI service for memory CRUD, vector asset search, prompt-template versioning, and rule-based Copilot endpoints.

## Run locally / with Docker

1. Create `.env` locally (do not commit it) with `DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME`.
2. Ensure PostgreSQL has the `vector` extension available for pgvector.
3. Start: `docker compose up --build -d`
4. Swagger UI: `http://localhost:8002/docs`
5. Health check: `GET http://localhost:8002/health`

## Authentication (required before using protected endpoints)

The service now uses bearer API keys. Protected endpoints fail closed if `AEV_API_KEYS_JSON` is missing or invalid. Generate separate high-entropy keys locally (do not send them in chat or commit them):

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Run it twice, then edit your private `.env` (copied from `.env.example`) so `AEV_API_KEYS_JSON` maps each generated secret to a principal, for example:

```dotenv
AEV_API_KEYS_JSON='{"YOUR_GENERATED_ADMIN_KEY":{"user_id":"admin","role":"admin"},"YOUR_GENERATED_USER_KEY":{"user_id":"user1","role":"user"}}'
```

Restart the service after changing `.env`. Send keys as `Authorization: Bearer YOUR_KEY` in API requests. In Swagger, click **Authorize** and enter the key as a Bearer credential. Never use the example placeholders as real keys.

- `user` keys can create/read/update/delete only memories associated with their configured `user_id`.
- `admin` keys can administer memories and access asset/Copilot/template endpoints.
- Asset and template endpoints are deliberately admin-only because the schema still has no per-asset owner/tenant mapping. This is a safe interim gate, **not** multi-tenant asset-level authorization.
- `/`, `/health`, and API documentation are public. Do not expose the service directly to the internet without TLS, network controls, and key rotation.

## Shared mock data (Weeks 1–6)

`app/mock_data.py` is the single deterministic fixture source for assets, exposures, risk scores, users, roles, audit events, and integrations. It includes admin-only records and seeded denial events so permission tests have restricted data to exercise. The shape is provider-neutral (`schema_version`, named collections, stable IDs) for a future Pod Beta adapter.

- Set `AEV_DATA_SOURCE=mock` in the local `.env` to make Copilot inventory endpoints use the shared fixture module.
- Set `AEV_DATA_SOURCE=database` (default) to use PostgreSQL/pgvector.
- Mock asset search uses deterministic keyword overlap, **not** vector similarity. Mock timestamps are illustrative and must not be presented as operational SLA measurements.
- Mock mode is read-only for `PATCH /assets/{asset_id}`; use database mode for persisted updates.
- `GET /copilot/integrations` reports mock adapter metadata; it does not contact any external integration.
- Test the shared fixture and low-privilege denial with `app/tests/test_mock_data.py` against a dedicated test database, as app import currently initializes SQLAlchemy metadata.

## Endpoint guide

### Memory
- `POST /memory` — create memory and embedding. Body: `user_id`, `conversation`, `memory_type`.
- `GET /memory` — list all memory rows (administrative; do not expose publicly without authorization).
- `GET /memory/user/{user_id}` — list one user's memories.
- `PUT /memory/{memory_id}` — update memory; body must include `user_id`.
- `DELETE /memory/{memory_id}` — delete memory; JSON body must include `user_id`.

**Important:** user IDs in request bodies/paths are not authentication. The current API-key layer binds each non-admin key to a configured `user_id`; never allow clients to choose their own key-to-user mapping.

### Assets and Copilot
- `POST /copilot/asset-search` — vector search; accepts `query` and optional `limit` (1–10). Results include similarity score and `why_this_matched`.
- `GET /copilot/asset-summary/{asset_id}` — summary of stored fields plus fact-check and embedding status.
- `GET /copilot/exposure-explain/{asset_id}` — explains available recorded risk/description; does not run a vulnerability scan.
- `GET /copilot/remediation-plan/{asset_id}` — generic, rules-based remediation suggestions.
- `GET /copilot/executive-summary` — inventory metrics based on stored asset rows.
- `GET /copilot/recommendations` — rules-based recommendations from stored risk scores.
- `PATCH /assets/{asset_id}` — update allowed fields and synchronously regenerate embedding.
- `GET /copilot/permission-audit` — returns the current permission/RAG audit findings; in mock mode includes restricted-record counts and seeded denial events.
- `GET /copilot/integrations` — lists configured mock integration metadata (mock mode only; database mode returns an empty registry).
- `GET /copilot/freshness-metrics` — snapshot counts and max measurable embedding lag.

### Templates
- `POST /templates` — create version 1.
- `PUT /templates/{template_name}` — create a new version and deactivate the prior active version.
- `GET /templates/{template_name}/versions` — list version history.
- `POST /templates/{template_name}/rollback/{version}` — make an existing version active.
- `GET /templates/{template_name}/route?request_id=...` — deterministic routing across active template versions. Updating a template leaves prior versions active for A/B routing; rollback deactivates all versions except the selected version.

## Fact-checking policy and optional external webhook
Copilot endpoints use database-grounded facts and list missing fields. If `FACT_CHECK_WEBHOOK_URL` is configured, the service POSTs a JSON object containing `facts` and `source` to that URL. An optional `FACT_CHECK_WEBHOOK_TOKEN` is sent as a Bearer token, and `FACT_CHECK_WEBHOOK_TIMEOUT_SECONDS` defaults to 3. The endpoint should return JSON; its response is exposed under `external_check.result`. A missing URL, invalid response, or timeout is explicitly reported and never treated as verification. No vulnerability scanner or threat-intelligence feed is queried by these endpoints. This optional integration is separate from the shared mock-data source.

## Freshness SLA and measurement
`PATCH /assets/{id}` regenerates the asset embedding synchronously before returning. Persisted `updated_at` and `embedding_updated_at` timestamps support per-record lag, and `GET /copilot/freshness-metrics` provides a current snapshot. Apply the migration and refresh legacy embeddings first. This snapshot is not a historical SLA report; retries, background queueing, alerting, and load testing are not included. Do not claim 60-second SLA compliance until verified under representative load.

## Permission-aware RAG audit (current result)
**Partially enforced.** Bearer API keys authenticate protected requests; memory access is scoped to the configured key principal, while asset/Copilot/template routes are admin-only. There is still no per-asset owner/tenant policy, so multi-tenant asset-level RAG authorization is not implemented. See `app/PRIVACY.md` and `/copilot/permission-audit`.

## Expiry
Run a safe preview:
`python -m app.expiry_job`
The default is dry-run and does not delete records. Only run live deletion against an isolated test database until retention policy and backups are approved.

## Tests
Install dependencies from the UTF-8 `requirements.txt` first. Inside the running container:
`docker compose exec ai-context sh -c "PYTHONPATH=/app python -m pytest /app/app/tests -v"`
The existing isolation test uses the configured database; run it only with a dedicated test database. A 70% coverage target is not certified by this repository yet.

See `HANDOVER_STATUS.md` for the remaining handover blockers and verification status.

## Privacy and deployment
- Never commit `.env`, credentials, access tokens, or production dumps.
- Configure strong `AEV_API_KEYS_JSON` secrets and restrict `/memory`, `/copilot/asset-search`, and asset detail endpoints behind authorization before deployment.
- Configure TLS, request logging without sensitive memory content, backups, retention monitoring, and least-privilege DB credentials.

## Handover verification status
Static Python compilation passes in the packaging environment. The full pytest suite was not run here because the environment does not have `pgvector` installed and no dedicated PostgreSQL test database/credentials were provided. Before handover, install dependencies and run the documented tests against an isolated test database. Do not run data-mutating tests against production.
