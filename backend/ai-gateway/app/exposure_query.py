
"""
Exposure query tool for the AI Gateway.

Provides structured exposure information with optional asset and
severity filters. The local exposure list contains demo data.
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


ALLOWED_SEVERITIES = {"low", "medium", "high", "critical"}


@register_tool("exposure_query")
def exposure_query(
    user_id: str,
    asset_id: Optional[str] = None,
    severity: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Query asset exposures with optional asset ID and severity filters.

    Args:
        user_id: ID of the user requesting exposure information.
        asset_id: Optional asset identifier, such as 'asset-001'.
        severity: Optional severity filter: low, medium, high, or critical.

    Returns:
        A dictionary containing matching exposures, count, filters,
        and citations for the returned results.

    Raises:
        TypeError: If an argument has an invalid type.
        ValueError: If a required value or filter is invalid.
    """

    # Validate the requesting user.
    if not isinstance(user_id, str):
        raise TypeError("user_id must be a string")

    user_id = user_id.strip()
    if not user_id:
        raise ValueError("user_id must be a non-empty string")

    # Validate and normalize the optional asset ID.
    if asset_id is not None:
        if not isinstance(asset_id, str):
            raise TypeError("asset_id must be a string")

        asset_id = asset_id.strip()
        if not asset_id:
            raise ValueError("asset_id cannot be empty")

    # Validate and normalize the optional severity.
    if severity is not None:
        if not isinstance(severity, str):
            raise TypeError("severity must be a string")

        severity = severity.strip().lower()
        if not severity:
            raise ValueError("severity cannot be empty")

        if severity not in ALLOWED_SEVERITIES:
            raise ValueError(
                "severity must be low, medium, high, or critical"
            )

    # Filter the exposure records.
    matches: List[Dict[str, Any]] = []

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

        # Return a copy so callers cannot modify the demo data.
        matches.append(exposure.copy())

    # Generate citations for matching exposure records.
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
