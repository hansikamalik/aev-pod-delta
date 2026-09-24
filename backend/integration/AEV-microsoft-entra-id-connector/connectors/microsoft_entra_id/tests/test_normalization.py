"""Tests for Entra ID normalization (raw Graph objects -> Asset/Finding)."""
from connectors.base.models import AssetType, Severity
from connectors.microsoft_entra_id.normalization import (
    normalize_asset,
    normalize_assets,
    normalize_findings,
)


def test_normalize_asset_maps_user():
    raw = {
        "id": "u1",
        "displayName": "Alice",
        "mail": "alice@example.com",
        "accountEnabled": True,
        "_object_type": "user",
    }
    asset = normalize_asset(raw)

    assert asset.name == "Alice"
    assert asset.asset_type == AssetType.IDENTITY
    assert asset.vendor == "microsoft_entra_id"
    assert asset.external_id == "u1"
    assert asset.metadata["email"] == "alice@example.com"


def test_normalize_asset_maps_group_and_service_principal():
    group_raw = {"id": "g1", "displayName": "Admins", "securityEnabled": True, "_object_type": "group"}
    sp_raw = {"id": "sp1", "displayName": "CI", "appId": "app-1", "_object_type": "service_principal"}

    group_asset = normalize_asset(group_raw)
    sp_asset = normalize_asset(sp_raw)

    assert group_asset.metadata["security_enabled"] is True
    assert sp_asset.metadata["app_id"] == "app-1"
    assert group_asset.asset_type == AssetType.IDENTITY
    assert sp_asset.asset_type == AssetType.IDENTITY


def test_normalize_assets_handles_list():
    raw_items = [
        {"id": "u1", "displayName": "Alice", "_object_type": "user"},
        {"id": "g1", "displayName": "Admins", "_object_type": "group"},
    ]
    assets = normalize_assets(raw_items)
    assert len(assets) == 2


def test_normalize_findings_flags_disabled_user():
    raw_items = [
        {"id": "u1", "displayName": "Ghost User", "accountEnabled": False, "_object_type": "user"},
        {"id": "u2", "displayName": "Active User", "accountEnabled": True, "_object_type": "user"},
    ]
    findings = normalize_findings(raw_items)

    assert len(findings) == 1
    assert findings[0].severity == Severity.LOW
    assert findings[0].asset_external_id == "u1"
    assert "Ghost User" in findings[0].title


def test_normalize_findings_ignores_groups():
    raw_items = [{"id": "g1", "displayName": "Admins", "_object_type": "group"}]
    findings = normalize_findings(raw_items)
    assert findings == []


def test_normalize_findings_flags_disabled_service_principal():
    raw_items = [
        {"id": "sp1", "displayName": "Old App", "accountEnabled": False, "_object_type": "service_principal"}
    ]
    findings = normalize_findings(raw_items)
    assert len(findings) == 1
    assert findings[0].asset_external_id == "sp1"
