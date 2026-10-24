# Active Directory Connector

Integration Hub connector that syncs users and groups from an on-prem
**Active Directory** domain controller via LDAP, normalizes them to
the platform's shared Asset shape, and pushes them into the Asset
service.

## What it does

- **Authentication** — LDAP simple bind against a domain controller using a
  service account.
- **Discovery** — paged LDAP search over user and group objects, normalized
  to `Asset` (`ad_user` / `ad_group`).
- **Sync** — runs discovery and pushes results to the platform's asset
  ingestion API, returning a `SyncResult`.
- **Health check** — verifies the LDAP bind succeeds.

Active Directory has no separate alert/finding stream (unlike, say,
Microsoft Defender), so `ingest()` is a documented no-op — user/group
data is fully covered by `discover()`.

## Architecture

```
config.py           connector configuration (non-secret)
credentials.py       Vault-backed credential resolution (bind password)
auth.py               LDAP simple bind (Active Directory)
discovery.py          paged LDAP search over users and groups
normalization.py      raw LDAP entries -> Asset
push.py               POST normalized assets to Beta's ingestion API
schemas.py            config_schema() / credential_schema()
sdk_interface.py      vendored copy of the platform Connector ABC
connector.py          ActiveDirectoryConnector — implements Connector
```

## Dependencies

| Dependency | Why | Failure mode |
|---|---|---|
| **Vault access** (Pod Alpha) | The service account's bind password is never stored in connector config — it is resolved at runtime from the Vault path in `integrations.credentials_ref` | **Fails closed.** No local fallback; `discover()`, `sync()`, and `health_check()` all raise/report `VaultAccessError` if Vault is unreachable |
| Domain controller reachability (LDAP/LDAPS) | The bind and all searches | Raises `LDAPBindError` (bind) or `LDAPSearchError` (search); a bind rejection also invalidates the cached credential so the next attempt re-reads Vault |
| Beta asset ingestion endpoint | `sync()` pushes normalized records here | Push failures are counted in `SyncResult.records_failed` rather than aborting the whole sync |

## Configuration

Two separate inputs, matching the platform's separation of config vs. secrets:

1. **`config`** (non-secret, stored on the `integrations` table) — see
   `config.example.yaml`. Validated against `config_schema()`.
2. **Credentials** (Vault, referenced by `credentials_ref`) — see
   `credential_schema()`. Only `bind_password` is required; the bind
   identity itself (`bind_dn`) is non-secret config.

The service account needs read access to the user and group subtrees
configured via `user_search_base` / `group_search_base` (defaults to
`base_dn` if unset). LDAPS (port 636) is the default and recommended
transport.

## Usage

```python
from active_directory_connector import ActiveDirectoryConnector

connector = ActiveDirectoryConnector(
    integration_id="int-456",
    credentials_ref="secret/data/integrations/active-directory/int-456",
    vault_client=vault_client,  # platform-provided Vault client
    asset_ingest_url="https://beta.internal/api/v1/assets/ingest",
)

result = await connector.sync(config, direction="pull")
await connector.aclose()
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in ldap_server / bind_dn / Vault path
```

## Testing

```bash
pytest                                    # unit + integration
pytest --cov=active_directory_connector --cov-report=term-missing
ruff check .
mypy src
```

Bind and health-check tests use ldap3's in-memory `MOCK_SYNC` strategy
(no real domain controller required). Discovery tests fake the
`connection.extend.standard.paged_search` call directly rather than
relying on `MOCK_SYNC` for that extended operation, since ldap3's mock
strategy documents support for bind/search/add/modify/compare/delete
but not paged search specifically. No real AD environment or Vault
instance is required to run the suite.

## Notes on standardization

This connector follows the same shape as every other Integration Hub
connector: `discover()` / `ingest()` / `sync()` / `health_check()` /
`config_schema()` / `credential_schema()`, per the platform's Connector
SDK contract (vendored in `sdk_interface.py`). Swapping the vendored
copy for the shared `connector-sdk` package (once published) should
require no changes to `connector.py`.
