# Okta Connector

**Owner:** Bhavesh Kanekar — Week 3, Integration Squad
**Status:** Foundation-complete milestone deliverable

Syncs users and groups from an Okta org into the AEV Platform's asset
inventory. Implements the shared `Connector` interface frozen in Week 1
with the Connector SDK squad.

## What it does

- Authenticates to Okta with a token-based (SSWS) API token
- Discovers all users and all groups (with group membership) via the Okta
  Users and Groups APIs, following pagination
- Normalizes users and groups into the platform's shared `Asset` shape
- Reports a `SyncResult` (counts + errors) after each run
- Exposes a `health_check()` so the cron scheduler can skip unhealthy runs

## Setup

### 1. Create the Okta API token

In the Okta admin console: **Security → API → Tokens → Create Token**.
Use a service account with a **read-only admin** role — this connector
never writes to Okta, only reads.

### 2. Configure credentials

In production, credentials are pulled from the shared secrets vault:

```python
from okta_connector.credentials import OktaCredentials

creds = OktaCredentials.load_from_vault(vault_client, secret_path="connectors/okta")
```

For local development, set environment variables instead:

```bash
export OKTA_ORG_URL="https://your-org.okta.com"
export OKTA_API_TOKEN="00xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

```python
from okta_connector.credentials import OktaCredentials

creds = OktaCredentials.load_from_env()
```

Credential schema (also returned by `describe_credentials()`):

| Field       | Type   | Required | Notes                              |
|-------------|--------|----------|-------------------------------------|
| `org_url`   | string | yes      | Must be `https://`                  |
| `api_token` | string | yes      | SSWS token, read-only admin scope   |

### 3. Run a sync

```python
from okta_connector import OktaConnector, OktaCredentials

creds = OktaCredentials.load_from_env()
connector = OktaConnector(creds)

result = connector.sync()
print(result.assets_discovered, result.assets_pushed, result.errors)
```

By default, `sync()` uses a no-op push. Wire the real asset-service client
in by passing `push_fn`:

```python
connector = OktaConnector(creds, push_fn=asset_service_client.push_assets)
```

## Config options

Returned by `describe_config()`:

| Option                        | Type    | Default | Notes                                             |
|--------------------------------|---------|---------|----------------------------------------------------|
| `sync_interval_minutes`        | integer | `60`    | Used by the cron scheduler (Week 3 shared task)     |
| `include_deprovisioned_users`  | boolean | `false` | Reserved for a future filter; currently all users are ingested and tagged with their status |

## Data normalization

| Okta record | Asset `asset_type` | Asset `name`         | Key `attributes`                                      |
|-------------|--------------------|-----------------------|--------------------------------------------------------|
| User        | `user`             | "First Last"           | `login`, `email`, `department`, `title`, `okta_status`, `created`, `last_login` |
| Group       | `group`            | Okta group name        | `description`, `member_ids`, `member_count`, `type`     |

Okta user statuses are collapsed into the shared `AssetStatus` enum:
`ACTIVE`, `PROVISIONED`, `PASSWORD_EXPIRED`, `RECOVERY` → `active`;
`SUSPENDED`, `LOCKED_OUT`, `DEPROVISIONED`, `STAGED` → `inactive`.

## Testing

```bash
pip install pydantic requests pytest --break-system-packages
python -m pytest okta_connector/tests/ -v
```

15 tests covering: auth header construction, credential validation,
pagination handling, error handling on non-200 responses, health checks,
user/group normalization (including the deprovisioned-user edge case),
and an end-to-end `sync()` integration test (discover → normalize → push),
plus a failure-path test confirming a discovery error is recorded and
push is skipped.

## Notes for future connectors

This connector follows the same shape as the AWS/Azure/GCP connectors
from Week 2: `Connector` interface in, `Asset`/`SyncResult` out. The
`push_fn` injection pattern (rather than a hard dependency on the asset
service) is what made it possible to unit-test `sync()` without any real
network calls — worth keeping for the CrowdStrike/Splunk/Jira connectors
too.
