import pytest
from regression_tests.mock_platform import MockPlatformClient
from sync_engine.vault_audit import VaultAuditLogger, VaultAuditViolationError
from connectors import (
    AzureNormalizationPlatformPush,
    CyberArkAuthModule,
    CyberArkDiscoveryIntegration,
    ElasticConnector,
    QRadarConnector,
    SplunkConnector,
    VaultEnterpriseFramework,
)

ALL_CONNECTORS = [
    AzureNormalizationPlatformPush,
    CyberArkAuthModule,
    CyberArkDiscoveryIntegration,
    ElasticConnector,
    QRadarConnector,
    SplunkConnector,
    VaultEnterpriseFramework,
]


@pytest.fixture
def client():
    return MockPlatformClient()


@pytest.mark.parametrize("connector_cls", ALL_CONNECTORS)
@pytest.mark.asyncio
async def test_vault_audit_pass_across_connectors(connector_cls, client):
    """Verifies every connector passes Vault audit assertion during complete lifecycle execution."""
    connector = connector_cls(client)

    # 1. Health Check
    health = await connector.health_check()
    assert health.healthy is True
    assert health.vault_audit_passed is True

    # 2. Discover
    disc = await connector.discover()
    assert isinstance(disc, list)
    for item in disc:
        VaultAuditLogger.assert_vault_compliant(item)

    # 3. Ingest
    ingested = await connector.ingest("2026-10-01T00:00:00Z")
    assert isinstance(ingested, list)
    for evt in ingested:
        VaultAuditLogger.assert_vault_compliant(evt)

    # 4. Sync
    result = await connector.sync()
    assert result.vault_audit_passed is True

    # 5. Pushed Assets Check
    pushed = client.pushed_assets.get(connector.connector_id, [])
    for asset in pushed:
        VaultAuditLogger.assert_vault_compliant(asset.raw)


def test_vault_audit_violation_trigger():
    """Confirms VaultAuditViolationError triggers if raw credentials bypass sanitization."""
    dirty_payload = {"user": "admin", "token": "raw_unredacted_secret_token"}
    with pytest.raises(VaultAuditViolationError):
        VaultAuditLogger.assert_vault_compliant(dirty_payload)
