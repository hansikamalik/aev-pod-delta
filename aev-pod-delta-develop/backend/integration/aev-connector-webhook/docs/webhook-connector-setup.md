# Webhook Connector — Setup & Configuration

The custom Webhook connector is the one bidirectional connector in the catalog.
It does two jobs:

- **Inbound** — an external system POSTs signed events to the platform, which
  are normalized into `Asset` and `Finding` records.
- **Outbound** — the platform delivers signed events to customer-supplied URLs,
  with per-event subscriptions, retry, and a permanent delivery log.

---

## 1. Configuration

| Field | Required | Default | Notes |
| --- | --- | --- | --- |
| `org_id` | yes | — | Tenant scope for every operation |
| `connector_id` | yes | — | Registry ID for this instance |
| `target_url` | yes | — | Absolute `http(s)` URL; used by `health_check` |
| `signing_secret` | yes | — | Vault-resolved. Comma-separated during rotation |
| `auth_mode` | no | `hmac` | `hmac` \| `bearer` \| `basic` \| `none` |
| `auth_token` | if bearer | — | Bearer token |
| `basic_username` / `basic_password` | if basic | — | Basic credentials |
| `timeout_seconds` | no | `10.0` | Per-request HTTP timeout |
| `signature_tolerance_seconds` | no | `300` | Replay window for inbound signatures |
| `verify_tls` | no | `true` | Only disable in the sandbox |
| `retry` | no | see below | `RetryPolicy` |

`RetryPolicy` defaults: 6 attempts, 1s base delay, 2× multiplier, 300s cap,
full jitter on. Retryable HTTP statuses: `408, 425, 429, 500, 502, 503, 504`.

Every value is resolved from HashiCorp Vault at startup. `.env.example` exists
for local development only and `.env` is gitignored.

---

## 2. Signing

Both directions use the same scheme, so a customer can verify our deliveries
with the same code we use to verify theirs.

```
X-AEV-Signature: t=1726550400,v1=<hex hmac-sha256>
```

The HMAC is computed over `f"{timestamp}.{raw_body}"` using the signing secret.
Binding the timestamp into the signed string means a captured signature can't
be replayed against a different body, and the 5-minute tolerance window means it
can't be replayed later at all.

Additional headers on every outbound delivery:

| Header | Meaning |
| --- | --- |
| `X-AEV-Timestamp` | Unix seconds, matches `t=` |
| `X-AEV-Event-Id` | Stable across retries — use it for idempotency |
| `X-AEV-Event-Type` | e.g. `asset.created` |
| `X-AEV-Delivery-Id` | Delivery-log row ID |
| `X-AEV-Attempt` | 1-based attempt number |

**Verification order matters.** Compute the HMAC over the raw bytes *before*
JSON parsing — re-serializing changes key order and whitespace, and the
signature will not match.

Secret rotation: set `signing_secret` to `"new_secret,old_secret"`. Both verify;
deliveries are signed with the first. Drop the old value after one tolerance
window.

---

## 3. Event types

```
asset.created      asset.updated      asset.deleted
exposure.created   exposure.resolved
finding.created    scan.completed
```

Subscriptions accept exact names, a trailing wildcard (`asset.*`), or `*`.

---

## 4. Retry and the delivery log

A delivery moves through: `pending → delivered`, or
`pending → retrying → … → failed | dead_lettered`.

- **2xx** → `delivered`, stop.
- **Retryable status or transport error** → `retrying`, back off, try again.
- **Non-retryable status (4xx)** → `failed`, stop immediately. A customer's
  broken auth config is not fixed by hammering their endpoint.
- **Attempts exhausted** → `dead_lettered`, replayable by hand via
  `POST /connectors/webhook/deliveries/{id}/redeliver`.

Every attempt writes a row: attempt number, status code, duration, error.
Rows follow the same 1-year retention as `ai_interactions`; `purge_expired()`
is the cleanup job.

---

## 5. Endpoints

Mounted at `/connectors/webhook`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Reachability + delivery stats |
| `POST` | `/events` | **Inbound.** Signed event from an external system |
| `POST` | `/sync` | Drain buffered inbound events into the platform |
| `POST` | `/subscriptions` | Create a subscription |
| `GET` | `/subscriptions` | List subscriptions |
| `PATCH` | `/subscriptions/{id}` | Update event types / pause |
| `DELETE` | `/subscriptions/{id}` | Remove a subscription |
| `POST` | `/emit` | Fan an event out to matching subscriptions |
| `GET` | `/deliveries` | Delivery log, filterable by status |
| `POST` | `/deliveries/{id}/redeliver` | Manual replay |

Status codes: `401` bad signature or credentials, `400` unparseable body,
`422` unknown event type or unmappable payload, `202` inbound accepted.

---

## 6. Inbound payload shape

```json
{
  "event_type": "asset.created",
  "occurred_at": "2026-09-18T10:00:00Z",
  "assets": [
    { "id": "i-0abc", "hostname": "web-01", "type": "ec2", "ip": "10.0.0.4" }
  ],
  "findings": [
    { "id": "f-1", "asset_id": "i-0abc", "severity": "high", "title": "Open port 22" }
  ]
}
```

Field names are resolved through an alias table, so `id` / `asset_id` / `uuid`
and `hostname` / `name` / `display_name` all work. Severity is mapped onto the
platform's closed set — `P1` and `sev1` become `critical`, anything unrecognized
becomes `info`. A payload with no identifier, or a finding not linked to an
asset, is rejected with `422` rather than silently dropped.

---

## 7. Local run (Windows / PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -e .

Copy-Item .env.example .env

ruff check src tests
pytest -q
```

To run the service:

```powershell
uvicorn examples.app:app --reload --port 8000
```

Send a signed test event:

```powershell
python examples\send_test_event.py
```
