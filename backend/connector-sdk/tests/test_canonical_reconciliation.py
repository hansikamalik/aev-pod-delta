"""
Unit tests for P1-5: Canonical Connector SDK Single-Version Reconciliation.

Validates:
1. Canonical async and sync contract lifecycle (Connector & AsyncConnector).
2. Asset schema dual-casing reconciliation (discovered_at <-> discoveredAt, raw <-> raw_payload).
3. SyncResult backward and forward compatibility (records_synced, success, duration_seconds).
4. Domain exception hierarchy (ConnectorError, AuthenticationError, etc.).
5. Bidirectional lifecycle method aliasing (check_health <-> health_check, describe_config <-> get_config_schema).
6. Frozen v1.0.0 SDK version specification.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import AsyncIterable, Iterable

import pytest

import connector_sdk
from connector_sdk import (
    Asset,
    AssetType,
    AsyncConnector,
    AuthenticationError,
    ConfigurationError,
    Connector,
    ConnectorError,
    CredentialError,
    DiscoveryError,
    IngestionError,
    SampleConnector,
    SyncResult,
    SyncStatus,
    ValidationError,
)


class TestAssetAndSyncResultReconciliation:
    """Verify data models reconcile camelCase and snake_case contracts without data loss."""

    def test_asset_dual_naming_reconciliation(self):
        fixed_dt = datetime(2026, 10, 25, 12, 0, 0, tzinfo=timezone.utc)
        asset = Asset(
            id="vm-recon-101",
            source="aws",
            type=AssetType.COMPUTE,
            name="prod-gateway-instance",
            raw={"instance_type": "m5.large"},
            discovered_at=fixed_dt,
            tags={"env": "prod"},
        )

        # Attribute access
        assert asset.discovered_at == fixed_dt
        assert asset.discoveredAt == fixed_dt
        assert asset.raw_payload == {"instance_type": "m5.large"}

        # Dictionary serialization contains both keys
        d = asset.to_dict()
        assert d["discovered_at"] == fixed_dt.isoformat()
        assert d["discoveredAt"] == fixed_dt.isoformat()
        assert d["raw"] == {"instance_type": "m5.large"}
        assert d["raw_payload"] == {"instance_type": "m5.large"}

    def test_asset_from_dict_with_camel_case(self):
        payload = {
            "id": "sec-group-55",
            "source": "azure",
            "type": "network",
            "name": "default-sec-group",
            "rawPayload": {"inbound_ports": [443, 80]},
            "discoveredAt": "2026-10-25T10:15:30+00:00",
            "tags": {"tier": "dmz"},
        }

        asset = Asset.from_dict(payload)
        assert asset.id == "sec-group-55"
        assert asset.source == "azure"
        assert asset.discoveredAt.year == 2026
        assert asset.raw["inbound_ports"] == [443, 80]

    def test_sync_result_backward_and_forward_compatibility(self):
        # Initialized with legacy integration stub parameters (success, records_synced)
        start = datetime(2026, 10, 25, 12, 0, 0, tzinfo=timezone.utc)
        finish = datetime(2026, 10, 25, 12, 0, 4, tzinfo=timezone.utc)
        result = SyncResult(
            connector="okta",
            success=True,
            records_synced=42,
            started_at=start,
            finished_at=finish,
        )

        assert result.status == SyncStatus.SUCCESS
        assert result.success is True
        assert result.records_synced == 42
        assert result.assets_discovered == 42
        assert result.assets_pushed == 42
        assert result.duration_seconds == 4.0
        assert len(result.errors) == 0

        # Adding errors updates status and legacy success flag
        result.add_error("Network timeout pushing batch 2")
        assert result.status == SyncStatus.PARTIAL
        assert result.success is False
        assert len(result.errors) == 1

        d = result.to_dict()
        assert d["records_synced"] == 42
        assert d["success"] is False
        assert d["duration_seconds"] == 4.0


class TestDomainExceptionHierarchy:
    """Verify domain exception tree provides consistent structured attributes."""

    def test_exception_tree_and_attributes(self):
        err = AuthenticationError(
            message="Invalid API token for tenant 99",
            operation="authenticate",
            source="crowdstrike",
            resource_id="tenant-99",
        )

        assert isinstance(err, CredentialError)
        assert isinstance(err, ConnectorError)
        assert err.operation == "authenticate"
        assert err.source == "crowdstrike"
        assert err.resource_id == "tenant-99"
        assert "operation=authenticate" in str(err)
        assert "source=crowdstrike" in str(err)


class CustomAsyncConnector(AsyncConnector):
    """Test connector implementing the canonical asynchronous standard."""

    name = "async_test_connector"

    async def discover(self) -> AsyncIterable[Asset]:
        yield Asset(id="async-asset-1", source=self.name, type=AssetType.COMPUTE, name="Async Worker 1")
        yield Asset(id="async-asset-2", source=self.name, type=AssetType.STORAGE, name="Async Bucket 2")

    async def ingest(self, assets: Iterable[Asset]) -> int:
        return len(list(assets))

    async def check_health(self) -> bool:
        return True


class TestConnectorAsyncSyncUnification:
    """Verify connectors can execute both asynchronously and synchronously."""

    @pytest.mark.asyncio
    async def test_async_connector_primary_async_sync(self):
        connector = CustomAsyncConnector()

        # Primary canonical async execution
        result = await connector.sync()
        assert result.connector == "async_test_connector"
        assert result.status == SyncStatus.SUCCESS
        assert result.assets_discovered == 2
        assert result.assets_pushed == 2
        assert result.success is True

    def test_async_connector_sync_fallback(self):
        connector = CustomAsyncConnector()

        # Legacy synchronous fallback execution
        result = connector.sync_sync()
        assert result.status == SyncStatus.SUCCESS
        assert result.assets_discovered == 2
        assert result.assets_pushed == 2

    @pytest.mark.asyncio
    async def test_sync_connector_can_be_awaited_via_async_sync(self):
        connector = SampleConnector()

        # Synchronous connector executed in an async pipeline
        result = await connector.async_sync()
        assert result.status == SyncStatus.SUCCESS
        assert result.assets_discovered == 3
        assert result.assets_pushed == 3

    def test_lifecycle_method_aliasing(self):
        connector = SampleConnector()

        # Verify check_health <-> health_check
        assert connector.check_health() is True
        assert connector.health_check() is True

        # Verify describe_config <-> get_config_schema
        cfg1 = connector.describe_config()
        cfg2 = connector.get_config_schema()
        assert cfg1 == cfg2
        assert cfg1["type"] == "object"

        # Verify describe_credentials <-> get_credential_schema
        cred1 = connector.describe_credentials()
        cred2 = connector.get_credential_schema()
        assert cred1 == cred2
        assert "api_key" in cred1["properties"]


class TestFrozenPackageVersion:
    """Verify v1.0.0 frozen contract version."""

    def test_package_version_is_1_0_0(self):
        assert connector_sdk.__version__ == "1.0.0"
