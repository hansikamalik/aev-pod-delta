"""
Mock tool implementations for the demo phase.

These return fake-but-realistic data so the full Gateway flow (RBAC ->
dispatch -> citation -> audit log) can be shown end to end. When Pod
Beta's Risk API is available, only the body of each function changes to
an HTTP call -- the registration, arguments and return shape stay.
"""

from typing import Any, Dict

from app.tools import register_tool

# Same 6 factors and weights as Pod Beta's proposal (must sum to 100).
_WEIGHTS = {
    "criticality": 25,
    "threat_intel": 20,
    "severity": 20,
    "age": 10,
    "business_impact": 15,
    "likelihood": 10,
}

# Each factor is scored 0-100 per asset.
_MOCK_ASSETS: Dict[str, Dict[str, Any]] = {
    "asset-001": {
        "name": "prod-db-01",
        "factors": {
            "criticality": 95, "threat_intel": 80, "severity": 90,
            "age": 70, "business_impact": 90, "likelihood": 75,
        },
    },
    "asset-002": {
        "name": "hr-laptop-14",
        "factors": {
            "criticality": 40, "threat_intel": 30, "severity": 35,
            "age": 50, "business_impact": 30, "likelihood": 25,
        },
    },
}


def _band(score: int) -> str:
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 30:
        return "Medium"
    return "Low"


@register_tool("risk_score_get")
def risk_score_get(asset_id: str, user_id: str) -> Dict[str, Any]:
    """Return a mock risk score, band and per-factor breakdown."""

    asset = _MOCK_ASSETS.get(asset_id)
    if asset is None:
        raise ValueError(f"Asset '{asset_id}' not found")

    breakdown = {
        name: {
            "value": asset["factors"][name],
            "weight_percent": weight,
        }
        for name, weight in _WEIGHTS.items()
    }
    score = round(
        sum(asset["factors"][n] * w for n, w in _WEIGHTS.items()) / 100
    )

    return {
        "asset_id": asset_id,
        "asset_name": asset["name"],
        "score": score,
        "band": _band(score),
        "confidence": 0.9,
        "breakdown": breakdown,
        "citation": {
            "id": f"cit-risk-{asset_id}",
            "type": "risk_score",
            "id_ref": asset_id,
            "url": f"/risk/{asset_id}",
        },
    }
