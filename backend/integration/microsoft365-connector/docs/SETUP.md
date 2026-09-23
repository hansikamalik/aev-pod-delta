# Setup

## 1. Azure AD app registration

1. Azure Portal → Microsoft Entra ID → App registrations → New registration.
2. Note the **Application (client) ID** and **Directory (tenant) ID**.
3. Certificates & secrets → new client secret. Store the value in Vault at
   the path configured in `azure_ad.client_secret_vault_path`
   (key: `client_secret`) — never in `config.yaml` or the environment.
4. API permissions → Microsoft Graph → **Application** permissions, add and
   grant admin consent for:
   - `User.Read.All`
   - `Group.Read.All`
   - `Device.Read.All`
   - `Domain.Read.All`
   - `Organization.Read.All` (covers `subscribedSkus`)
   - `AuditLog.Read.All` (covers `auditLogs/directoryAudits`)

## 2. Platform API token

Store the platform ingest API token in Vault at the path configured in
`platform.api_token_vault_path` (key: `api_token`).

## 3. Vault access

Set `VAULT_TOKEN` in the environment (never commit it). `vault.addr` in
config points at the Vault instance.

## 4. Install and run

```bash
pip install -r requirements.txt
cp config/config.example.yaml config/config.yaml   # then edit config.yaml
python -m microsoft365_connector.cli --config config/config.yaml
```

Wire the CLI into whatever the squad uses to schedule connector runs, the
same way the other connectors are scheduled.

## 5. Tests (no tenant, no network needed)

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p "test_*.py" -v
# or, with requirements-dev.txt installed:
pytest
```
