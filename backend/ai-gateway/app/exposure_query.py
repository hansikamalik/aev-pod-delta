
"""
Exposure query tool for the AI Gateway.

Provides structured exposure information with optional
asset and severity filters.
The local exposure list is demo data.
"""

from typing import Any, Dict, List, Optional

from app.tools import register_tool


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


@register_tool("exposure_query")
def exposure_query(
    user_id: str,
    asset_id: Optional[str] = None,
    severity: Optional[str] = None,
) -> Dict[str, Any]:
    """Query exposures, optionally filtering by asset and severity."""

    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id must be a non-empty string")

    if asset_id is not None:
        if not isinstance(asset_id, str):
            raise TypeError("asset_id must be a string")

        asset_id = asset_id.strip()

        if not asset_id:
            raise ValueError("asset_id cannot be empty")

    allowed_severities = {"low", "medium", "high", "critical"}

    if severity is not None:
        if not isinstance(severity, str):
            raise TypeError("severity must be a string")

        severity = severity.strip().lower()

        if severity not in allowed_severities:
            raise ValueError(
                "severity must be low, medium, high, or critical"
            )

    matches = []

    for exposure in EXPOSURES:
        if (
            asset_id is not None
            and exposure["asset_id"].lower() != asset_id.lower()
        ):
            continue

        if (
            severity is not None
            and exposure["risk_level"].lower() != severity
        ):
            continue

        matches.append(exposure.copy())

    citations = [
        {
            "id": f"cit-exposure-{item['asset_id']}",
            "type": "exposure",
            "id_ref": item["asset_id"],
            "url": f"/exposures/{item['asset_id']}",
        }
        for item in matches
    ]

    return {
        "tool": "exposure_query",
        "asset_id": asset_id,
        "severity": severity,
        "results": matches,
        "count": len(matches),
        "citations": citations,
    }
