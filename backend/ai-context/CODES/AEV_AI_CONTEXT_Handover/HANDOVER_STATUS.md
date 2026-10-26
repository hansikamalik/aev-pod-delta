# Handover Status — AEV AI Context Service

## Implemented in this package
- Shared provider-neutral mock dataset in `app/mock_data.py` with assets, exposures, risk scores, users/roles, audit events, and integrations.
- Seeded admin-only asset/exposure records plus denied audit events so permission tests exercise real restricted fixtures.
- Copilot inventory endpoints switch between the shared mock provider and PostgreSQL using `AEV_DATA_SOURCE=mock|database` (database is the default); mock keyword search is clearly labeled and does not claim vector similarity.
- Mock-mode integration registry endpoint and tests for fixture shape plus low-privilege denial.
- Bearer API-key authentication with fail-closed behavior if configuration is missing/invalid.
- User API keys are bound to a configured user_id for memory CRUD; admin-only gate for asset/Copilot/template routes.
- Six Copilot endpoints are present: asset search, asset summary, exposure explanation, remediation plan, executive summary, recommendations.
- Asset search returns `why_this_matched`.
- Copilot responses label their scope and flag missing/unverified asset fields; they do not claim to have queried vulnerability scanners or external threat feeds.
- Optional external fact-check webhook support is implemented through environment variables; it is not required for the local shared-mock-data workflow and remains unverified unless a concrete service contract is supplied.
- `GET /copilot/freshness-metrics` reports a snapshot of persisted freshness status and measured lag.
- Asset updates synchronously regenerate embeddings.
- Freshness fields are persisted (`updated_at`, `embedding_updated_at`) and lag is calculated when timestamps are available.
- Template routing deterministically splits requests across active versions; rollback reverts to one active version.
- Expiry job defaults to dry-run.
- Requirements file is UTF-8 and model loading is lazy.
- README and privacy audit describe current limitations.

## Required before handover/deployment
0. **Run the new mock-data E2E tests and full suite** against a dedicated test database. These tests are added but not executed in this packaging environment; report them as pending until they pass locally.
1. **Apply database migration first:** back up the database, then run `migrations/001_asset_embedding_freshness.sql` against the target PostgreSQL database. `Base.metadata.create_all()` does not add columns to existing tables.
2. **Refresh existing asset embeddings:** run `python -m app.generate_asset_embeddings` in the intended environment after migration. This updates vector timestamps; do this only when model dependencies and DB access are ready.
3. **Run tests against a dedicated test database:** do not run the isolation test against production because it creates a memory row. The current execution environment did not have `pgvector` installed and did not have the project database configured, so the full pytest suite and integration behavior are **not verified here**.
4. **Security — interim API-key authentication added:** protected endpoints require a bearer API key configured in `AEV_API_KEYS_JSON`. Memory CRUD is scoped to the key principal, and asset/Copilot/template routes are admin-only. Generate real keys and configure `.env` before testing. Per-asset/per-tenant authorization is still absent; do not treat admin-only access as multi-tenant RAG security.
5. **Optional external fact-check webhook:** not part of the shared mock-data acceptance check. Unless a concrete endpoint/schema is provided, treat external verification as not configured; local fact-checking reports stored-field completeness only.
6. **Operational freshness monitoring:** the metrics endpoint is included, but no background queue, retries, alerting, historical SLA report, or load test is included. Verify the 60-second objective under load before claiming the SLA is met.
7. **Coverage target:** 70% coverage has not been measured or certified. Add/execute database-backed endpoint tests, template A/B/rollback tests, expiry dry-run/live tests against isolated DBs, and cross-tenant authorization tests.

## Safe run checklist
- Copy `.env.example` to `.env`, set a dedicated database URL, and replace the API-key placeholders with generated random keys; never include `.env` in handover ZIP.
- Ensure PostgreSQL `vector` extension is available.
- Back up database and apply migration before starting the updated app.
- `docker compose up --build -d`
- `docker compose exec ai-context sh -c "PYTHONPATH=/app python -m pytest /app/app/tests -v"` using a dedicated test DB.
- `docker compose exec ai-context python -m app.expiry_job` for dry-run only.
- Open `http://localhost:8002/docs` and smoke-test the endpoints with non-production test records.

## Handover statement
This is a development handover candidate, **not yet certified production-ready**. The security/authorization blocker and external webhook integration need project-owner decisions and verification.
