# GitLab Connector — Setup & Config

**Owner:** Bhavesh Kanekar · Integration Squad
**Milestone:** Pod Delta M4, Week 3 (Sep 18–24)

## What this connector does

Pulls a GitLab **group's projects** (including subgroups) as Assets and each
project's open **vulnerabilities** as Findings via the GitLab REST API v4,
normalizes them to the shared Asset/Finding shape, and pushes Assets to Beta's
asset/exposure service.

## Prerequisites

1. A GitLab group — numeric ID or full path (e.g. `acme` or `acme/platform`).
2. A **group access token** (or PAT of a service user) with the `read_api` scope
   and at least the **Reporter** role on the group. Reading vulnerabilities
   normally needs the **Developer** role or higher.
3. Vulnerability data requires **GitLab Ultimate**. On other tiers the connector
   still discovers projects; vulnerabilities are skipped with a warning.
4. Credentials stored in Vault at:
   ```
   secret/connectors/gitlab/{org_id}
   ```
   ```json
   { "token": "...", "group": "acme", "api_url": "https://gitlab.com/api/v4" }
   ```
   `api_url` is optional (defaults to gitlab.com). For self-managed use your host,
   e.g. `https://gitlab.example.com` — `/api/v4` is appended if missing.
5. A Beta platform API token with write access to the bulk asset endpoint.

## Wiring into the real environment (before staging)

| File | Stub | Replace with |
|---|---|---|
| `base.py` | Local `Connector`/`Asset`/`Finding`/`SyncResult` | `from connector_sdk.base import ...` |
| `credentials.py` | `MockVaultClient` | Real internal Vault client |
| `push.py` | Placeholder `BETA_ASSET_ENDPOINT` | Real service discovery / client for Beta's asset service |

Same three swaps as the other connectors — do them once, consistently.

## Usage

```python
from gitlab_connector import GitLabConnector

c = GitLabConnector(vault=vault, org_id="org-123", beta_api_token="<token>")
result = c.run_full_sync()
print(result)       # SyncResult(assets_count=..., findings_count=...)
c.findings          # normalized Finding objects from the last sync
c.warnings          # e.g. ["vulnerabilities skipped for 3 of 40 projects (HTTP 403); ..."]
```

## Pipeline stages

1. **authenticate()** — `GET /groups/{group}` with `PRIVATE-TOKEN`.
2. **discover()** — page all projects in the group and subgroups (`Link` header, 100/page).
3. **ingest()** — per project, fetch vulnerabilities and keep `detected`/`confirmed`
   ones (resolved/dismissed are dropped).
4. **normalize()** — projects → `Asset` (`asset_type="repository"`); vulnerabilities → `Finding`.
5. **push()** — bulk-send Assets in batches of 200.
6. **health_check()** — auth-only check for monitoring.

## Behavior worth knowing

- **Source-code extracts are never stored.** Vulnerability records can carry
  `raw_source_code_extract` (for secret detection this may be the secret itself);
  it is stripped recursively at ingestion (tested).
- **Rate limits:** HTTP 429 is retried up to 3 times, waiting `Retry-After` /
  `RateLimit-Reset` capped at 60s.
- **Unavailable vulnerability data** (HTTP 403/404 per project) is skipped and
  summarised in one entry in `connector.warnings`; a 5xx fails the sync.
- **Cost:** vulnerabilities are fetched per project (N+1 calls). Fine for tens to
  low hundreds of projects; see follow-ups for large groups.
- Finding IDs are `"vulnerability:{group/project}#{id}"`.

## Mapping notes (confirm with platform team)

- `critical` is preserved (same as the GitHub connector); other connectors use
  high/medium/low/info/unknown. `undefined` → `unknown`.
- Project `path_with_namespace` is used as the asset name; `asset_type` is
  `repository`, matching GitHub.

## Known follow-ups (not in Week 3 scope)

- **Verify the vulnerabilities endpoint and response fields on a real Ultimate
  instance** (built from the REST docs; not run against a live one). State
  filtering is done client-side; switch to a server-side `state` filter once the
  accepted format is confirmed.
- For very large groups, use the GraphQL group-level `vulnerabilities` query
  instead of per-project REST calls, and/or keyset pagination.
- Finding push path: only Assets are pushed today (same as the other connectors).
- Incremental sync (`updated_after`) — currently full refresh.
- Swap live-API mocks for Connector SDK's Python sandbox v2 (Ben Johnson, Week 2).
