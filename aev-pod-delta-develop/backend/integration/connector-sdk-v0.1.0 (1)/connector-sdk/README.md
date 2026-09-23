# Connector SDK

Common contract, base classes, and shared contract test suite for platform
integration connectors. This is the code implementation of `contract_v2.md`.

**Every connector MUST extend `Connector` and MUST pass the shared contract
test suite before merge.**

- Zero runtime dependencies (stdlib only) — installs cleanly everywhere.
- Python 3.10+
- Current version: **0.1.0**

---

## Install

From the repo root, in each workstream's virtualenv:

```bash
pip install -e ".[dev]"
```

Or as a dependency of a connector repo:

```bash
pip install "connector-sdk @ git+ssh://git@github.com/<org>/connector-sdk.git@v0.1.0"
```

**Pin `connector-sdk==0.1.0` for Week 1.** Breaking changes to the contract go
through the Integration Lead — see [CONTRIBUTING.md](CONTRIBUTING.md).

Verify your environment:

```bash
pytest          # SDK's own suite: models, base class, schemas, contract suite
ruff check src tests
```

---

## Quickstart

```python
from connector_sdk import Asset, AssetType, Connector, object_schema, field, secret_field

class AzureConnector(Connector):
    name = "azure"                      # stable, lowercase, no env/version

    def discover(self):
        for vm in self._client.list_vms():          # handles pagination
            yield Asset(
                id=vm["id"],                        # stable source ID
                source=self.name,                   # MUST equal name
                type=AssetType.COMPUTE,             # normalized category
                name=vm["name"],
                raw=vm,                             # original payload, no secrets
            )

    def ingest(self, assets):
        assets = list(assets)
        accepted = self._platform.bulk_upsert(assets)
        return accepted                             # only what was accepted

    def check_health(self) -> bool:
        try:
            return self._client.ping()
        except Exception:
            return False

    def describe_config(self) -> dict:
        return object_schema(
            {"tenant_id": field("string"), "subscription_id": field("string")},
            required=["tenant_id", "subscription_id"],
        )

    def describe_credentials(self) -> dict:
        return object_schema({"client_secret": secret_field()}, required=["client_secret"])
```

Run it:

```python
result = await connector.sync()          # or connector.sync_blocking()
print(result.status, result.assets_discovered, result.assets_pushed)
```

**Do not implement `sync()`.** The SDK provides it: `discover → ingest →
SyncResult`, with status derived per contract Section 15, errors captured
rather than propagated, and timestamps stamped automatically. Override only
for a documented reason (incremental sync, checkpointing, custom batching,
retry orchestration) and preserve the `SyncResult` contract.

---

## Wiring the contract tests into your connector

This is the whole integration — one fixture:

```python
# tests/test_contract.py
import pytest
from connector_sdk.testing import ConnectorContractTests
from azure_connector import AzureConnector

class TestAzureContract(ConnectorContractTests):
    @pytest.fixture
    def connector(self):
        return AzureConnector(
            config={"tenant_id": "t", "subscription_id": "s"},
            credentials={"client_secret": "x"},
            client=FakeAzureClient(),        # your mock
        )
```

That runs ~27 assertions covering name validity, discovery output, asset
identity and stability, type normalization, secret leakage in `raw`,
ingestion counts, health, schema hygiene, credential redaction, sync status
coherence, timestamps, and idempotency.

Do not skip or override a contract test to make a connector pass. A failure
means either the connector or the contract needs to change, and the contract
goes through the Integration Lead.

---

## Test doubles — build without waiting for anyone

`connector_sdk.testing` ships fakes so no workstream blocks on another:

```python
from connector_sdk.testing import FakeConnector, InMemoryPlatformClient

# Scheduler / distributed-lock testing with no real source system:
connector = FakeConnector()
assert connector.sync_blocking().status == "success"

# Partial-sync path (platform rejects one asset):
platform = InMemoryPlatformClient(reject_ids={"vm-0002"})
assert FakeConnector(platform=platform).sync_blocking().status == "partial"

# Source outage:
assert FakeConnector(raise_on_discover=True).sync_blocking().status == "failed"

# Platform outage:
assert FakeConnector(platform=InMemoryPlatformClient(fail_entirely=True)) \
    .sync_blocking().status == "failed"
```

`src/sample_connector/` is the reference implementation (contract Section 27):
cursor pagination, deterministic IDs, type mapping with an `other` fallback,
batched ingestion, config-flag filtering. Copy its structure and replace the
source-specific parts. Treat it as a behavioral reference, not production code.

---

## Who uses what, this week

| Workstream | Owner | Start here |
|---|---|---|
| Azure authentication | Bhavesh | `describe_credentials`, `validate_configuration()`, `AuthenticationError`, `safe_credentials` for logging |
| Azure discovery | Subramani | `discover()`, `Asset`, `AssetType`, `build_asset_id`, `RateLimitError`/`SourceUnavailableError` for retries |
| Azure normalization + push | Ashwin | `Asset.to_dict()`, `ingest()`, `IngestionError`, `InMemoryPlatformClient` as the push target |
| Splunk connector | Ayyappatadi | Whole `Connector` surface; `sample_connector/` as the skeleton |
| Vault + scheduling + lock | Abhiram | `FakeConnector` as the dummy connector; `sync_blocking()` as the cron entry point; `SyncResult.status` for job outcome |
| QA + automation | Bhawook | `ConnectorContractTests`, the doubles, `tests/` as the pattern to copy |

---

## Package layout

```
src/connector_sdk/
├── __init__.py          public API — import from here, not submodules
├── connector.py         Connector ABC + default sync()
├── models.py            Asset, SyncResult, build_asset_id
├── enums.py             AssetType, SyncStatus
├── exceptions.py        error hierarchy with retryable flag
├── schemas.py           config/credential schema build + validate + redact
└── testing/
    ├── contract.py      ConnectorContractTests (inherit this)
    └── doubles.py       FakeConnector, InMemoryPlatformClient

src/sample_connector/    reference implementation (Section 27)
tests/                   the SDK's own suite — 130 cases
```

---

## Hard rules, enforced in code

| Rule | Where enforced |
|---|---|
| `asset.source == connector.name` | `discover_validated()` → `ContractViolation` |
| Asset type is a known category | `Asset.__post_init__` → `ValidationError` |
| Asset IDs unique per run, stable across runs | `discover_validated()`, contract suite |
| `ingest()` returns an `int` it can justify | `_coerce_pushed_count()` |
| Never report `success` with errors or a short push | `SyncResult.derive_status()` |
| Config contains no secrets | `assert_valid_schema(kind="config")` |
| Credential fields marked `"secret": True` | `assert_valid_schema(kind="credentials")` |
| Secrets never logged | `safe_credentials`, `redact()` |
| Secrets never in error messages | validators omit values by construction |
| `sync()` never propagates an exception | `sync()` error boundary |

---

## Definition of Done for a connector PR

- [ ] Extends `Connector`; no public signature changed
- [ ] `TestXContract(ConnectorContractTests)` present and green
- [ ] Unit tests for discovery, ingestion, health, sync (success/partial/failed)
- [ ] Pagination handled, or full-sync behavior documented in the README
- [ ] Retries limited to transient failures; no duplicate assets on retry
- [ ] No hardcoded credentials; secrets only via `describe_credentials`
- [ ] `ruff check` clean, CI green
- [ ] Connector README: config, credentials, asset types, sync mode
