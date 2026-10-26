# Public Connector SDK Developer Guide

This guide governs the development, testing, packaging, and registration of connectors against the platform sync architecture[cite: 2].

## Core Contract Requirements
* **Methods:** Every connector must implement `discover()`, `ingest()`, `check_health()`, `describe_config()`, and `describe_credentials()`[cite: 2].
* **Models:** Data objects flow via shared `Asset` and `SyncResult` schemas using snake_case field naming[cite: 2].
* **Security:** Credentials retrieved via HashiCorp Vault must never be hardcoded or leaked into plain text audit logs.
