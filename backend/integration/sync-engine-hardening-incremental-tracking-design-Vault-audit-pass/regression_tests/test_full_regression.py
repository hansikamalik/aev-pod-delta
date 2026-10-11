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


@pytest.mark.asyncio
async def test_azure_normalization_platform_push_failure_recovery():
    client = MockPlatformClient()
    azure = AzureNormalizationPlatformPush(client)

    azure.simulate_partial_failure = True
    result_fail = await azure.sync()
    assert result_fail.status == "partial_failure"

    azure.simulate_partial_failure = False
    result_pass = await azure.sync()
    assert result_pass.status == "success"


@pytest.mark.asyncio
async def test_full_system_regression_sweep():
    client = MockPlatformClient()
    connectors = [
        AzureNormalizationPlatformPush(client),
        CyberArkAuthModule(client),
        CyberArkDiscoveryIntegration(client),
        ElasticConnector(client),
        QRadarConnector(client),
        SplunkConnector(client),
        VaultEnterpriseFramework(client),
    ]

    for conn in connectors:
        health = await conn.health_check()
        assert health.healthy is True
        sync_res = await conn.sync()
        assert sync_res.status == "success"
