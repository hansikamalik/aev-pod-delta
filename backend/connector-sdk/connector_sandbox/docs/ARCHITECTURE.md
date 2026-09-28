# Architecture

> Describes sandbox v0.3.0 and the **vendored Week-1 SDK** (`python/connector_sdk`, `ts/src`).
> The repo's `connector-sdk-v0.1.0` differs; see [KNOWN_GAPS.md](KNOWN_GAPS.md).

## 1. High-level flow

```text
Connector implementation
        |
        v
Connector SDK contract
        |
        +--> discover() ----> source API
        |                       |
        |                       v
        |                  raw resources
        |                       |
        |                       v
        |                  Asset objects
        |
        +--> ingest() <---- normalized assets
        |
        v
     SyncResult
```

In the sandbox the "source API" is a local mock server. The connector talks to it over real HTTP, so
the code path is the same as against a real vendor. Only the URL changes.

## 2. Python components

| Component | Path | Purpose |
|---|---|---|
| `connector_sdk` | `python/connector_sdk/` | The contract: `Connector` (abstract), `Asset`, `AssetType`, `SyncResult`, `SyncStatus`, and `SampleConnector` |
| Reference connector | `python/connectors/reference/` | Example HTTP connector: calls an API, turns vendor payloads into `Asset`, health-checks, describes its config and credentials |
| Mock server | `python/mock_server/server.py` | FastAPI app: `GET /health` and `GET /api/assets?scenario=<name>` |
| Scenarios | `python/scenarios/` | `scenarios.yaml` plus `load_scenarios()`; see [SCENARIOS.md](SCENARIOS.md) |
| Runner | `python/sandbox/runner.py` | Command-line entry point: `python -m sandbox.runner` |
| Tests | `python/tests/`, `python/conftest.py` | See [TESTING.md](TESTING.md) |

**Models.** `Asset` has `id`, `source`, `type`, `name`, `raw`, `discovered_at` (defaults to now) and
`tags`. `SyncResult` has `connector`, `status`, `assets_discovered`, `assets_pushed`, `errors`,
`started_at` and `finished_at`, plus a `duration_seconds` property.

**Reference connector constructor:** `ReferenceConnector(base_url, api_key, timeout=5.0, extra_params=None)`.

## 3. TypeScript components

| Component | Path | Purpose |
|---|---|---|
| SDK | `ts/src/connector.ts`, `models.ts`, `sampleConnector.ts`, `index.ts` | Same contract as Python. Models are zod schemas, so `Asset.parse(...)` validates |
| Contract suite | `ts/src/testing/contractHarness.ts` | `runContractSuite(factory)` runs 7 generic checks against any connector |
| Mock server | `ts/src/testing/mockServer.ts` | `MockApiServer`: in-process `node:http` server on a free port. Serves fixed JSON per route |
| Mock data | `ts/src/testing/mockData.ts` | `MOCK_ASSETS`, `MOCK_CREDENTIALS` and related fixtures |
| Template | `ts/tests/sandboxTestHarness.template.test.ts` | Copy-me test for a new connector (excluded from runs) |

The TypeScript mock server is much simpler than the Python one; see [KNOWN_GAPS.md](KNOWN_GAPS.md).

## 4. How the two halves relate

They are independent toolchains in one folder. They do not exchange data at runtime. What ties them
together is the **contract**: the same six methods and the same model fields. Keeping them aligned is
currently a manual job (there is no shared golden test yet), which is why field-naming drift is the
top risk in [KNOWN_GAPS.md](KNOWN_GAPS.md).

## 5. The six contract methods

| Method (Python / TS) | Responsibility |
|---|---|
| `discover()` | Read from the source and return normalized `Asset` objects. No writes |
| `ingest(assets)` | Push assets to the platform; return how many were pushed |
| `sync()` / `sync()` | Default: discover, then ingest, then report. Override only for batching or retries |
| `check_health()` / `checkHealth()` | Cheap "can I reach the source with these credentials?" |
| `describe_config()` / `describeConfig()` | JSON-Schema-like description of non-secret settings |
| `describe_credentials()` / `describeCredentials()` | Same for secrets, marked `secret: True` |

## 6. Default `sync()` lifecycle

1. Record `started_at`.
2. Call `discover()`; materialize the result into a list.
3. If there is at least one asset, call `ingest()`.
4. Catch any exception from either step and record it as `"discover() failed: ..."` or
   `"ingest() failed: ..."`. `sync()` itself does not raise.
5. Pick a status:
   - no errors: `SUCCESS`
   - errors and nothing pushed: `FAILED`
   - errors and something pushed: `PARTIAL`
6. Return `SyncResult`.

> **`PARTIAL` cannot occur in the default `sync()`.** An error is recorded only when `discover()` or
> `ingest()` raises, and in both cases `assets_pushed` is 0. A connector must override `sync()`
> (for example to ingest page by page) to produce `PARTIAL`.

Direct calls versus `sync()` is a deliberate distinction in the tests: calling `discover()` directly
exposes the raw exception, while `sync()` converts it into `SyncResult.errors`.

## 7. Reference connector request flow

```text
ReferenceConnector.sync()
        |
        v
ReferenceConnector.discover()
        |
        |  GET /api/assets
        |  Authorization: Bearer <api_key>        (sent, but NOT validated by the server)
        |  ?scenario=<name>                       (only if extra_params is set; see below)
        v
FastAPI mock server  --->  success | empty | malformed | HTTP error | delayed response
        |
        v
JSON response --> Asset normalization --> Connector.sync() --> ingest() --> SyncResult
```

Two things here are easy to miss:

- **`?scenario=` is a test hook, not normal behaviour.** `ReferenceConnector` sends it only when you
  pass `extra_params={"scenario": "..."}`. Without it, every request gets the `success` scenario. A
  new connector needs an equivalent way to forward query parameters or you cannot drive failures.
- **The server does not check the bearer token.** `unauthorized` (401) is selected by the scenario
  name, not by a bad credential.

## 8. Test-server lifecycle (Python)

The `live_server` fixture finds a free port, starts Uvicorn in a background thread, polls `/health`
until it answers, yields the base URL, then requests shutdown and joins the thread. This gives the
connector a real HTTP boundary without fixed ports or fixed sleeps. It starts a fresh server per test.
