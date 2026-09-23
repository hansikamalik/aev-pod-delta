# Connector SDK — Week 1 Scaffold

Python SDK that defines the shared `Connector` contract every connector
(AWS, Azure, GCP, CrowdStrike, Splunk, Jira, Okta, ...) must implement.
This is the interface frozen jointly with the Integration squad.

## Install

```bash
pip install -r requirements.txt
pip install -e .          # optional, if you add a setup.py/pyproject.toml
```

## Run the tests

```bash
python -m pytest tests/ -v
```

## Project layout

```
connector_sdk/
├── connector_sdk/
│   ├── __init__.py        # public exports
│   ├── models.py           # Asset, SyncResult data shapes
│   ├── connector.py        # abstract Connector base class
│   └── sample_connector.py # reference implementation (fake data)
├── tests/
│   └── test_sample_connector.py
├── requirements.txt
└── README.md
```

## Data models (`models.py`)

- **`Asset`** — normalized representation of any discovered resource
  (an EC2 instance, an Okta user, a Jira ticket, etc).
- **`SyncResult`** — outcome of a single `sync()` run: how many assets
  were discovered/pushed, status, errors, timing.

## The 6 interface methods

Every connector subclasses `Connector` and implements these:

### 1. `discover() -> Iterable[Asset]`
Reads from the source system and returns normalized assets. No side effects.

```python
def discover(self) -> Iterable[Asset]:
    for vm in self._client.list_vms():
        yield Asset(id=vm.id, source=self.name, type=AssetType.COMPUTE, name=vm.name, raw=vm.dict())
```

### 2. `ingest(assets: Iterable[Asset]) -> int`
Pushes a batch of assets to the platform's asset service. Returns count pushed.

```python
def ingest(self, assets: Iterable[Asset]) -> int:
    assets = list(assets)
    self._platform_client.bulk_upsert(assets)
    return len(assets)
```

### 3. `sync() -> SyncResult`
Runs discover → ingest and reports the outcome. Has a default implementation
in the base class built on `discover()`/`ingest()` — override only if you
need custom batching or incremental logic.

```python
result = connector.sync()
print(result.status, result.assets_pushed)
```

### 4. `check_health() -> bool`
Confirms credentials are valid and the source system is reachable.

```python
def check_health(self) -> bool:
    try:
        self._client.ping()
        return True
    except Exception:
        return False
```

### 5. `describe_config() -> dict`
JSON-schema-like description of non-secret configuration fields.

```python
def describe_config(self) -> dict:
    return {"type": "object", "properties": {"region": {"type": "string"}}, "required": ["region"]}
```

### 6. `describe_credentials() -> dict`
JSON-schema-like description of the credential fields needed.

```python
def describe_credentials(self) -> dict:
    return {"type": "object", "properties": {"api_key": {"type": "string", "secret": True}}, "required": ["api_key"]}
```

## Writing a new connector

1. Copy `sample_connector.py` as your starting point.
2. Implement `discover`, `ingest`, `check_health`, `describe_config`,
   `describe_credentials`.
3. Leave `sync()` as-is unless you need custom logic.
4. Add tests mirroring `tests/test_sample_connector.py`.
5. Run the joint contract test with the Integration squad before merging.

## Note

`pydantic` and `pytest` could not be installed/run in the sandbox that
generated this scaffold (no network access), so the test suite has been
written but not executed here. Run `pip install -r requirements.txt &&
python -m pytest tests/ -v` locally to confirm — the logic has been
reviewed by hand and should pass cleanly.
