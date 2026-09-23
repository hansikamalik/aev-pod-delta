# AEV Platform — Microsoft Entra ID Connector — Week 1 Auth Module

Week 1 Integration squad deliverable (Pod Delta M4, Sep 4–Sep 10).
Owner: **Abhiram**

Week 1 deliverable: auth module only. Full connector (discovery, normalization, push) ships in Week 2 on top of this module.

## Layout

```
connectors/
  base/            # Shared Connector ABC, models, Vault, platform push client
  microsoft_entra_id/   # This connector
sandbox/           # Mock vendor-API test server
```

## Connector contract

The connector implements the 6-method `Connector` ABC in
`connectors/base/interface.py`:

1. `authenticate()` — obtain vendor tokens / sessions
2. `health_check()` — vendor reachability + credential validity
3. `discover()` — enumerate assets
4. `ingest()` — pull findings (alerts / offenses)
5. `normalize()` — map raw vendor data to shared `Asset` / `Finding` shapes
6. `push()` — send normalized data to the Beta platform asset/exposure service

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Credentials (Vault or env)

Credentials are retrieved through HashiCorp Vault (`connectors/base/vault.py`):
path `secret/connectors/microsoft_entra_id`. Set `VAULT_ADDR` / `VAULT_TOKEN`,
or export env vars as fallback (see `connectors/microsoft_entra_id/config.example.yaml`).

## Run

```bash
python -c "from connectors.microsoft_entra_id.connector import build_from_config as b; print(b().run_sync())"
python -c "from connectors.microsoft_entra_id.connector import build_from_config as b; print(b().health_check())"
```

## Tests

```bash
pytest -q   # zero real API calls — everything is mocked
```
