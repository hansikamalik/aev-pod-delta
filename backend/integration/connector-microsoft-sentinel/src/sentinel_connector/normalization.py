"""
Normalization: map Sentinel's incident/entity shape to the shared
Asset/Finding shape used across all connectors.

Est: 0.5 day (per plan's per-connector standard pattern)
"""

from typing import Any, Dict, List

from .base import Asset, Finding

# Sentinel severities -> shared severity vocabulary
SEVERITY_MAP = {
    "High": "high",
    "Medium": "medium",
    "Low": "low",
    "Informational": "info",
}

# Sentinel entity kinds -> shared asset_type vocabulary
ENTITY_TYPE_MAP = {
    "account": "identity",
    "host": "endpoint",
    "ip": "network_address",
    "url": "url",
    "file": "file",
    "process": "process",
}


def normalize_entities(incident: Dict[str, Any]) -> List[Asset]:
    assets: List[Asset] = []
    for entity in incident.get("entities", []):
        kind = (entity.get("kind") or "").lower()
        props = entity.get("properties", {})
        asset_type = ENTITY_TYPE_MAP.get(kind, "unknown")

        name = (
            props.get("hostName")
            or props.get("accountName")
            or props.get("address")
            or props.get("friendlyName")
            or entity.get("name")
            or "unnamed-entity"
        )

        assets.append(
            Asset(
                external_id=entity.get("name", ""),
                source="microsoft_sentinel",
                asset_type=asset_type,
                name=name,
                raw=entity,
                tags=[f"sentinel-entity-kind:{kind}"] if kind else [],
            )
        )
    return assets


def normalize_incident(incident: Dict[str, Any]) -> Finding:
    props = incident.get("properties", {})
    severity = SEVERITY_MAP.get(props.get("severity", ""), "unknown")

    return Finding(
        external_id=incident.get("name", ""),
        source="microsoft_sentinel",
        severity=severity,
        title=props.get("title", "Untitled Sentinel Incident"),
        description=props.get("description", ""),
        raw=incident,
        detected_at=props.get("createdTimeUtc"),
    )


def normalize(raw_records: List[Dict[str, Any]]) -> List[Asset]:
    """
    Public entry point matching the Connector ABC's `normalize` signature.
    Returns the flattened list of Assets derived from entities across all
    incidents. Findings are attached to the connector's own `.findings`
    buffer by the caller (see connector.py) since the shared push path
    in this codebase pattern pushes Assets; adjust here if your platform
    ingests Findings via a separate endpoint.
    """
    assets: List[Asset] = []
    for incident in raw_records:
        assets.extend(normalize_entities(incident))
    return assets
