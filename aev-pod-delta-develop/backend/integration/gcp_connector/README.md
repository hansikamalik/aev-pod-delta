# GCP Connector

Discovers Compute Engine instances, Cloud Storage buckets, IAM service
accounts, and Cloud SQL instances in a GCP project, normalizes them into
the platform's shared `Asset` shape (from `connector_sdk`), and pushes
them to the platform's asset service.

Built against the `connector_sdk.Connector` interface frozen with the
Integration squad in Week 1. Owners: Harshal Sahare & Bhavesh Kanekar.

## Install

```bash
pip install -r requirements.txt
```

## What it discovers

| Resource | GCP API | Normalized as |
|---|---|---|
| VM instances | Compute Engine (`compute.instances.aggregatedList`) | `AssetType.COMPUTE` |
| Buckets | Cloud Storage (`storage.buckets.list`) | `AssetType.STORAGE` |
| Service accounts | IAM (`iam.projects.serviceAccounts.list`) | `AssetType.IDENTITY` |
| SQL instances | Cloud SQL Admin (`sqladmin.instances.list`) | `AssetType.OTHER`, tagged `resource_kind=cloudsql` |

The shared `Asset` contract (frozen Week 1) only defines 6 broad
`AssetType` values and has no `DATABASE` category, so Cloud SQL
instances are normalized as `OTHER` with a `resource_kind` tag —
the same convention any connector should use for a resource type
outside those 6 categories, so it doesn't fork the shared contract.

## Configuration

`describe_config()`:

```json
{
  "type": "object",
  "properties": {
    "project_id": { "type": "string", "description": "GCP project ID to discover resources in" }
  },
  "required": ["project_id"]
}
```

## Credentials

`describe_credentials()`:

```json
{
  "type": "object",
  "properties": {
    "service_account_key_json": {
      "type": "string",
      "secret": true,
      "description": "Full JSON key for a read-only GCP service account"
    }
  },
  "required": ["service_account_key_json"]
}
```

### Setting up the service account (customer-side)

1. In the GCP project to be onboarded, create a dedicated service
   account, e.g. `platform-copilot-readonly@<project>.iam.gserviceaccount.com`.
2. Grant it read-only roles: `roles/compute.viewer`,
   `roles/storage.objectViewer` (bucket metadata, not object contents),
   `roles/iam.securityReviewer`, `roles/cloudsql.viewer`. Do **not**
   grant any write/admin role — the connector never mutates the source
   project.
3. Create a JSON key for the service account and paste its contents
   into the connector's credential field during onboarding. The key is
   stored in the platform's secrets vault, never in plaintext config.
4. The connector authenticates with `cloud-platform.read-only` OAuth
   scope (see `auth.py`) — it cannot write to the project even if a
   broader role were mistakenly granted.

## Usage

```python
from gcp_connector import GCPConnector

connector = GCPConnector(
    project_id="my-gcp-project",
    service_account_key_json=vault.get_secret("gcp/my-gcp-project/key"),
)

result = connector.sync()
print(result.status, result.assets_discovered, result.assets_pushed)
```

## Testing

```bash
python -m pytest tests/ -v
```

Unit and integration tests run against `FakeGCPAPIClient`, which
returns canned Compute/Storage/IAM/Cloud SQL data with the same shape
the real GCP APIs return — this is the "sandbox/mock account" this
week's checklist calls for, and lets CI run the full discover → ingest
cycle without live GCP credentials or network access.

> Note: `pydantic`, `pytest`, and the `google-*` client libraries could
> not be installed in the sandbox that generated this connector (no
> network access — same constraint noted in the SDK squad's Week 1
> scaffold), so the suite has been written and reviewed by hand but not
> executed here. Run `pip install -r requirements.txt && python -m
> pytest tests/ -v` locally to confirm before merging, per the Week 2
> checklist ("All tests passing in CI").

## Health check

`check_health()` calls a cheap, side-effect-free GCP API
(`compute.zones.list` with `maxResults=1`) to confirm the service
account's credentials are valid and the project is reachable, without
doing a full discovery pass.

## Files

```
gcp_connector/
├── gcp_connector/
│   ├── __init__.py     # public exports
│   ├── auth.py          # service-account auth module
│   ├── client.py        # real (GCPAPIClient) + fake (FakeGCPAPIClient) API clients
│   └── connector.py     # GCPConnector: discover/ingest/normalize
├── tests/
│   └── test_gcp_connector.py
├── requirements.txt
└── README.md
```

## Status against the Week 2 task breakdown

| Sub-task | Status |
|---|---|
| Authentication (service account) | Done — `auth.py`, read-only scope |
| Credentials configuration | Done — `describe_credentials()` |
| Asset discovery (Compute, Storage, IAM, Cloud SQL) | Done — `client.py` + `connector.discover()` |
| Data normalization | Done — `Asset`-shape mapping in `connector.py` |
| Push to platform | Done — `ingest()` via injectable `PlatformClient` |
| Unit tests | Written, not yet executed (see note above) |
| Integration testing (sandbox/mock account) | Done via `FakeGCPAPIClient` |
| Documentation | This file |
