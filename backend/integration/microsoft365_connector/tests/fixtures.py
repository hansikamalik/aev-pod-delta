"""
Shared test fixtures as plain functions/data (no pytest dependency) — these
tests are written as stdlib unittest.TestCase so they run with
`python -m unittest discover` and (once installed) with pytest too.
"""

from microsoft365_connector.config import ConnectorConfig


def sample_config() -> ConnectorConfig:
    return ConnectorConfig(
        tenant_id="tenant-123",
        client_id="client-123",
        client_secret_vault_path="secret/data/aev/connectors/microsoft365/azure_ad",
        graph_api_base_url="https://graph.microsoft.com/v1.0",
        token_url_template="https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        scope="https://graph.microsoft.com/.default",
        platform_api_base_url="https://api.aev.internal",
        platform_api_token_vault_path="secret/data/aev/connectors/microsoft365/platform",
        ingest_endpoint="/api/v1/assets/ingest",
        findings_ingest_endpoint="/api/v1/findings/ingest",
        batch_size=100,
        vault_addr="https://vault.aev.internal",
        page_size=100,
        discover_resources={
            "user": True,
            "group": True,
            "device": True,
            "domain": True,
            "license": True,
            "audit_log": True,
        },
        audit_log_lookback_hours=24,
        log_level="INFO",
    )
