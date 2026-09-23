"""Tests for Asset / SyncResult models (contract Sections 5-9, 14-15)."""

from datetime import datetime, timezone

import pytest

from connector_sdk import (
    Asset,
    AssetType,
    SyncResult,
    SyncStatus,
    ValidationError,
    build_asset_id,
)


def make_asset(**overrides):
    payload = {
        "id": "vm-1",
        "source": "fake",
        "type": AssetType.COMPUTE,
        "name": "host-1",
        "raw": {"id": "vm-1"},
    }
    payload.update(overrides)
    return Asset(**payload)


class TestAsset:
    def test_minimal_asset_is_valid(self):
        asset = make_asset()
        assert asset.id == "vm-1"
        assert asset.type is AssetType.COMPUTE

    def test_string_type_is_coerced_to_enum(self):
        assert make_asset(type="storage").type is AssetType.STORAGE

    def test_unknown_type_is_rejected(self):
        with pytest.raises(ValidationError, match="Unknown asset type"):
            make_asset(type="quantum_computer")

    @pytest.mark.parametrize("missing", ["id", "source", "name"])
    def test_required_string_fields(self, missing):
        with pytest.raises(ValidationError):
            make_asset(**{missing: ""})

    def test_discovered_at_defaults_to_aware_utc(self):
        assert make_asset().discovered_at.tzinfo is not None

    def test_naive_datetime_is_assumed_utc(self):
        asset = make_asset(discovered_at=datetime(2026, 1, 1, 12, 0, 0))
        assert asset.discovered_at.tzinfo == timezone.utc

    def test_to_dict_uses_contract_field_names(self):
        payload = make_asset().to_dict()
        assert payload["discoveredAt"]
        assert payload["type"] == "compute"
        assert set(payload) == {"id", "source", "type", "name", "raw", "discoveredAt", "tags"}


class TestBuildAssetId:
    def test_is_deterministic(self):
        assert build_asset_id("azure", "vm", "abc") == build_asset_id("azure", "vm", "abc")

    def test_format(self):
        assert build_asset_id("azure", "vm", "abc") == "azure:vm:abc"

    @pytest.mark.parametrize("args", [("", "vm", "a"), ("azure", "", "a"), ("azure", "vm", "")])
    def test_rejects_empty_parts(self, args):
        with pytest.raises(ValidationError):
            build_asset_id(*args)


class TestSyncResult:
    def test_status_string_is_coerced(self):
        assert SyncResult(connector="fake", status="success").status is SyncStatus.SUCCESS

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            SyncResult(connector="fake", status="mostly_fine")

    @pytest.mark.parametrize(
        "discovered,pushed,errors,expected",
        [
            (100, 100, [], SyncStatus.SUCCESS),
            (100, 97, ["e"], SyncStatus.PARTIAL),
            (100, 97, [], SyncStatus.PARTIAL),
            (100, 0, ["e"], SyncStatus.FAILED),
            (0, 0, ["e"], SyncStatus.FAILED),
            (0, 0, [], SyncStatus.SUCCESS),
        ],
    )
    def test_derive_status(self, discovered, pushed, errors, expected):
        assert (
            SyncResult.derive_status(discovered=discovered, pushed=pushed, errors=errors)
            == expected
        )

    def test_duration_is_none_until_completed(self):
        assert SyncResult(connector="fake", status="success").duration_seconds is None

    def test_add_error_accepts_multiple_shapes(self):
        result = SyncResult(connector="fake", status="failed")
        result.add_error("plain message")
        result.add_error({"message": "mapping"})
        assert len(result.errors) == 2
        assert all("message" in e for e in result.errors)
