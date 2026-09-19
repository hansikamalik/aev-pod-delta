# ServiceNow Connector

Full connector for the AEV platform. Implements the standard connector pattern:

| Stage | Module | Description |
|---|---|---|
| Authentication | `auth.py` | Basic-auth + OAuth token support against a ServiceNow instance |
| Credentials | `vault.py` | Credential retrieval through HashiCorp Vault (KV v2) |
| Discovery | `discovery.py` | `discover()` — enumerate CMDB CIs and security-incident findings |
| Ingestion | `ingestion.py` | `ingest()` — pull raw records with pagination + retry |
| Normalization | `normalize.py` | Map ServiceNow records to the shared `Asset` / `Finding` shape |
| Push | `push.py` | Send normalized records to the Beta asset/exposure service |
| Health check | `health_check()` | Verify instance reachability + auth validity |

## Quick start

```bash
pip install -r requirements.txt
cp config/servicenow.example.yaml config/servicenow.yaml   # fill in values
export VAULT_ADDR="https://vault.example.com"
export VAULT_TOKEN="..."
python -m connectors.servicenow.health_check --config config/servicenow.yaml
pytest tests/ -v
```

## Configuration

| Key | Env override | Description |
|---|---|---|
| `instance_url` | `SN_INSTANCE_URL` | e.g. `https://dev12345.service-now.com` |
| `auth.method` | `SN_AUTH_METHOD` | `basic` or `oauth` |
| `auth.username` | `SN_USERNAME` | ServiceNow user (or Vault lookup if empty) |
| `auth.password` | `SN_PASSWORD` | Password (or Vault lookup if empty) |
| `auth.oauth_client_id` / `oauth_client_secret` | `SN_OAUTH_CLIENT_ID` / `SN_OAUTH_CLIENT_SECRET` | OAuth app credentials |
| `vault.path` | — | Vault KV v2 path, e.g. `secret/data/connectors/servicenow` |
| `tables.cmdb_ci` | — | CMDB table to scan (default `cmdb_ci`) |
| `tables.incident` | — | Findings table (default `incident`) |
| `push.asset_url` | `AEV_ASSET_URL` | Beta asset service endpoint |
| `push.exposure_url` | `AEV_EXPOSURE_URL` | Beta exposure service endpoint |
| `push.token` | `AEV_PLATFORM_TOKEN` | Bearer token for the Beta platform |
| `batch_size` | — | Records per API page (default 200) |

See `docs/setup.md` for the full setup + ServiceNow-side requirements.
