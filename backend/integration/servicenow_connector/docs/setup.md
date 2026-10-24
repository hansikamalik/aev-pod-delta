# ServiceNow Connector — Setup & Config

## 1. ServiceNow-side requirements

| Requirement | Notes |
|---|---|
| Instance | Any PDY/PDI instance reachable from the sync worker |
| User | Service account with read access to `cmdb_ci` and `incident` |
| Auth | Basic auth (simplest) or an OAuth app (password grant) |
| Rate limits | Default Table API limits apply; the client retries 429/5xx with backoff |

### OAuth app (optional)
1. Navigate to **System OAuth > Application Registry > New > Create an OAuth API endpoint for external clients**.
2. Note the **Client ID** and **Client Secret**.
3. Ensure the service account can use the `password` grant.

## 2. Credentials in Vault (recommended)

```bash
vault kv put secret/connectors/servicenow   username="svc-aev-sync"   password="****"   oauth_client_id=""   oauth_client_secret=""
```

Leave `auth.username` / `auth.password` empty in the config to force the Vault
lookup path. The connector reads `VAULT_ADDR` and `VAULT_TOKEN` (or
`VAULT_NAMESPACE`) from the environment.

## 3. Connector config

Copy `config/servicenow.example.yaml` to `config/servicenow.yaml` and set:

- `instance_url` — your instance, e.g. `https://dev12345.service-now.com`
- `auth.method` — `basic` or `oauth`
- `tables.cmdb_ci` / `tables.incident` — override if you use extended tables
  (e.g. `cmdb_ci_server` or `sn_si_incident`)
- `push.asset_url` / `push.exposure_url` — Beta platform endpoints
  (env overrides: `AEV_ASSET_URL`, `AEV_EXPOSURE_URL`)
- `AEV_PLATFORM_TOKEN` — bearer token for the push stage

## 4. Run

```bash
# health check (auth + table probes)
python -m connectors.servicenow.health_check --config config/servicenow.yaml

# full sync
python -c "from connectors.servicenow.connector import ServiceNowConnector; print(ServiceNowConnector().run_sync())"
```

## 5. Test

```bash
pytest tests/ -v                      # unit tests (no network)
pytest tests/integration -v           # sandbox tests (needs mock server)
```

## 6. Troubleshooting

| Symptom | Likely cause |
|---|---|
| `401` on every call | Wrong credentials, or user locked / SSO-only |
| `403` on a table | Service account lacks read ACL on that table |
| `VaultError: no secret found` | Path not `secret/data/...` KV v2 format, or secret missing |
| Push 4xx | `AEV_PLATFORM_TOKEN` missing/expired or URL wrong |
