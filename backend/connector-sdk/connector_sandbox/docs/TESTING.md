# Testing Guide

Run everything with `.\run_all.ps1` (see the [README](../README.md)). At v0.3.0 that is **39 Python
tests and 13 TypeScript tests**; these numbers will change as tests are added.

## Python

### Test modules (`python/tests/`)

| File | Runs against | Verifies |
|---|---|---|
| `test_mock_server.py` | In-process `TestClient` (no socket) | `/health`; success, default, empty, malformed payloads; each error status; unknown scenario returns 400; the timeout scenario really delays |
| `test_reference_connector.py` | A **real** server on a localhost port (`live_server`) | Normalization; full sync; zero-asset sync; malformed data; 401/403/429/500; client timeout; health checks. Each case is tested both directly and through `sync()` |
| `test_runner_cli.py` | `live_server` | `run_connector()` output and return value; `main()` exit code 0 on success and 1 on failure |
| `test_scenario_loader.py` | YAML file | Loads to a dict; all required scenarios exist with the right status; the timeout scenario declares a positive delay |

The mock-server tests do not prove a connector handles responses correctly. That is the connector
tests' job. A real socket is needed for connector tests because the connector calls `httpx.get(url)`,
which cannot be pointed at an in-process ASGI app.

### Fixtures (`python/conftest.py`)

- **`api_client`**: in-process `TestClient`. Use for mock-server endpoint tests.
- **`live_server`**: real Uvicorn on a free port. It finds a port, starts a background thread, polls
  `/health` until ready, yields the base URL, then shuts down and joins the thread. It starts a fresh
  server per test, which is why the suite takes about 20 s (the three timeout tests also wait about 2 s each).

### Running

```powershell
pytest -q                                          # all
pytest tests/test_reference_connector.py -q        # one file
pytest -k timeout -v                               # by name
```

Expect one deprecation warning from `starlette.testclient` (about `httpx`). It does not fail the suite.

### Expected behaviour matrix (default `sync()`)

| Situation | `discover()` called directly | `sync()` |
|---|---|---|
| Valid response | returns assets | `SUCCESS` |
| Empty response | returns an empty list | `SUCCESS` (0 discovered, `ingest()` skipped) |
| Malformed item | raw exception (`KeyError`) | `FAILED`, error `discover() failed: ...` |
| 401 / 403 / 429 / 500 | `httpx.HTTPStatusError` | `FAILED`, error `discover() failed: ...` |
| Client timeout | `httpx.TimeoutException` | `FAILED`, error `discover() failed: ...` |
| `ingest()` raises | n/a | `FAILED`, error `ingest() failed: ...` |

`PARTIAL` is not in this table because the default `sync()` never produces it (see
[ARCHITECTURE.md](ARCHITECTURE.md#6-default-sync-lifecycle)).

**Not yet covered by a test:** the last row. `SampleConnector(simulate_failure=True)` makes `ingest()`
raise, so a suggested test is:

```python
from connector_sdk import SampleConnector, SyncStatus

def test_sync_reports_ingest_failure():
    result = SampleConnector(simulate_failure=True).sync()
    assert result.status == SyncStatus.FAILED
    assert result.assets_discovered == 3 and result.assets_pushed == 0
    assert result.errors == ["ingest() failed: simulated push failure"]
```

### Why both direct and wrapped behaviour are tested

A generic harness can call `discover()` directly, so a connector must not only look correct when called
through `sync()`. The suite deliberately checks `list(connector.discover())` and `connector.sync()`.

### Known limits of the Python tests

- The mock server never validates credentials, so no test can prove authentication is handled.
- There is no reusable contract suite; each connector copies `test_reference_connector.py`.
- No test checks that a connector missing an abstract method is rejected.
- The unsupported-type path is not exercised (see [SCENARIOS.md](SCENARIOS.md#malformed)).

## TypeScript

### Test files (`ts/tests/`)

| File | Verifies |
|---|---|
| `sample.contract.test.ts` | The shared contract suite (7 checks) against `SampleConnector`, plus 3 behaviour tests: kind-to-type mapping, `FAILED` when `ingest()` throws, `checkHealth()` false when simulating failure |
| `mockServer.test.ts` | `MockApiServer` starts, serves a route, returns 404 for unknown routes |
| `sandboxTestHarness.template.test.ts` | Starter for a new connector. **Excluded** from runs by `vitest.config.ts` |

`runContractSuite(factory)` (in `src/testing/contractHarness.ts`) takes a function that builds your
connector and runs the generic checks against it: name is set, `discover()` returns an array,
`ingest()` returns a count, `sync()` returns a result, `checkHealth()` returns a boolean, and both
`describe*` methods return objects.

### Running

```powershell
cd ts
npm run typecheck
npm test
```

### Known limits of the TypeScript tests

- `mockServer.test.ts` contains an `it.fails` test asserting that `/assets?limit=10` returns 200. It
  returns 404 today, so the test counts as **passed while the bug exists**. When the mock server is
  fixed, that test will fail; convert it to a normal `it`.
- The mock server ignores the HTTP method and headers and cannot return errors or delays, so failure
  scenarios cannot be tested in TypeScript.
- The contract checks are shallow: `discover()` is checked for being an array, not for valid assets,
  and the `describe*` results are checked only for being objects, not for the schema shape.

## Adding tests for a new connector

Start from the reference tests (Python) or the template (TypeScript). Use a local mock server or a
controlled test double for the external boundary.

Avoid: real production credentials, real production APIs, tests that need internet access, fixed ports,
and long arbitrary sleeps.

## Test completion checklist

- [ ] Success path
- [ ] Empty response
- [ ] Malformed data
- [ ] Authentication failure
- [ ] Authorization failure (where applicable)
- [ ] Rate limiting (where applicable)
- [ ] Server failure
- [ ] Timeout (network connectors)
- [ ] Health check (healthy and unreachable)
- [ ] Ingestion count
- [ ] Ingestion failure
- [ ] Each error case tested both directly and through `sync()`
- [ ] `describe_config()` / `describe_credentials()` use the schema envelope
- [ ] Full suite passes (`.\run_all.ps1`)
