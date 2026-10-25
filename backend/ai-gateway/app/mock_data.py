"""Single source of truth for demo/mock data (shared mock layer).

asset_search, exposure_query, risk_score_get, workflow_assist and integration_list
all read from here. When real APIs arrive, replace this module with real lookups.
"""

import json
import os
from typing import Any, Dict, List, Optional

# Default fallback data if no dataset is mounted
_DEFAULT_ASSETS: List[Dict[str, Any]] = [
    {
        "id": "asset-001",
        "name": "AI Gateway",
        "type": "service",
        "description": "FastAPI service responsible for AI Copilot requests.",
        "status": "active",
    },
    {
        "id": "asset-002",
        "name": "Redis",
        "type": "database",
        "description": "Redis instance used for request rate limiting.",
        "status": "active",
    },
    {
        "id": "asset-003",
        "name": "PostgreSQL",
        "type": "database",
        "description": "PostgreSQL database used by the platform.",
        "status": "active",
    },
]

_DEFAULT_RISK_FACTORS: Dict[str, Dict[str, int]] = {
    "asset-001": {
        "criticality": 95, "threat_intel": 80, "severity": 90,
        "age": 70, "business_impact": 90, "likelihood": 75,
    },
    "asset-002": {
        "criticality": 40, "threat_intel": 30, "severity": 35,
        "age": 50, "business_impact": 30, "likelihood": 25,
    },
    "asset-003": {
        "criticality": 85, "threat_intel": 60, "severity": 70,
        "age": 55, "business_impact": 80, "likelihood": 50,
    },
}

# Dynamic Dataset Resolution
_dataset_path = os.getenv("AEV_DATASET_PATH")
if not _dataset_path:
    _candidate = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "data", "aev_unified_handover_dataset.json"
        )
    )
    if os.path.exists(_candidate):
        _dataset_path = _candidate

_DYNAMIC_DATA: Optional[Dict[str, Any]] = None
if _dataset_path and os.path.exists(_dataset_path):
    try:
        with open(_dataset_path, "r", encoding="utf-8") as _f:
            _DYNAMIC_DATA = json.load(_f)
    except Exception:
        _DYNAMIC_DATA = None

# Initialize collections dynamically
if _DYNAMIC_DATA and "assets" in _DYNAMIC_DATA:
    ASSETS: List[Dict[str, Any]] = _DYNAMIC_DATA["assets"]
else:
    ASSETS = _DEFAULT_ASSETS

if _DYNAMIC_DATA and "risk_factor_profiles" in _DYNAMIC_DATA:
    RISK_FACTORS: Dict[str, Dict[str, int]] = _DYNAMIC_DATA["risk_factor_profiles"]
else:
    RISK_FACTORS = _DEFAULT_RISK_FACTORS

WORKFLOWS: Dict[str, Dict[str, Any]] = {
    "rotate_credentials": {
        "workflow_id": "rotate_credentials",
        "description": "Rotate credentials for a specified asset.",
        "required_params": ["asset_id"],
    },
    "isolate_host": {
        "workflow_id": "isolate_host",
        "description": "Isolate a host from the network.",
        "required_params": ["host_id"],
    },
    "rescan_asset": {
        "workflow_id": "rescan_asset",
        "description": "Run a vulnerability rescan against an asset.",
        "required_params": ["asset_id"],
    },
}

POLICY_RULES: Dict[str, Dict[str, Any]] = {
    "pol-no-public-access": {
        "resource_types": ["storage_bucket"],
        "field": "public_access",
        "expected": False,
        "description": "Storage buckets must not allow public access.",
    },
    "pol-storage-encryption": {
        "resource_types": ["storage_bucket", "database"],
        "field": "encrypted",
        "expected": True,
        "description": "Stored data must be encrypted.",
    },
    "pol-user-mfa": {
        "resource_types": ["user_account"],
        "field": "mfa_enabled",
        "expected": True,
        "description": "User accounts must have MFA enabled.",
    },
    "pol-firewall-admin-ports": {
        "resource_types": ["firewall_rule"],
        "field": "open_admin_ports",
        "expected": False,
        "description": "Administrative ports must not be openly exposed.",
    },
}

INTEGRATIONS: List[Dict[str, Any]] = [
    {"name": "Microsoft Defender", "status": "connected"},
    {"name": "GitHub", "status": "connected"},
    {"name": "Okta", "status": "error"},
    {"name": "Splunk", "status": "disconnected"},
]

MOCK_AUDIT_EVENTS: List[Dict[str, Any]] = [
    {
        "resource": "firewall",
        "actor": "hansika",
        "action": "update",
        "details": "Firewall rule updated",
        "days_ago": 2,
    },
    {
        "resource": "storage_bucket",
        "actor": "analyst01",
        "action": "policy_check",
        "details": "Storage bucket policy checked",
        "days_ago": 5,
    },
    {
        "resource": "database",
        "actor": "admin01",
        "action": "read",
        "details": "Database audit event",
        "days_ago": 9,
    },
]


def get_asset(asset_id: str) -> Optional[Dict[str, Any]]:
    """Return a copy of the asset with this ID, or None."""
    for asset in ASSETS:
        if asset["id"] == asset_id:
            return asset.copy()
    return None


def get_asset_name(asset_id: str) -> str:
    """Return the asset's name, or the ID itself if unknown."""
    asset = get_asset(asset_id)
    return asset["name"] if asset else asset_id


def get_workflows() -> Dict[str, Dict[str, Any]]:
    """Return workflows from the shared mock layer."""
    return {k: dict(v) for k, v in WORKFLOWS.items()}


def get_policy_rules() -> Dict[str, Dict[str, Any]]:
    """Return policy rules from the shared mock layer."""
    return {k: dict(v) for k, v in POLICY_RULES.items()}


def get_integrations() -> List[Dict[str, Any]]:
    """Return integrations from the shared mock layer."""
    return [dict(i) for i in INTEGRATIONS]


def get_mock_audit_events() -> List[Dict[str, Any]]:
    """Return mock audit events from the shared mock layer."""
    return [dict(e) for e in MOCK_AUDIT_EVENTS]


def get_exposures() -> List[Dict[str, Any]]:
    """Return exposures dynamically loaded from dataset or defaults."""
    if _DYNAMIC_DATA and "exposures" in _DYNAMIC_DATA:
        return [dict(e) for e in _DYNAMIC_DATA["exposures"]]
    return [
        {
            "asset_id": "asset-001",
            "asset_name": get_asset_name("asset-001"),
            "exposure": "internal",
            "risk_level": "medium",
            "status": "active",
        },
        {
            "asset_id": "asset-002",
            "asset_name": get_asset_name("asset-002"),
            "exposure": "internal",
            "risk_level": "low",
            "status": "active",
        },
        {
            "asset_id": "asset-003",
            "asset_name": get_asset_name("asset-003"),
            "exposure": "restricted",
            "risk_level": "high",
            "status": "active",
        },
    ]
