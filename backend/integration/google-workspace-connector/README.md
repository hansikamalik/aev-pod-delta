# Google Workspace Connector

GitHub-ready connector for the AEV Platform Integration Hub.

## Source-of-truth requirements

The Pod Delta build guide defines the connector contract as:

- `discover()`
- `ingest()`
- `sync()`
- `health_check()`
- `config_schema()`
- `credential_schema()`

Google Workspace is specified as a Service Account JWT connector with user inventory and audit-log ingestion. Credentials are stored/retrieved through the platform's Vault/auth boundary.

The M4 plan specifies the standard connector sequence as authentication, Vault credential retrieval, discovery/ingestion, normalization, platform push, tests, and documentation.

## Dependency

This connector deliberately depends on the project-provided **Google Workspace Auth Module**. The supplied engineering documents specify the auth-module dependency but do not specify its package distribution name or concrete Python API. The connector therefore isolates that dependency behind `GoogleWorkspaceAuthProvider`.

Expected dependency placeholder:

```text
google-workspace-auth >= 1.0.0
```

If your internal auth module uses a different distribution name/version, change `pyproject.toml` without changing the connector contract.

## What it implements

- Service-account JWT authentication through the auth-module boundary.
- User inventory discovery from Google Workspace Admin SDK Directory API.
- Audit-log ingestion through Google Workspace Admin SDK Reports API.
- Shared `Asset` normalization.
- Health checking.
- JSON schemas for connector configuration and credentials.
- Incremental sync state via an injected state store.
- Idempotent stable source identifiers.
- Resumable per-resource sync state.
- Unit tests with mocked Google Workspace APIs/auth.

## Repository layout

```text
google-workspace-connector/
├── .github/workflows/ci.yml
├── examples/config.example.json
├── src/google_workspace_connector/
│   ├── __init__.py
│   ├── connector.py
│   ├── auth.py
│   ├── clients.py
│   ├── models.py
│   ├── schemas.py
│   ├── normalize.py
│   └── state.py
├── tests/
│   ├── test_connector.py
│   ├── test_normalize.py
│   └── test_schemas.py
├── .gitignore
├── LICENSE
├── pyproject.toml
└── README.md
```

## Configuration

Example:

```json
{
  "customer_id": "my_customer",
  "domain": "example.com",
  "admin_user": "admin@example.com",
  "sync": {
    "users": true,
    "audit_logs": true,
    "audit_application": "login",
    "page_size": 100
  }
}
```

The auth module is responsible for obtaining credentials securely. Do not put private keys in source control or connector configuration.

## Platform integration

The connector is intentionally framework-agnostic at its edges. The platform adapter should:

1. Construct `GoogleWorkspaceConnector` with the platform's Google Workspace auth provider.
2. Inject the platform state store.
3. Call `discover()` for normalized assets.
4. Call `ingest()` for audit events.
5. Publish normalized records to the platform Asset/Exposure service.
6. Persist sync checkpoints and `last_sync_at` using the platform sync engine.

No project-specific platform endpoint was invented because the supplied documents define the responsibility but not a concrete HTTP client contract.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

On Windows:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest -q
```

## Security notes

- Never commit service-account private keys.
- Keep credentials in the platform Vault/auth module.
- Request only the Google Workspace scopes approved by the deployment.
- Use read-only scopes unless a future requirement explicitly needs write access.
