# SentinelOne Connector — Setup & Config

**Owner:** Bhavesh Kanekar · Integration Squad
**Milestone:** Pod Delta M4, Week 1 (Sep 4–10)

## What this connector does

Pulls SentinelOne **agents** (as Assets) and **threats** (as Findings) from the
Management Console REST API v2.1, normalizes them to the shared Asset/Finding
shape, and pushes Assets to Beta's asset/exposure service.

## Prerequisites

1. A SentinelOne Management Console URL, e.g. `https://usea1-acme.sentinelone.net`.
2. An **API token** for a service user with read access to Agents and Threats
   (Viewer role is sufficient). Generate it in the console under
   *Settings → Users → Service Users*.
3. Credentials stored in Vault at:
   ```
   secret/connectors/sentinelone/{org_id}
   ```
   ```json
   { "base_url": "https://usea1-acme.sentinelone.net", "api_token": "..." }
   ```
4. A Beta platform API token with write access to the bulk asset endpoint.

## Wiring into the real environment (before staging)

| File | Stub | Replace with |
|---|---|---|
| `base.py` | Local `Connector`/`Asset`/`Finding`/`SyncResult` | `from connector_sdk.base import ...` |
| `credentials.py` | `MockVaultClient` | Real internal Vault client |
| `push.py` | Placeholder `BETA_ASSET_ENDPOINT` | Real service discovery / client for Beta's asset service |

These are the same three swaps as the Microsoft Sentinel connector — do them
once, consistently.

## Usage

```python
from sentinelone_connector import SentinelOneConnector

connector = SentinelOneConnector(vault=vault, org_id="org-123", beta_api_token="<token>")
result = connector.run_full_sync()
print(result)            # SyncResult(assets_count=..., findings_count=...)
connector.findings       # normalized Finding objects from the last sync
```

## Pipeline stages

1. **authenticate()** — `GET /agents?limit=1` with `Authorization: ApiToken ...`.
2. **discover()** — page all agents (cursor pagination, 1000/page, 429 backoff).
3. **ingest()** — page all threats and attach to their agent; threats whose
   agent no longer exists are kept on an orphan record, never dropped.
4. **normalize()** — agents → `Asset`; threats → `Finding` (stored on `connector.findings`).
5. **push()** — bulk-send Assets in batches of 200.
6. **health_check()** — auth-only check for monitoring.

## Mapping notes (confirm with platform team)

- SentinelOne threats have no severity field. `confidenceLevel`
  `malicious → high`, `suspicious → medium`, anything else `low`.
- `machineType` `server`/`kubernetes node`/`storage` → `server`; everything
  else → `endpoint`.

## Known follow-ups (not in Week 1 scope)

- Finding push path: only Assets are pushed today (same as Sentinel). Add
  `push_findings()` once Beta confirms the findings endpoint.
- Incremental sync (`updatedAt__gte`) — currently full refresh.
- Swap live-API mocks for Connector SDK's Python sandbox v2 once it lands (Week 2).

## Ramp-up notes for Bhawook (Mon–Wed shadowing)

Suggested walk-through order: `credentials.py` → `auth.py` → `discovery.py` →
`normalization.py` → `push.py` → `tests/`. Then on Thu–Fri Bhawook builds the
**Google Workspace auth module** solo, copying the `auth.py` + `credentials.py`
pattern here (Google Workspace uses a service account / OAuth2 rather than an
API token, so `auth.py` will differ but the class shape stays the same).
