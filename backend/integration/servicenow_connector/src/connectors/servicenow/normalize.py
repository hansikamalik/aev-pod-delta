"""Map ServiceNow records to the platform's shared Asset / Finding shape.

Shared shape (agreed with the Integration squad):

    Asset:      asset_id, name, type, ip_addresses, fqdn, os, environment,
                owner, source, first_seen, last_seen, raw
    Finding:    finding_id, asset_id, title, severity, status, description,
                source, first_seen, last_seen, raw
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


SEVERITY_MAP = {
    "1": "critical", "2": "high", "3": "medium", "4": "low", "5": "info",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _first(*vals: Optional[str]) -> Optional[str]:
    for v in vals:
        if v:
            return v
    return None


def _split_csv(value: Optional[str]) -> List[str]:
    return [v.strip() for v in (value or "").split(",") if v.strip()]


def normalize_ci(record: Dict[str, Any], source: str = "servicenow") -> Dict[str, Any]:
    """Normalize a cmdb_ci row into the shared Asset shape."""
    ip = _first(record.get("ip_address"), record.get("u_ip_address"))
    fqdn = _first(record.get("fqdn"), record.get("name"))
    return {
        "asset_id": f"servicenow:{record.get('sys_id')}",
        "name": record.get("name") or record.get("sys_id"),
        "type": (record.get("sys_class_name") or "unknown").replace("cmdb_ci_", ""),
        "ip_addresses": _split_csv(ip) if ip else [],
        "fqdn": fqdn,
        "os": record.get("os") or record.get("operating_system"),
        "environment": record.get("environment") or record.get("u_environment"),
        "owner": record.get("assigned_to") or record.get("owned_by"),
        "source": source,
        "first_seen": record.get("sys_created_on") or _utc_now(),
        "last_seen": _utc_now(),
        "raw": record,
    }


def normalize_incident(record: Dict[str, Any], source: str = "servicenow") -> Dict[str, Any]:
    """Normalize an incident (security findings) row into the Finding shape."""
    severity_raw = str(record.get("severity") or record.get("impact") or "4")
    cmdb_id = record.get("cmdb_ci")
    if isinstance(cmdb_id, dict):  # reference link excluded, but be safe
        cmdb_id = cmdb_id.get("value")
    return {
        "finding_id": f"servicenow:{record.get('sys_id')}",
        "asset_id": f"servicenow:{cmdb_id}" if cmdb_id else None,
        "title": record.get("short_description") or record.get("number") or "incident",
        "severity": SEVERITY_MAP.get(severity_raw, "info"),
        "status": (record.get("state") or "unknown").lower(),
        "description": record.get("description") or record.get("short_description") or "",
        "source": source,
        "first_seen": record.get("opened_at") or record.get("sys_created_on") or _utc_now(),
        "last_seen": record.get("sys_updated_on") or _utc_now(),
        "raw": record,
    }
