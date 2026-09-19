"""Tests for the reference connector, including the shared contract suite."""

import pytest

from connector_sdk import AssetType, SyncStatus
from connector_sdk.testing import ConnectorContractTests, InMemoryPlatformClient
from sample_connector import SampleConnector, SampleSourceClient


def build(**kwargs):
    reachable = kwargs.pop("reachable", True)
    resources = kwargs.pop("resources", None)
    return SampleConnector(
        config={"region": "eastus", "page_size": kwargs.pop("page_size", 50)},
        credentials={"api_key": "reference-key"},
        client=SampleSourceClient(
            api_key="reference-key", reachable=reachable, resources=resources
        ),
        platform_client=kwargs.pop("platform_client", InMemoryPlatformClient()),
        **kwargs,
    )


class TestSampleConnectorContract(ConnectorContractTests):
    @pytest.fixture
    def connector(self):
        return build()


class TestSampleBehavior:
    def test_discovers_all_fixture_resources(self):
        assert len(list(build().discover())) == 7

    def test_normalizes_types(self):
        types = {a.type for a in build().discover()}
        assert AssetType.COMPUTE in types
        assert AssetType.STORAGE in types
        assert AssetType.OTHER in types  # unknown "widget" kind

    def test_pagination_walks_every_page(self):
        connector = build(page_size=2)
        assert len(list(connector.discover())) == 7
        assert connector._client.page_requests > 1

    def test_config_flag_filters_identity_assets(self):
        connector = SampleConnector(
            config={"region": "eastus", "include_users": False},
            credentials={"api_key": "k"},
            client=SampleSourceClient(api_key="k"),
            platform_client=InMemoryPlatformClient(),
        )
        assert all(a.type is not AssetType.IDENTITY for a in connector.discover())

    def test_health_false_when_unreachable(self):
        assert build(reachable=False).check_health() is False

    def test_health_false_without_credentials(self):
        connector = SampleConnector(
            config={"region": "eastus"},
            credentials={},
            client=SampleSourceClient(api_key=None),
            platform_client=InMemoryPlatformClient(),
        )
        assert connector.check_health() is False

    def test_discovery_error_surfaces_as_failed_sync(self):
        result = build(reachable=False).sync_blocking()
        assert result.status is SyncStatus.FAILED
        assert result.errors[0]["error_type"] == "DiscoveryError"

    def test_full_sync_succeeds(self):
        platform = InMemoryPlatformClient()
        result = build(platform_client=platform).sync_blocking()
        assert result.status is SyncStatus.SUCCESS
        assert result.assets_pushed == 7
        assert platform.count == 7

    def test_batching_splits_large_pushes(self):
        resources = [
            {"id": f"r-{i}", "name": f"n-{i}", "kind": "server"} for i in range(250)
        ]
        platform = InMemoryPlatformClient()
        result = build(resources=resources, platform_client=platform).sync_blocking()
        assert result.assets_pushed == 250
        assert len(platform.upsert_calls) == 3  # 100 + 100 + 50

    def test_validate_configuration_passes(self):
        build().validate_configuration()

    def test_credentials_are_redacted(self):
        assert build().safe_credentials["api_key"] == "***REDACTED***"
