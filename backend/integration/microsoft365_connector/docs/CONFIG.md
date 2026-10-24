# Configuration reference

`config/config.example.yaml` — copy to `config.yaml` and fill in tenant
values. Secrets are never stored here; they're Vault paths instead.

| Key | Meaning |
|---|---|
| `azure_ad.tenant_id` | Entra ID tenant GUID |
| `azure_ad.client_id` | App registration client ID |
| `azure_ad.client_secret_vault_path` | Vault KV v2 path holding `{"client_secret": ...}` |
| `azure_ad.graph_api_base_url` | Graph API base, normally `https://graph.microsoft.com/v1.0` |
| `azure_ad.scope` | OAuth2 scope, normally `https://graph.microsoft.com/.default` |
| `platform.api_base_url` | AEV platform API base URL |
| `platform.api_token_vault_path` | Vault KV v2 path holding `{"api_token": ...}` |
| `platform.ingest_endpoint` | Asset ingest path on the platform API |
| `platform.findings_ingest_endpoint` | Findings (audit log) ingest path on the platform API |
| `platform.batch_size` | Assets/findings per push request |
| `vault.addr` | Vault address (token itself comes from `VAULT_TOKEN` env var) |
| `sync.discover_*` | Toggle each resource type on/off (`discover_audit_logs` included) |
| `sync.audit_log_lookback_hours` | How far back each sync pulls directory audit log entries |
| `sync.page_size` | Graph API `$top` page size |
| `logging.level` | Python logging level |
