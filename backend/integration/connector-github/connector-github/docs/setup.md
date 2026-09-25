# GitHub Connector — Setup & Config

**Owner:** Bhavesh Kanekar · Integration Squad
**Milestone:** Pod Delta M4, Week 2 (Sep 11–17)

## What this connector does

Pulls an organization's **repositories** (as Assets) and their open **security
alerts** — Dependabot, code scanning, secret scanning — (as Findings) via the
GitHub REST API, normalizes them to the shared Asset/Finding shape, and pushes
Assets to Beta's asset/exposure service.

## Prerequisites

1. A GitHub organization name (e.g. `acme`).
2. A token that can read the org. Recommended: a **fine-grained PAT or GitHub App
   installation token** with read-only repository permissions: *Metadata*,
   *Dependabot alerts*, *Code scanning alerts*, *Secret scanning alerts*.
   (Classic PAT equivalent: `repo`, `security_events`, `read:org`.)
3. Credentials stored in Vault at:
   ```
   secret/connectors/github/{org_id}
   ```
   ```json
   { "token": "...", "org": "acme", "api_url": "https://api.github.com" }
   ```
   `api_url` is optional (defaults to github.com). For GitHub Enterprise Server use
   e.g. `https://ghe.example.com/api/v3`.
4. A Beta platform API token with write access to the bulk asset endpoint.

## Wiring into the real environment (before staging)

| File | Stub | Replace with |
|---|---|---|
| `base.py` | Local `Connector`/`Asset`/`Finding`/`SyncResult` | `from connector_sdk.base import ...` |
| `credentials.py` | `MockVaultClient` | Real internal Vault client |
| `push.py` | Placeholder `BETA_ASSET_ENDPOINT` | Real service discovery / client for Beta's asset service |

Same three swaps as the other connectors — do them once, consistently.

## Usage

```python
from github_connector import GitHubConnector

c = GitHubConnector(vault=vault, org_id="org-123", beta_api_token="<token>")
result = c.run_full_sync()
print(result)       # SyncResult(assets_count=..., findings_count=...)
c.findings          # normalized Finding objects from the last sync
c.warnings          # non-fatal issues, e.g. ["code_scanning alerts skipped (HTTP 404)"]
```

## Pipeline stages

1. **authenticate()** — `GET /orgs/{org}` with the bearer token.
2. **discover()** — page all org repos (`Link` header pagination, 100/page).
3. **ingest()** — fetch open Dependabot / code-scanning / secret-scanning alerts
   for the org and attach each to its repo. Alerts for unknown repos are kept on
   an orphan record, never dropped.
4. **normalize()** — repos → `Asset` (`asset_type="repository"`); alerts → `Finding`.
5. **push()** — bulk-send Assets in batches of 200.
6. **health_check()** — auth-only check for monitoring.

## Behavior worth knowing

- **Secret values are never stored.** Secret-scanning alerts contain the leaked
  secret in a `secret` field; it is stripped at ingestion (tested).
- **Rate limits:** 429, or 403 with `X-RateLimit-Remaining: 0`, are retried up to
  3 times, waiting `Retry-After`/reset time capped at 60s.
- **Alert types that are disabled or not permitted** (HTTP 403/404/410/451) are
  skipped and recorded in `connector.warnings` instead of failing the sync. A 5xx
  still fails it.
- Finding IDs are `"{type}:{owner/repo}#{number}"` because alert numbers are only
  unique within a repo.

## Mapping notes (confirm with platform team)

- GitHub has a `critical` severity; it is kept as `critical`, whereas the other
  connectors' vocabulary is high/medium/low/info. Confirm whether to collapse it to `high`.
- Secret-scanning alerts have no severity field; mapped to `high`.
- Code scanning uses `security_severity_level`, falling back to `rule.severity`
  (`error→high`, `warning→medium`, `note→low`).

## Known follow-ups (not in Week 2 scope)

- Finding push path: only Assets are pushed today (same as Sentinel/SentinelOne).
- Incremental sync (`since`/`updated` filters) — currently full refresh.
- Optional per-repo scoping (allow/deny lists) for very large orgs.
- Swap live-API mocks for Connector SDK's Python sandbox v2 (Ben Johnson, Week 2).
