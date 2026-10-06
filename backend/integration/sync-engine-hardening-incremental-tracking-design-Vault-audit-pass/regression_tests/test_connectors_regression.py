import pytest
from regression_tests.mock_platform import MockPlatformClient
from connectors import (
    AzureNormalizationPlatformPush,
    CyberArkAuthModule,
    CyberArkDiscoveryIntegration,
    ElasticConnector,
    QRadarConnector,
    SplunkConnector,
    VaultEnterpriseFramework,
)


@pytest.fixture
def platform_client():
    return MockPlatformClient()


@pytest.mark.parametrize(
    "connector_cls",
    [
        AzureNormalizationPlatformPush,
        CyberArkAuthModule,
        CyberArkDiscoveryIntegration,
        ElasticConnector,
        QRadarConnector,
        SplunkConnector,
        VaultEnterpriseFramework,
    ],
)
@pytest.mark.asyncio
async def test_all_connectors_lifecycle(connector_cls, platform_client):
    connector = connector_cls(platform_client)

    # 1. Health Check
    health = await connector.health_check()
    assert health.healthy is True
    assert health.latency_ms >= 0

    # 2. Discover
    disc = await connector.discover()
    assert isinstance(disc, list)
    assert len(disc) > 0

    # 3. Ingest
    ingested = await connector.ingest("2026-10-01T00:00:00Z")
    assert isinstance(ingested, list)
    assert len(ingested) > 0

    # 4. Sync
    result = await connector.sync()
    assert result.status in ["success", "partial_failure"]
    assert result.assets_pushed >= 0
