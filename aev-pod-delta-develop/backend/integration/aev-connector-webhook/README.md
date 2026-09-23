# AEV Platform — Custom Webhook Connector

Connector 21 of 21 in the AEV catalog, and the only bidirectional one. It
accepts signed events from external systems and delivers signed events to
customer-supplied URLs with per-event subscriptions, retry, and a permanent
delivery log.

**Squad:** Integration (Pod Delta, M4)
**Owner:** Harshal Sahare
**Week 3 deliverable:** Webhook (custom) connector — URL/auth/signing,
per-event subscription, retry, delivery log — plus the connector-interface
stability doc.

---

## What's here

```
src/aev_connectors/webhook/
  config.py          WebhookConfig + RetryPolicy (Vault-resolved credentials)
  models.py          Asset, Finding, SyncResult, Subscription, Event, DeliveryRecord
  signing.py         HMAC-SHA256 signing, timestamp binding, replay window, rotation
  auth.py            Outbound auth headers; inbound auth + signature verification
  subscriptions.py   Per-event subscription registry (exact / wildcard matching)
  retry.py           Exponential backoff with full jitter; retryability rules
  delivery_log.py    Every attempt logged; retry queue; 1-year retention purge
  client.py          Async delivery client — sign, send, retry, log
  normalizer.py      Arbitrary vendor payloads → shared Asset/Finding shapes
  connector.py       WebhookConnector — the six-method Connector interface
  routes.py          FastAPI routes mounted at /connectors/webhook
examples/            Runnable local app + signed-event sender
docs/                Setup guide + connector interface stability doc
tests/               86 tests
```

## Quick start (Windows / PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -e .

Copy-Item .env.example .env

ruff check src tests examples
pytest -q
```

Run it locally:

```powershell
uvicorn examples.app:app --reload --port 8000
# in a second terminal:
python examples\send_test_event.py
```

## Quick start (bash)

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt && pip install -e .
cp .env.example .env
ruff check src tests examples && pytest -q
```

## Interface

`WebhookConnector` implements the six frozen methods — `authenticate`,
`health_check`, `discover`, `ingest`, `normalize`, `push` — identically to
every other connector in the catalog. It adds `accept_inbound`, `subscribe`,
`unsubscribe`, `emit`, and `redeliver` on top; nothing in the sync engine
depends on those. See
[`docs/CONNECTOR_INTERFACE_STABILITY.md`](docs/CONNECTOR_INTERFACE_STABILITY.md).

## Security notes

- Every outbound delivery is signed regardless of `auth_mode`, so a receiver can
  verify integrity independently of transport auth.
- Signatures bind the timestamp into the signed string and are checked against a
  300-second tolerance window, so captured signatures cannot be replayed.
- Comparisons use `hmac.compare_digest` throughout — no short-circuit on the
  first differing byte.
- Secrets come from Vault. `.env` is for local development and is gitignored.
- 4xx responses are not retried: a customer's broken auth config is not fixed by
  hammering their endpoint.

## Testing

86 tests, no network egress. `httpx.MockTransport` stands in for subscriber
endpoints; `sleep` is injected so backoff is exercised without real delays.

Coverage: signature round-trip, tamper, stale and future timestamps, malformed
headers, secret rotation, case-insensitive header lookup, all four auth modes,
subscription CRUD and wildcard matching, org scoping, backoff bounds and jitter,
retryable vs permanent statuses, transport errors, dead-lettering, retention
purge, payload alias resolution, severity mapping, full inbound-to-push
round-trip, and every route.

## Docs

- [Setup & configuration](docs/webhook-connector-setup.md)
- [Connector interface stability](docs/CONNECTOR_INTERFACE_STABILITY.md)
- [Week 3 status](docs/week3-status.md)
