"""
Exposure query tool for the AI Gateway.

Provides a structured interface for querying asset exposure information.
"""


from typing import Any, Dict, List


EXPOSURES: List[Dict[str, Any]] = [
    {
        "asset_id": "asset-001",
        "asset_name": "AI Gateway",
        "exposure": "internal",
        "risk_level": "medium",
        "status": "active",
    },
    {
        "asset_id": "asset-002",
        "asset_name": "Redis",
        "exposure": "internal",
        "risk_level": "low",
        "status": "active",
    },
    {
        "asset_id": "asset-003",
        "asset_name": "PostgreSQL",
        "exposure": "restricted",
        "risk_level": "high",
        "status": "active",
    },
]


def exposure_query(
    asset_id: str,
) -> Dict[str, Any]:
    """
    Query exposure information for an asset.

    Args:
        asset_id: Unique identifier of the asset.

    Returns:
        Structured exposure information.
    """
    if not isinstance(asset_id, str):
        raise TypeError("asset_id must be a string")

    asset_id = asset_id.strip()

    if not asset_id:
        raise ValueError("asset_id cannot be empty")

    matches = [
        exposure.copy()
        for exposure in EXPOSURES
        if exposure["asset_id"].lower() == asset_id.lower()
    ]

    return {
        "tool": "exposure_query",
        "asset_id": asset_id,
        "results": matches,
        "count": len(matches),
    }