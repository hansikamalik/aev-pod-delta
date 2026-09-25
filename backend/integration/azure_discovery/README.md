# Azure Discovery Engine
**Owner:** Subramani

Discovers Azure resources — VMs, Storage Accounts, AAD objects, SQL Databases,
and Function Apps — with pagination, retry-on-transient-error handling, and
fatal-error short-circuiting.

Developed independently against `mock_azure_api.py`, per the parallel-work
rule: this module never waits on Bhavesh's real authentication module. The
engine only requires an API client object exposing `list_*` methods, so the
mock is a drop-in swap for a real Azure SDK-based client later.

## Files
- `src/azure_discovery.py` — engine, pagination, retries, error types
- `src/mock_azure_api.py` — mock Azure API client with fault injection
- `tests/test_azure_discovery.py` — unit tests

## Run
```bash
pip install -r requirements.txt
pytest tests/ -v
```

## Usage
```python
from azure_discovery import AzureDiscoveryEngine, DiscoveryConfig
from mock_azure_api import MockAzureApiClient

client = MockAzureApiClient()
engine = AzureDiscoveryEngine(client, DiscoveryConfig(page_size=50))
results = engine.discover()  # {"vm": [...], "storage": [...], ...}
```
