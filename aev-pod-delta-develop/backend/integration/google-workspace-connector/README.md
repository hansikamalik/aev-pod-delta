# Google Workspace Connector

Full connector implementation: authenticates against a Workspace tenant via
domain-wide delegation, pulls the user inventory and admin audit log,
normalizes both into a shared asset/finding shape, and pushes the results
to the platform's ingestion service.

## Pipeline

```
authenticate()
      │
      ▼
discover()   → paginated user inventory (Directory API)
      │
      ▼
normalize()  → maps users into Assets
      │             (internally calls ingest() to build Findings
      │              from the admin audit log — see note below)
      ▼
push()       → posts Assets to the platform's ingestion endpoint
```

`GoogleWorkspaceConnector.run_full_sync()` runs the whole pipeline in one
call — this is what a scheduler would invoke on a sync interval.

### Why normalize() also calls ingest()

User inventory and audit log activity come from two different Admin SDK
sub-APIs (Directory vs. Reports) and aren't related the way "discover a
list of IDs, then fetch full detail for each" connectors work. Rather than
exposing that as a separate step callers have to remember to invoke,
`normalize()` handles both: it maps the user records it's given into
Assets, and separately pulls and normalizes audit log activity into
Findings, stored on `self.findings`. `push()` picks up that count when it
reports the sync result.

## Authentication

Uses a service account with domain-wide delegation — see `auth.py` and
`credentials.py` for the full setup (Vault secret shape, required Workspace
Admin Console configuration, scopes).

## Modules

```
src/google_workspace_connector/
├── __init__.py
├── base.py            # shared Connector interface (Asset, Finding, SyncResult, Connector)
├── auth.py             # domain-wide delegation, Directory + Reports API clients
├── credentials.py       # Vault-backed credential loading
├── discovery.py          # paginated Directory API + Reports API pulls
├── normalization.py       # raw records -> Asset / Finding
├── push.py                 # posts Assets to the platform's ingestion endpoint
└── connector.py              # wires the above into the Connector interface
```

## Usage

```python
from google_workspace_connector.connector import GoogleWorkspaceConnector

connector = GoogleWorkspaceConnector(
    vault=vault_client,
    org_id="org-123",
    beta_api_token="...",
)

result = connector.run_full_sync()
print(result.assets_count, result.findings_count, result.errors)
```

Each step is also callable independently — `connector.discover()`,
`connector.ingest()`, `connector.normalize(raw_users)`,
`connector.push(assets)` — for testing or partial runs.

## Findings

Audit log activities are mapped to Findings, not Assets. One activity
record can contain multiple discrete events, so a single activity can
produce several findings. A small set of high-impact event types (granting
admin privileges, disabling two-step verification, deleting or suspending
a user, changing a password) are flagged `high` severity; everything else
is `informational`.

## Push

`push.py` posts normalized assets to the platform's `/assets/ingest`
endpoint. This is a standalone implementation against that documented
contract — swap it for the platform's shared client once available, the
same way the Vault client in `credentials.py` is meant to be swapped.

## Running tests

```bash
pip install -r requirements.txt
pytest -v
```

Everything is mocked — the Google API client, Vault, and outbound HTTP —
so no real tenant, credentials, or network access is required.
