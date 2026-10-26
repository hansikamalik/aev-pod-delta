# Privacy and Permission Audit

## Current implementation status

Bearer API keys are configured through `AEV_API_KEYS_JSON`. Non-admin keys are bound to a configured `user_id`; memory create/read/update/delete routes check that principal against the requested user. The request body/path alone is not trusted. Admin keys can administer all memories.

Asset search and Copilot endpoints are admin-only as a fail-closed interim policy. This prevents a low-privilege API key from querying restricted assets, but the asset model does not contain owner/tenant policy fields and there is no per-asset filtering. `GET /copilot/permission-audit` reports this limitation. Do not describe the service as fine-grained permission-aware RAG until asset ownership/tenant policy, query-time filtering, and cross-tenant tests are implemented.

## Data use and factual claims

Copilot summaries and recommendations are based on stored database fields and simple rules. The service does not currently query external vulnerability databases, scanners, network telemetry, or threat-intelligence feeds. Missing fields are called out; generated text should not be treated as a verified security assessment.

## Retention

The expiry job uses `last_used_at` and a 90-day cutoff. Running `python -m app.expiry_job` defaults to dry-run and does not delete data. Test live deletion only with an isolated test database.

## Production checklist

- Use verified authentication; derive user identity from credentials, not request-supplied IDs.
- Add owner/tenant policy to assets and filter before vector ranking.
- Add negative tests for unauthorized reads, updates, deletes, and asset search.
- Avoid logging conversation text, tokens, secrets, or unnecessary personal data.
- Configure TLS, least-privilege database credentials, backup/restore tests, and monitored retention jobs.
