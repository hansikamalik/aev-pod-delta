"""Single source of truth for demo/mock asset data.

asset_search, exposure_query and risk_score_get all read from here so an
asset ID always means the same thing. When Pod Beta's real APIs arrive,
replace this module with real lookups.
"""

from typing import Any, Dict, List, Optional

ASSETS: List[Dict[str, Any]] = [
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

# Risk factors (0-100 each) per asset ID, used by risk_score_get.
RISK_FACTORS: Dict[str, Dict[str, int]] = {
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
