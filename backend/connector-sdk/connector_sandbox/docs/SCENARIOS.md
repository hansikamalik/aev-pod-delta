# Scenario Catalog

Scenarios are deterministic source-system conditions the mock server can be switched into. They are
defined in `python/scenarios/scenarios.yaml` and selected per request with `?scenario=<name>`.

*Scenarios exist only in the Python mock server.* The TypeScript mock server has none yet
([KNOWN_GAPS.md](KNOWN_GAPS.md)).

## File format

```yaml
scenarios:                # required root key
  success:
    status_code: 200
  timeout:
    status_code: 200
    delay_seconds: 2      # optional: server sleeps this long before responding
```

`load_scenarios()` returns the mapping under `scenarios:`. Anything outside that key is ignored.

## Catalog

| Scenario | Status | Server behaviour | Main use |
|---|---:|---|---|
| `success` (default) | 200 | Two valid compute assets | Normal operation |
| `empty` | 200 | `{"assets": []}` | No resources available |
| `malformed` | 200 | Two broken assets | Payload validation and error handling |
| `unauthorized` | 401 | HTTP error | Authentication failure |
| `forbidden` | 403 | HTTP error | Authorization failure |
| `rate_limited` | 429 | HTTP error | Rate-limit handling |
| `server_error` | 500 | HTTP error | Vendor/server failure |
| `timeout` | 200 | Responds after 2 s | Client timeout handling |

An unknown scenario name returns **400**. `GET /health` ignores scenarios and always returns 200.

## Details

### success
Returns `asset-001` / `reference-server-01` and `asset-002` / `reference-server-02`. The reference
connector normalizes both as `AssetType.COMPUTE`.

### empty
Returns `{"assets": []}`. The connector treats this as a successful sync with 0 discovered and 0
pushed, and `ingest()` is not called.

### malformed
Returns two items: `{"id": "asset-broken"}` (no `name`) and `{"id": "asset-bad-type", "name": "weird one",
"type": "spaceship"}` (unsupported type).

The reference connector reads `item["name"]` directly, so it raises `KeyError` on the **first** item and
never reaches the second. The unsupported-type path (a `ValueError` from the `AssetType` enum) is
therefore **not exercised** by this scenario. Testing it needs a separate scenario, for example
`unknown_type`, that returns only the second kind of item.

Called directly, `discover()` raises. Through `sync()` the exception is captured in `SyncResult.errors`
and the status is `FAILED`.

### unauthorized, forbidden, rate_limited, server_error
The server returns the configured status. The reference connector calls `raise_for_status()`, so a
direct `discover()` raises `httpx.HTTPStatusError`, and `sync()` reports `FAILED`.

### timeout
The server delays `/api/assets` by `delay_seconds` (2 s). The test gives the connector a 0.3 s client
timeout, so a direct `discover()` raises `httpx.TimeoutException` and `sync()` reports `FAILED`.
`/health` is not delayed.

## What scenarios do not simulate

- **Credential checks.** `unauthorized` and `forbidden` are chosen by name. Sending a wrong or missing
  API key does not produce a 401.
- **`Retry-After` and rate-limit headers.** `rate_limited` returns a bare 429.
- **Pagination**, partial pages, or changing data between calls.
- **Connection-level failures** such as a dropped connection or a slow body.

## Adding a scenario

1. Add it under `scenarios:` in `python/scenarios/scenarios.yaml`.
2. If it needs a special body, add a branch in `python/mock_server/server.py`.
3. If the contract requires it, add it to `REQUIRED_SCENARIOS` in `tests/test_scenario_loader.py`.
4. Add mock-server tests for the endpoint behaviour (`tests/test_mock_server.py`).
5. Add connector tests for how the connector should respond, both directly and through `sync()`.
6. Run the full suite.

## Design principle

A scenario should represent a specific integration condition, not a random test case. That keeps
scenarios reusable across connectors and the results deterministic.

## Note on `fixtures/`

`python/fixtures/reference/success/assets.json` is currently unused. The server keeps its own copy of
the same data inline. Treat `server.py` as the source of truth until this is resolved.
