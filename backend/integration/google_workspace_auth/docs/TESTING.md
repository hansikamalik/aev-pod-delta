# Testing

The suite is fully offline.

```bash
pytest -q
pytest --cov=google_workspace_auth --cov-report=term-missing
```

Covered cases include successful token exchange, caching, expiry refresh, explicit
invalidation, network failure, malformed JSON, missing fields, invalid expiry,
configuration validation, and authorization-header generation.

The project plan calls for at least 70% coverage and integration testing. Live Google
Workspace testing requires backend-provided configuration and approved credentials.
