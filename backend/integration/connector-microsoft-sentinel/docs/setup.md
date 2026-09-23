# Microsoft Sentinel Connector — Setup & Config

**Owner:** Harshal Sahare · Integration Squad Lead
**Milestone:** Pod Delta M4, Week 1 (Sep 4–10)

## What this connector does

Pulls Microsoft Sentinel incidents (as Findings) and the entities
attached to them — hosts, accounts, IPs — (as Assets), normalizes
them to the shared Asset/Finding shape, and pushes them to Beta's
asset/exposure service.

## Prerequisites

1. **Azure AD App Registration** with API permissions against the
   Sentinel workspace (`Microsoft.SecurityInsights` scope) — client ID
   + client secret + tenant ID.
2. **Log Analytics workspace name**, **resource group**, and
   **subscription ID** for the Sentinel instance being connected.
3. Credentials stored in Vault at:
   ```
   secret/connectors/microsoft-sentinel/{org_id}
   ```
   with the fields:
   ```json
   {
     "tenant_id": "...",
     "client_id": "...",
     "client_secret": "...",
     "subscription_id": "...",
     "resource_group": "...",
     "workspace_name": "..."
   }
   ```
4. A Beta platform API token with write access to the bulk asset
   ingestion endpoint.

## Wiring into the real environment (TODOs before this goes to staging)

This scaffold was built without access to the actual shared packages,
so three things need to be swapped from stub → real:

| File | Stub | Replace with |
|---|---|---|
| `base.py` | Local `Connector`/`Asset`/`Finding`/`SyncResult` definitions | `from connector_sdk.base import ...` (shared package) |
| `credentials.py` | `MockVaultClient` | Real internal Vault client (`platform_vault.VaultClient` or equivalent) |
| `push.py` | Hardcoded `BETA_ASSET_ENDPOINT` placeholder URL | Real service discovery / internal client for Beta's asset service |

Also confirm the ARM API version pinned in `discovery.py`
(`API_VERSION = "2023-11-01"`) against current org policy.

## Running locally

```bash
pip install -r requirements.txt
pytest tests/ -v
```

## Usage

```python
from sentinel_connector import SentinelConnector
from my_real_vault_client import VaultClient  # replace MockVaultClient

vault = VaultClient()
connector = SentinelConnector(vault=vault, org_id="org-123", beta_api_token="<token>")

result = connector.run_full_sync()
print(result)
```

## Pipeline stages

1. **authenticate()** — OAuth2 client-credentials against Azure AD.
2. **discover()** — paginate Sentinel incidents via ARM API.
3. **ingest()** — enrich each incident with its related entities.
4. **normalize()** — map entities → shared `Asset` shape.
5. **push()** — bulk-send assets to Beta's asset/exposure service.
6. **health_check()** — cheap auth-only reachability check for
   monitoring/alerting.

## Known follow-ups (not in Week 1 scope)

- Finding push path: this scaffold's `push()` only sends Assets.
  If Beta's service ingests Findings via a separate endpoint, add a
  `push_findings()` alongside `push()` — `normalize_incident()`
  already builds the `Finding` objects, they're just not wired to a
  push call yet.
- Rate-limit/backoff handling on the ARM API calls (Sentinel's
  management API does throttle under load).
- Incremental sync (only pulling incidents since last successful run)
  — currently full-refresh outside of `$top` paging.
