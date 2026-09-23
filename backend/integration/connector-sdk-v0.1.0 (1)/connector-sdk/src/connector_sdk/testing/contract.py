"""Shared connector contract test suite.

Contract references:
  - Section 25 (Testing Contract)
  - Section 26 (Minimum Contract Test)
  - Section 29 (PR Acceptance Criteria)

Every connector MUST pass this suite before merge. A connector author
subclasses :class:`ConnectorContractTests` and supplies a fixture::

    # connectors/azure/tests/test_contract.py
    import pytest
    from connector_sdk.testing import ConnectorContractTests
    from azure_connector import AzureConnector

    class TestAzureContract(ConnectorContractTests):
        @pytest.fixture
        def connector(self):
            return AzureConnector(
                config={"tenant_id": "t", "subscription_id": "s"},
                credentials={"client_secret": "x"},
            )

That is the whole integration. Roughly twenty assertions covering name,
discovery, asset identity and stability, ingestion, health, sync status,
and schema hygiene then run against the connector automatically.

Requires pytest. Install with ``pip install connector-sdk[test]``.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any

import pytest

from ..connector import Connector
from ..enums import AssetType, SyncStatus
from ..models import Asset, SyncResult
from ..schemas import assert_valid_schema


def run_sync(connector: Connector) -> SyncResult:
    """Execute ``connector.sync()`` from a synchronous test."""
    result = connector.sync()
    if inspect.isawaitable(result):
        return asyncio.run(result)
    return result  # type: ignore[return-value]


class ConnectorContractTests:
    """Inherit and provide a ``connector`` fixture.

    Every test here asserts a requirement stated in the contract document.
    Do not skip or override tests to make a connector pass; a failure here
    means either the connector or the contract needs to change, and the
    latter goes through the Integration Lead.
    """

    # ------------------------------------------------------------------
    # Section 4 — name
    # ------------------------------------------------------------------

    def test_is_connector_subclass(self, connector: Any) -> None:
        assert isinstance(connector, Connector), "Connector MUST extend the SDK Connector base class"

    def test_connector_name_present(self, connector: Connector) -> None:
        assert connector.name, "Connector MUST define a non-empty name"

    def test_connector_name_is_lowercase_and_stable(self, connector: Connector) -> None:
        name = connector.name
        assert name == name.lower(), "Connector name SHOULD be lowercase"
        assert " " not in name, "Connector name must not contain spaces"
        for banned in ("prod", "production", "staging", "dev", "test", "v1", "v2"):
            assert banned not in name.split("_"), (
                f"Connector name {name!r} must not embed environment or version information"
            )

    # ------------------------------------------------------------------
    # Section 10 — discover()
    # ------------------------------------------------------------------

    def test_discover_returns_iterable_of_assets(self, connector: Connector) -> None:
        assets = list(connector.discover())
        assert all(isinstance(a, Asset) for a in assets), "discover() MUST yield only Asset objects"

    def test_discovered_asset_source_matches_name(self, connector: Connector) -> None:
        for asset in connector.discover():
            assert asset.source == connector.name, (
                f"asset.source {asset.source!r} MUST equal connector.name {connector.name!r}"
            )

    def test_discovered_asset_types_are_normalized(self, connector: Connector) -> None:
        for asset in connector.discover():
            assert isinstance(asset.type, AssetType), (
                f"asset.type {asset.type!r} MUST be a normalized AssetType"
            )

    def test_discovered_assets_have_required_fields(self, connector: Connector) -> None:
        for asset in connector.discover():
            asset.validate()
            assert asset.raw is not None, "asset.raw is REQUIRED"
            assert asset.discovered_at is not None, "asset.discoveredAt is REQUIRED"

    def test_asset_ids_are_unique(self, connector: Connector) -> None:
        ids = [a.id for a in connector.discover()]
        assert len(ids) == len(set(ids)), "discover() MUST NOT emit duplicate asset IDs"

    def test_asset_ids_are_stable_across_runs(self, connector: Connector) -> None:
        """Section 6: the same source resource yields the same ID every run."""
        first = sorted(a.id for a in connector.discover())
        second = sorted(a.id for a in connector.discover())
        assert first == second, (
            "Asset IDs MUST be stable across discovery runs — do not generate random IDs"
        )

    def test_asset_ids_are_not_random(self, connector: Connector) -> None:
        import uuid

        for asset in connector.discover():
            try:
                uuid.UUID(str(asset.id))
            except (ValueError, AttributeError, TypeError):
                continue
            pytest.fail(
                f"Asset id {asset.id!r} looks like a generated UUID; use a stable "
                "source identifier or build_asset_id() (Section 6)"
            )

    def test_raw_payload_contains_no_secrets(self, connector: Connector) -> None:
        banned = ("client_secret", "api_key", "password", "private_key", "access_token")
        for asset in connector.discover():
            keys = {str(k).lower() for k in dict(asset.raw).keys()}
            leaked = keys.intersection(banned)
            assert not leaked, f"asset.raw MUST NOT contain secrets, found: {sorted(leaked)}"

    # ------------------------------------------------------------------
    # Section 11 — ingest()
    # ------------------------------------------------------------------

    def test_ingest_returns_int_count(self, connector: Connector) -> None:
        assets = list(connector.discover())
        pushed = connector.ingest(assets)
        assert isinstance(pushed, int) and not isinstance(pushed, bool), (
            "ingest() MUST return an int"
        )
        assert 0 <= pushed <= len(assets), (
            "ingest() MUST NOT report more pushed assets than it received"
        )

    def test_ingest_accepts_empty_iterable(self, connector: Connector) -> None:
        assert connector.ingest([]) == 0, "ingest([]) MUST return 0, not raise"

    # ------------------------------------------------------------------
    # Section 17 — check_health()
    # ------------------------------------------------------------------

    def test_check_health_returns_bool(self, connector: Connector) -> None:
        health = connector.check_health()
        assert isinstance(health, bool), "check_health() MUST return a bool, never raise"

    # ------------------------------------------------------------------
    # Sections 18 / 19 — schemas
    # ------------------------------------------------------------------

    def test_describe_config_schema_is_valid(self, connector: Connector) -> None:
        assert_valid_schema(connector.describe_config(), kind="config")

    def test_describe_credentials_schema_is_valid(self, connector: Connector) -> None:
        assert_valid_schema(connector.describe_credentials(), kind="credentials")

    def test_config_declares_no_secrets(self, connector: Connector) -> None:
        """Section 18: configuration MUST NOT contain credentials or secrets."""
        properties = connector.describe_config().get("properties", {})
        for name, spec in properties.items():
            assert not spec.get("secret"), (
                f"describe_config() declares secret field {name!r}; "
                "move it to describe_credentials()"
            )

    def test_credential_fields_marked_secret(self, connector: Connector) -> None:
        properties = connector.describe_credentials().get("properties", {})
        for name, spec in properties.items():
            assert spec.get("secret") is True, (
                f"credential field {name!r} MUST be marked \"secret\": True"
            )

    def test_credentials_are_redacted_when_logged(self, connector: Connector) -> None:
        for name, value in connector.safe_credentials.items():
            schema_spec = connector.describe_credentials().get("properties", {}).get(name, {})
            if schema_spec.get("secret"):
                assert value == "***REDACTED***", (
                    f"credential {name!r} MUST be redacted by safe_credentials"
                )

    # ------------------------------------------------------------------
    # Sections 13–15 — sync()
    # ------------------------------------------------------------------

    def test_sync_returns_sync_result(self, connector: Connector) -> None:
        result = run_sync(connector)
        assert isinstance(result, SyncResult), "sync() MUST return a SyncResult"

    def test_sync_result_identifies_connector(self, connector: Connector) -> None:
        result = run_sync(connector)
        assert result.connector == connector.name

    def test_sync_status_is_valid(self, connector: Connector) -> None:
        result = run_sync(connector)
        assert result.status in tuple(SyncStatus), (
            "SyncResult.status MUST be one of success, partial, failed"
        )

    def test_sync_result_counts_are_coherent(self, connector: Connector) -> None:
        result = run_sync(connector)
        assert result.assets_discovered >= 0
        assert result.assets_pushed >= 0
        assert result.assets_pushed <= result.assets_discovered, (
            "assets_pushed MUST NOT exceed assets_discovered"
        )

    def test_sync_result_has_timestamps(self, connector: Connector) -> None:
        result = run_sync(connector)
        assert result.started_at is not None, "SyncResult MUST record started_at"
        assert result.completed_at is not None, "SyncResult MUST record completed_at"
        assert result.completed_at >= result.started_at

    def test_success_status_implies_no_errors(self, connector: Connector) -> None:
        """Section 15: MUST NOT report success when assets were known to fail."""
        result = run_sync(connector)
        if result.status is SyncStatus.SUCCESS:
            assert not result.errors, "status 'success' MUST NOT be reported alongside errors"
            assert result.assets_pushed >= result.assets_discovered

    def test_sync_is_idempotent_in_asset_identity(self, connector: Connector) -> None:
        """Section 12: repeated runs identify the same resources as the same assets."""
        first = run_sync(connector)
        second = run_sync(connector)
        assert first.assets_discovered == second.assets_discovered, (
            "Repeated sync runs against unchanged source state MUST discover the same assets"
        )

    def test_sync_does_not_raise(self, connector: Connector) -> None:
        """sync() reports failure through SyncResult rather than propagating."""
        try:
            run_sync(connector)
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"sync() MUST NOT propagate exceptions, raised {type(exc).__name__}: {exc}")


__all__ = ["ConnectorContractTests", "run_sync"]
