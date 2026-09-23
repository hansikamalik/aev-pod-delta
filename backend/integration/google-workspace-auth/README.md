# Google Workspace Auth Module

Authentication layer for a Google Workspace connector, using a service
account with domain-wide delegation to call the Admin SDK on behalf of a
Workspace admin. Credentials are loaded from Vault, never from local files
or environment variables.

## Why domain-wide delegation

Google Workspace has no interactive OAuth flow for backend services. A
service account is instead granted permission, in the target Workspace's
Admin Console, to impersonate a specific admin account for a defined set
of OAuth scopes. The service account then requests tokens as that admin
directly, with no user-facing consent step.

```
Vault secret (service account key + delegated admin email)
        │
        ▼
credentials.py   loads and validates the secret, returns an AuthConfig
        │
        ▼
auth.py          builds delegated credentials, refreshes the token, and
                  validates it with a real Admin SDK call
```

## One-time setup (Workspace Admin Console)

This module assumes delegation has already been configured on the target
tenant. To set it up:

1. Create a service account in Google Cloud Console and download its JSON
   key.
2. Note the service account's numeric **Client ID**.
3. In the Workspace Admin Console → Security → API Controls → Domain-wide
   Delegation, authorize that Client ID for the scopes listed in
   `credentials.py::DEFAULT_SCOPES` (or your own override).
4. Store the service account key and the delegated admin's email in Vault
   using the shape below.

## Vault secret shape

Path: `secret/connectors/google-workspace/{org_id}`

```json
{
  "service_account_json": "<the full service account JSON key, as a string>",
  "delegated_admin_email": "admin@customer-domain.com",
  "scopes": "[\"https://www.googleapis.com/auth/admin.directory.user.readonly\"]"
}
```

`scopes` is optional — if omitted, `DEFAULT_SCOPES` is used. Since Vault
secrets are string key/value, it's accepted as either a JSON-encoded list
or a single scope string.

## Vault client interface

```python
class VaultClientProtocol(Protocol):
    def read_secret(self, path: str) -> Dict[str, str]: ...
```

Swap in your real Vault client wherever this is wired up — nothing here
depends on anything beyond `read_secret(path)`. `MockVaultClient` is a
fixture-backed stand-in for local development and tests.

## Usage

```python
from google_workspace_connector.credentials import load_google_workspace_credentials
from google_workspace_connector.auth import GoogleWorkspaceAuthenticator

config = load_google_workspace_credentials(vault=vault_client, org_id="org-123")
authenticator = GoogleWorkspaceAuthenticator(config)

if authenticator.validate():
    service = authenticator.get_directory_service()  # Admin SDK Directory API client
```

`validate()` doesn't just check that a token was issued — it makes a real,
cheap Admin SDK call, since a token can be issued and still fail if
delegation wasn't configured correctly on the tenant side.

## Project layout

```
src/google_workspace_connector/
├── __init__.py
├── auth.py            # AuthConfig, GoogleWorkspaceAuthenticator
└── credentials.py      # Vault-backed credential loading
tests/
├── test_auth.py
└── test_credentials.py
```

## Running tests

```bash
pip install -r requirements.txt
pytest -v
```

Tests mock both the Google API client and Vault, so no real tenant or
network access is required.

## Notes

- Credentials, once loaded, are never logged or serialized — `AuthConfig`'s
  `__repr__` redacts the service account key.
- Failures are fail-fast: a malformed or incomplete Vault secret raises
  immediately with a specific error, rather than surfacing later as an
  opaque auth failure.
- Discovery, ingestion, normalization, and sync are out of scope for this
  module and live in the connector layer that consumes it.
