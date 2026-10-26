"""Deterministic shared mock dataset for the AEV AI Context service.

Shape is deliberately provider-neutral so a future Pod Beta adapter can return
these same top-level collections. Do not put real credentials or personal data here.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

_NOW = datetime.now(timezone.utc)

MOCK_DATA = {
    "schema_version": "1.0",
    "source": "mock",
    "assets": [
        {"id": 101, "asset_name": "Finance Admin Workstation", "asset_type": "workstation", "operating_system": "Windows 11", "ip_address": "10.20.1.10", "risk_score": 9, "description": "Finance privileged workstation; simulated sensitive asset", "visibility": "admin_only", "owner_user_id": "admin", "updated_at": (_NOW - timedelta(seconds=20)).isoformat(), "embedding_updated_at": (_NOW - timedelta(seconds=8)).isoformat()},
        {"id": 102, "asset_name": "Public Web Server", "asset_type": "server", "operating_system": "Ubuntu 22.04", "ip_address": "10.20.2.20", "risk_score": 8, "description": "Internet-facing web service; simulated high risk", "visibility": "admin_only", "owner_user_id": "admin", "updated_at": (_NOW - timedelta(seconds=95)).isoformat(), "embedding_updated_at": (_NOW - timedelta(seconds=10)).isoformat()},
        {"id": 103, "asset_name": "Developer Laptop", "asset_type": "laptop", "operating_system": "Windows 11", "ip_address": "10.20.3.30", "risk_score": 5, "description": "Developer endpoint with standard access", "visibility": "admin_only", "owner_user_id": "admin", "updated_at": (_NOW - timedelta(seconds=15)).isoformat(), "embedding_updated_at": (_NOW - timedelta(seconds=12)).isoformat()},
        {"id": 104, "asset_name": "Inventory Database", "asset_type": "database", "operating_system": "PostgreSQL 16", "ip_address": "10.20.4.40", "risk_score": 7, "description": "Internal inventory database; simulated restricted record", "visibility": "admin_only", "owner_user_id": "admin", "updated_at": (_NOW - timedelta(seconds=45)).isoformat(), "embedding_updated_at": (_NOW - timedelta(seconds=30)).isoformat()},
        {"id": 105, "asset_name": "Unclassified Test Device", "asset_type": "unknown", "operating_system": None, "ip_address": None, "risk_score": None, "description": None, "visibility": "admin_only", "owner_user_id": "admin", "updated_at": None, "embedding_updated_at": None},
    ],
    "exposures": [
        {"id": "EXP-101", "asset_id": 101, "severity": "critical", "title": "Privileged workstation exposure", "status": "open", "source": "mock_inventory", "visibility": "admin_only"},
        {"id": "EXP-102", "asset_id": 102, "severity": "high", "title": "Internet-facing service review", "status": "open", "source": "mock_inventory", "visibility": "admin_only"},
        {"id": "EXP-104", "asset_id": 104, "severity": "medium", "title": "Database hardening review", "status": "in_progress", "source": "mock_inventory", "visibility": "admin_only"},
    ],
    "risk_scores": [
        {"asset_id": 101, "score": 9, "scale_min": 0, "scale_max": 10, "method": "mock_rules", "recorded_at": _NOW.isoformat()},
        {"asset_id": 102, "score": 8, "scale_min": 0, "scale_max": 10, "method": "mock_rules", "recorded_at": _NOW.isoformat()},
        {"asset_id": 103, "score": 5, "scale_min": 0, "scale_max": 10, "method": "mock_rules", "recorded_at": _NOW.isoformat()},
        {"asset_id": 104, "score": 7, "scale_min": 0, "scale_max": 10, "method": "mock_rules", "recorded_at": _NOW.isoformat()},
    ],
    "roles": [
        {"id": "role_admin", "name": "admin", "permissions": ["assets:read", "exposures:read", "risk:read", "audit:read", "integrations:read", "memory:admin"]},
        {"id": "role_analyst", "name": "analyst", "permissions": ["memory:own:read", "memory:own:write"]},
        {"id": "role_viewer", "name": "viewer", "permissions": ["memory:own:read"]},
    ],
    "users": [
        {"id": "admin", "display_name": "Mock Administrator", "role_id": "role_admin", "active": True},
        {"id": "analyst1", "display_name": "Mock Analyst One", "role_id": "role_analyst", "active": True},
        {"id": "viewer1", "display_name": "Mock Low-Privilege Viewer", "role_id": "role_viewer", "active": True},
    ],
    "audit_events": [
        {"id": "AUD-001", "actor_user_id": "viewer1", "action": "read_asset", "resource_id": "101", "outcome": "denied", "reason": "admin_only asset", "created_at": (_NOW - timedelta(minutes=3)).isoformat(), "visibility": "admin_only"},
        {"id": "AUD-002", "actor_user_id": "analyst1", "action": "read_memory", "resource_id": "analyst1", "outcome": "allowed", "reason": "own memory scope", "created_at": (_NOW - timedelta(minutes=2)).isoformat(), "visibility": "admin_only"},
        {"id": "AUD-003", "actor_user_id": "viewer1", "action": "read_exposure", "resource_id": "EXP-101", "outcome": "denied", "reason": "admin_only exposure", "created_at": (_NOW - timedelta(minutes=1)).isoformat(), "visibility": "admin_only"},
    ],
    "integrations": [
        {"id": "INT-MOCK-01", "name": "Pod Beta Inventory Adapter", "kind": "asset_inventory", "status": "mock", "configured": False, "data_contract": "pod_beta_inventory_v1"},
        {"id": "INT-MOCK-02", "name": "Exposure Feed Adapter", "kind": "exposure_feed", "status": "mock", "configured": False, "data_contract": "pod_beta_exposures_v1"},
    ],
}


def get_mock_data():
    """Return an isolated copy so a test or caller cannot mutate global fixtures."""
    return deepcopy(MOCK_DATA)


def get_mock_asset(asset_id: int):
    for asset in MOCK_DATA["assets"]:
        if asset["id"] == asset_id:
            return deepcopy(asset)
    return None
