import pytest
from regression_tests.mock_platform import MockPlatformClient
from connectors import SplunkConnector, VaultEnterpriseFramework
from sync_engine.engine import HardenedSyncEngine


@pytest.mark.asyncio
async def test_vault_and_splunk_health_and_redaction():
    client = MockPlatformClient()
    splunk = SplunkConnector(client)
    vault = VaultEnterpriseFramework(client)

    assert (await splunk.health_check()).healthy is True
    assert (await vault.health_check()).healthy is True

    secret_payload = {"api_key": "super_secret_val", "normal_data": "value"}
    asset = HardenedSyncEngine.create_asset("asset-1", secret_payload)
    assert asset.raw["api_key"] == "[REDACTED_VAULT_AUDIT]"
    assert asset.raw["normal_data"] == "value"
