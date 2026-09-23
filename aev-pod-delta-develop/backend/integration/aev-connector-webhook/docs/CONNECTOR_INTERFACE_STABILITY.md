# Connector Interface Stability

**Owner:** Harshal Sahare (Integration Squad Lead)
**Status:** Ratified — Week 3 (Sep 18 – Sep 24), Pod Delta M4
**Applies to:** all 21 catalog connectors + the custom Webhook connector

With the catalog complete, the connector interface is now **frozen**. Weeks 4–6
are hardening weeks, and the sync engine, the Python SDK, and the TypeScript SDK
all assume a fixed contract. This document is what that contract is, what
counts as a breaking change, and how a change gets made.

---

## 1. The frozen interface

Every connector implements exactly these six methods. No more, no fewer.

| Method | Signature | Returns | Must |
| --- | --- | --- | --- |
| `authenticate` | `async () -> bool` | `True` on valid credentials | Be idempotent; never raise for bad credentials — return `False` |
| `health_check` | `async () -> dict` | Status envelope (§2) | Complete in under 5s; never mutate state |
| `discover` | `async () -> list[Asset]` | Assets visible to the credential | Be read-only and safely re-runnable |
| `ingest` | `async () -> SyncResult` | Run summary | Collect errors into `SyncResult.errors`, not raise |
| `normalize` | `(raw: dict) -> tuple[list[Asset], list[Finding]]` | Platform shapes | Stay synchronous and side-effect free |
| `push` | `async (assets, findings) -> SyncResult` | Run summary | Be idempotent on `external_id` |

The TypeScript `Connector` abstract class mirrors this method-for-method. Any
change to this table must land in both SDKs in the same release.

### Class attributes

```python
class MyConnector(Connector):
    name: str = "my_vendor"     # lowercase, snake_case, stable forever
    version: str = "1.0.0"      # semver, per-connector
```

`name` is a primary key in the registry. Renaming one is a data migration, not
a code change.

---

## 2. Shared shapes

These are versioned together with the interface.

**`Asset`** — `external_id`, `name`, `asset_type`, `source`, `ip_addresses`,
`hostnames`, `tags`, `first_seen`, `last_seen`, `raw`

**`Finding`** — `external_id`, `asset_external_id`, `title`, `severity`,
`description`, `source`, `detected_at`, `raw`

**`SyncResult`** — `connector_id`, `org_id`, `started_at`, `finished_at`,
`assets_discovered`, `assets_pushed`, `findings_pushed`, `errors`

**`health_check()` envelope** — must contain at least:

```json
{ "connector": "webhook", "version": "1.0.0", "healthy": true }
```

Connectors may add their own keys below those three. The dashboard reads only
the three.

`severity` is a closed set: `critical | high | medium | low | info`. A vendor
scale is mapped in `normalize`, never passed through raw.

---

## 3. What counts as a breaking change

**Breaking — requires an interface RFC (§4):**

- Adding, removing, or renaming one of the six methods
- Changing a method's parameters or return type
- Removing a field from `Asset`, `Finding`, or `SyncResult`, or narrowing its type
- Changing a field's meaning while keeping its name
- Adding a value to the `severity` enum
- Changing a connector's `name`
- Making a previously optional field required

**Non-breaking — normal PR, squad review only:**

- Adding an optional field with a default to a shared shape
- Adding keys to the `health_check` envelope beyond the required three
- Anything inside a connector's own module: auth mechanics, pagination,
  rate-limit handling, vendor field mapping, retries, logging
- Bumping a connector's own `version`
- Adding tests, docs, or sandbox fixtures

The test for "breaking": would an existing connector, unchanged, still pass CI
and still produce the same normalized output? If no, it's breaking.

---

## 4. How the interface changes

1. **RFC** — a markdown file in `docs/rfcs/`, naming the change, the connectors
   affected, and the migration path. Opened by anyone; tagged to the
   Integration lead.
2. **Review** — Integration lead + Connector SDK lead (Likith TV) both sign off.
   The SDK lead's sign-off exists because every interface change is a
   double implementation, Python and TypeScript.
3. **Implementation** — Python SDK, TypeScript SDK, and all affected connectors
   land in one PR series against `develop`, behind the same milestone.
4. **Verification** — full connector test matrix green in the sandbox, with
   zero real vendor API calls.

No interface change merges on a Friday, and none merges during a hardening
week without lead approval.

---

## 5. Guarantees connectors can rely on

- **Vault-resolved credentials.** A connector never reads a secret from the
  environment. It receives resolved credentials in its config object. Local
  `.env` files are a development convenience and are gitignored.
- **Org scoping.** Every call is scoped to one `org_id`. A connector never sees
  or writes another tenant's data.
- **Idempotent push.** The platform upserts on `external_id`, so a replayed
  sync is safe. Connectors do not need to deduplicate before pushing.
- **Errors are data.** `ingest`/`push` return errors inside `SyncResult`; the
  sync engine decides on retries. Connectors do not implement their own
  cross-run retry loops.
- **Sandbox first.** Every connector must be fully testable against the Python
  sandbox (and, from Week 3, the TypeScript sandbox) with no network egress.

---

## 6. The Webhook connector as a special case

The custom Webhook connector implements all six methods identically, but it is
the only **bidirectional** connector in the catalog. Two deviations are
explicitly sanctioned and are not precedents for other connectors:

- `discover()` drains an inbound buffer rather than enumerating a remote API,
  because the connector is push-based. It still returns `list[Asset]` and is
  still safely re-runnable.
- It exposes extra methods beyond the six — `accept_inbound`, `subscribe`,
  `unsubscribe`, `emit`, `redeliver`. These are additive, live outside the
  frozen interface, and nothing in the sync engine depends on them.

Outbound delivery semantics (signing, retry, delivery log) are documented in
`docs/webhook-connector-setup.md`.

---

## 7. Catalog status at freeze

All 21 catalog connectors plus the custom Webhook are built and staged:

Microsoft Defender · Microsoft Entra ID · Active Directory · SentinelOne ·
IBM QRadar · Elastic · Microsoft Sentinel · ServiceNow · GitHub · GitLab ·
CyberArk · HashiCorp Vault · Google Workspace · Microsoft 365 ·
Webhook (custom) — plus the connectors staged in earlier pods.

From here, the interface changes only through §4.
