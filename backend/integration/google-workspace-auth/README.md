# Google Workspace Auth Module

Authentication module for the AEV Platform Integration Hub's Google Workspace connector.

## Scope
This module is authentication-only. It provides a connector-friendly interface for
Google OAuth 2.0 access tokens using a service account with Domain-Wide Delegation.

The project materials define standardized connector capabilities such as discovery,
ingestion, synchronization, health checks, configuration schema and credential schema.
Google Workspace is listed as a productivity-platform integration.

## SentinelOne shadowing dependency
The task was described as depending on "shadowing SentinelOne". The provided project
materials list SentinelOne as an endpoint-security connector, but do not include its
implementation or a concrete shared SDK auth interface. Therefore this module exposes
a small, isolated `GoogleWorkspaceAuthenticator` interface. The backend team can
adapt the thin integration layer to the actual SentinelOne/shared SDK interface.

## Flow
```text
AEV Google Workspace Connector
          |
          v
GoogleWorkspaceAuthenticator
          |
          | signed JWT assertion
          v
Google OAuth 2.0 token endpoint
          |
          v
access token
          |
          v
Google Workspace APIs
```

## Security
Do not commit service-account private keys, access tokens, refresh tokens, secrets,
`.env` files, or production configuration. Inject the private key at runtime from
the backend team's approved secret store.

## Local testing
```bash
pip install -r requirements-dev.txt
pytest -q
pytest --cov=google_workspace_auth --cov-report=term-missing
```

All tests are offline and require no Google credentials.

## Example
```python
from google_workspace_auth import GoogleWorkspaceAuthenticator

auth = GoogleWorkspaceAuthenticator(
    client_email="service-account@example.iam.gserviceaccount.com",
    private_key=private_key_from_secret_store,
    delegated_subject="admin@example.com",
)

token = auth.get_token()
headers = {"Authorization": f"{token.token_type} {token.access_token}"}
```
