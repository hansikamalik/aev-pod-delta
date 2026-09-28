# Connector Developer Guide (Python)

For TypeScript connectors see [../ts/docs/CONNECTOR_GUIDE.md](../ts/docs/CONNECTOR_GUIDE.md).

## 0. Setup

```powershell
.\run_all.ps1 -PythonOnly        # creates python\.venv, installs, runs the suite once
cd python
.\.venv\Scripts\Activate.ps1
```

Two examples to learn from:

- `SampleConnector` (`python/connector_sdk/sample_connector.py`): the minimum SDK shape, fake
  in-memory data, no network. Its `simulate_failure=True` mode makes `ingest()` raise and
  `check_health()` return `False`.
- `ReferenceConnector` (`python/connectors/reference/connector.py`): an HTTP integration against the
  mock server.

## 1. Subclass `Connector`

```python
from connector_sdk import Connector

class MyConnector(Connector):
    name = "my_source"
```

Use lowercase letters, digits and underscores, starting with a letter (`my_source`, not
`my-source`). The Week-1 SDK does not check this, but the repo's v0.1.0 SDK does
(`^[a-z][a-z0-9_]*$`), so a hyphenated name would break later. Do not leave the default
`"unnamed"`; the TypeScript contract suite already flags it, and the Python side should too.

Implement all five: `discover`, `ingest`, `check_health`, `describe_config`, `describe_credentials`.
`sync()` is inherited.

## 2. Implement `discover()`

Read from the source and normalize into `Asset`. Map the vendor's resource kinds onto the shared
`AssetType` enum, with `OTHER` as the fallback.

```python
_KIND_TO_TYPE = {"vm": AssetType.COMPUTE, "bucket": AssetType.STORAGE}

def discover(self):
    response = httpx.get(
        f"{self.base_url}/api/assets",
        headers={"Authorization": f"Bearer {self.api_key}"},
        params=self.extra_params,       # lets tests select a mock scenario, see step 7
        timeout=self.timeout,
    )
    response.raise_for_status()

    return [
        Asset(
            id=item["id"],
            source=self.name,
            type=_KIND_TO_TYPE.get(item.get("kind"), AssetType.OTHER),
            name=item["name"],
            raw=item,
        )
        for item in response.json().get("assets", [])
    ]
```

Guidelines:

- Keep the normalized shape stable; keep the vendor object in `raw`.
- Always set a timeout on network calls.
- Use `.get("assets", [])` rather than `["assets"]` so a missing key means "nothing found".
- Do not push data from `discover()`.
- Direct indexing (`item["name"]`) raises `KeyError` on a malformed item. The reference connector does
  this today and relies on `sync()` to catch it. Decide deliberately whether your connector should
  validate instead.

## 3. Implement `ingest()`

Receives normalized assets and returns how many were pushed. The sandbox examples keep them in memory:

```python
def ingest(self, assets):
    assets = list(assets)
    self._pushed_assets.extend(assets)
    return len(assets)
```

A production connector replaces this with a call to the platform's asset service.

## 4. Implement `check_health()`

Return a boolean from a lightweight request. The reference connector calls `/health` and returns
`False` on any `httpx.HTTPError` (which includes timeouts).

## 5. Describe configuration

Return a JSON-Schema-like dict for **non-secret** settings:

```python
{
    "type": "object",
    "properties": {"base_url": {"type": "string", "description": "Base URL of the vendor API"}},
    "required": ["base_url"],
}
```

Keep this exact envelope (`type`, `properties`, `required`); do not return a flat map of fields.

## 6. Describe credentials

Same envelope; mark secrets with `"secret": True`. Never put real credentials in tests or source.

```python
{
    "type": "object",
    "properties": {"api_key": {"type": "string", "secret": True}},
    "required": ["api_key"],
}
```

## 7. Make your connector testable against scenarios

The mock server chooses its behaviour from `?scenario=<name>`. Your connector must be able to send
that parameter, otherwise every test hits `success`. `ReferenceConnector` does it with an optional
constructor argument:

```python
def __init__(self, base_url, api_key, timeout=5.0, extra_params=None):
    ...
    self.extra_params = extra_params or {}
```

Tests then build it with `extra_params={"scenario": "unauthorized"}`. Real deployments leave it unset.

## 8. Add your vendor's routes to the mock server

The mock server only serves `/health` and `/api/assets`. For a different vendor API, add routes to
`python/mock_server/server.py` that follow the same scenario pattern:

```python
@app.get("/api/v1/users")                       # your vendor's route
def list_users(scenario: str = Query(default="success")):
    scenarios = load_scenarios()
    if scenario not in scenarios:
        raise HTTPException(status_code=400, detail=f"Unknown scenario: {scenario}")

    config = scenarios[scenario]
    if config.get("delay_seconds"):
        time.sleep(config["delay_seconds"])
    if config["status_code"] != 200:
        raise HTTPException(status_code=config["status_code"], detail=scenario)

    return {"users": [...]}                     # your vendor's response shape
```

Reuse the existing scenarios; only the success payload is vendor-specific. If your vendor needs a
condition that no scenario covers, see [SCENARIOS.md](SCENARIOS.md#adding-a-scenario).

## 9. Test the connector

Copy `python/tests/test_reference_connector.py` and cover at least: normal discovery, successful
sync, empty result, malformed data, 401, 403, 429, 500, timeout, health check, and ingestion.
Full checklist: [TESTING.md](TESTING.md#test-completion-checklist).

### Direct calls versus `sync()`

Test both wherever the difference matters.

```python
list(connector.discover())     # exposes the raw exception
connector.sync()               # converts discover/ingest exceptions into SyncResult.errors
```

A generic harness may call methods directly, so a connector that only behaves inside `sync()` is not
really correct.

## Adding a scenario (short version)

Entries live **under the `scenarios:` key** in `python/scenarios/scenarios.yaml`:

```yaml
scenarios:
  success:
    status_code: 200
  maintenance:           # new
    status_code: 503
```

An entry placed at the top level of the file is silently ignored. Then add tests; see
[SCENARIOS.md](SCENARIOS.md#adding-a-scenario).

## Running tests

```powershell
pytest -q                                         # everything
pytest tests/test_reference_connector.py -q       # one file
pytest tests/test_reference_connector.py -k timeout -v
```

## Before submitting a connector

- `pytest -q` passes.
- No real credentials or production URLs are committed.
- `describe_config()` and `describe_credentials()` are accurate and use the schema envelope.
- `name` is set and follows the naming rule.
- `Asset.raw` preserves useful source data.
- Error paths (direct and via `sync()`) and timeouts are covered.
- If a TypeScript twin exists, its field names match: see [KNOWN_GAPS.md](KNOWN_GAPS.md).
