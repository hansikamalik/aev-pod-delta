# Weeks 1â€“6 audit â€” AEV AI Context Service

This audit separates code presence from runtime verification. It does not certify production readiness.

| Week / area | Source review | Verification status | Notes / handover action |
|---|---|---|---|
| 1 â€” Service foundation | Present | Python syntax passed; live Docker/database not re-tested from this package | FastAPI, Docker, PostgreSQL/pgvector configuration exist. Keep `.env` private. |
| 2 â€” Memory CRUD and isolation | Present | Existing DB-backed tests not run here | API-key principal binding is present. Isolation test was updated to use distinct authenticated principals. Run only against a dedicated test database. |
| 3 â€” Asset vector search and templates | Present | Full endpoint integration not run here | Vector search and template version/history/route/rollback endpoints exist. Database migration state must be confirmed. |
| 4 â€” Copilot fact-checking and responses | Present | Unit/integration tests not fully run | Copilot outputs are grounded in stored fields and rules; no scanner or external threat feed is queried. Optional external webhook is not required for mock-data acceptance. |
| 5 â€” Freshness, permission audit, expiry | Present with limitations | Static checks only; database behavior pending | Migration must be applied; refresh script now writes `embedding_updated_at`. Expiry defaults to dry-run. Admin-only asset access is interim protection, not per-asset tenant authorization. 60-second SLA is not load-certified. |
| 6 â€” Shared mock data | Added in this revision | Pure fixture tests: 2 passed. E2E/database tests not run in this packaging environment | `app/mock_data.py` contains assets, exposures, risk scores, users/roles, audit events, and integrations, including restricted records and denied events. Copilot endpoints select mock/database with `AEV_DATA_SOURCE`. Mock search is keyword-based, not vector similarity. |

## Commands before handover

1. Copy `.env.example` to `.env`, use a dedicated test database, generate fresh API keys locally, and never include `.env` in the handover archive.
2. Apply `migrations/001_asset_embedding_freshness.sql` to the intended database after backup.
3. Refresh legacy embeddings with `python -m app.generate_asset_embeddings` after dependencies and DB are ready.
4. Run `python -m pytest app/tests -v` against the dedicated test database.
5. Run `python -m app.expiry_job` and verify it reports dry-run only.
6. Start Docker, check `/health`, then smoke-test the routes in `/docs` using admin and low-privilege keys.
7. Rotate any API/database credentials that were exposed during development and deliver new credentials through a secure channel, not inside this ZIP.

## Current verdict

**Development handover candidate; not yet certified end-to-end.** Static compilation passed and the pure shared-mock-data tests passed. Full pytest, live database migration, Docker smoke tests, and the mock-data E2E authorization test still need to pass in the project environment before stating that all weeks are complete.

## Week 5 — Freshness SLA Evidence

- Freshness metrics endpoint: HTTP 200.
- Permission audit endpoint: HTTP 200.
- Expiry job: detected 1 expired memory in dry-run mode; no deletion performed.
- Controlled embedding batch: 5 assets processed and verified.
- Measured batch duration: 28.613 seconds.
- Target: 60 seconds; controlled batch completed within target.
- Asset updated_at timestamps remained unchanged.
- Historical timestamp check: 5/5 assets exceeded the 60-second timestamp-lag threshold.
- Scope: local controlled batch measurement; repeated production SLA compliance has not been established.
- Security limitation: asset authorization remains admin-only; fine-grained tenant authorization and cross-tenant tests remain future requirements.
