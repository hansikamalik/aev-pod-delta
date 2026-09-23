"""
Normalization: map SentinelOne agent/threat shapes to the shared
Asset/Finding shape used across all connectors.

Est: 0.5 day (per plan's per-connector standard pattern)
"""

from typing import Any, Dict, List

from .base import Asset, Finding

SOURCE = "sentinelone"

# SentinelOne threats have no severity field; confidenceLevel is the
# closest signal. NOTE: confirm this mapping with the platform team.
CONFIDENCE_TO_SEVERITY = {
    "malicious": "high",
    "suspicious": "medium",
}

MACHINE_TYPE_TO_ASSET_TYPE = {
    "server": "server",
    "desktop": "endpoint",
    "laptop": "endpoint",
    "kubernetes node": "server",
    "storage": "server",
}


def normalize_agent(agent: Dict[str, Any]) -> Asset:
    machine_type = (agent.get("machineType") or "").lower()
    tags: List[str] = []
    for key, prefix in (
        ("osType", "s1-os"),
        ("siteName", "s1-site"),
        ("groupName", "s1-group"),
        ("agentVersion", "s1-agent-version"),
    ):
        if agent.get(key):
            tags.append(f"{prefix}:{agent[key]}")
    if agent.get("infected"):
        tags.append("s1-infected")
    if agent.get("isDecommissioned"):
        tags.append("s1-decommissioned")

    return Asset(
        external_id=agent.get("id", ""),
        source=SOURCE,
        asset_type=MACHINE_TYPE_TO_ASSET_TYPE.get(machine_type, "endpoint"),
        name=agent.get("computerName") or "unnamed-agent",
        raw={k: v for k, v in agent.items() if k != "threats"},
        tags=tags,
        first_seen=agent.get("createdAt"),
        last_seen=agent.get("lastActiveDate"),
    )


def normalize_threat(threat: Dict[str, Any]) -> Finding:
    info = threat.get("threatInfo") or {}
    agent_info = threat.get("agentRealtimeInfo") or {}
    confidence = (info.get("confidenceLevel") or "").lower()

    return Finding(
        external_id=threat.get("id", ""),
        source=SOURCE,
        severity=CONFIDENCE_TO_SEVERITY.get(confidence, "low"),
        title=info.get("threatName") or "Untitled SentinelOne Threat",
        description=(
            f"{info.get('classification', 'Unknown')} - "
            f"status: {info.get('incidentStatus', 'unknown')}, "
            f"mitigation: {info.get('mitigationStatus', 'unknown')}"
        ),
        asset_external_id=agent_info.get("agentId") or None,
        raw=threat,
        detected_at=info.get("identifiedAt") or info.get("createdAt"),
    )


def normalize_findings(raw_records: List[Dict[str, Any]]) -> List[Finding]:
    return [normalize_threat(t) for r in raw_records for t in r.get("threats", [])]


def normalize(raw_records: List[Dict[str, Any]]) -> List[Asset]:
    """Connector ABC entry point: agents -> Assets (orphan-threat records skipped)."""
    return [normalize_agent(r) for r in raw_records if not r.get("_orphaned_threats")]
