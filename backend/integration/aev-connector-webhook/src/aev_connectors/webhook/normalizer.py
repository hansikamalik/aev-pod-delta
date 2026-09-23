"""Map arbitrary inbound webhook payloads onto the shared Asset/Finding shapes.

Custom webhooks carry whatever the customer's system sends, so field names are
resolved through a small alias table rather than assumed.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from typing import Any

from .models import Asset, Finding, InboundEvent

_ID_KEYS = ("external_id", "id", "asset_id", "uuid", "resource_id")
_NAME_KEYS = ("name", "hostname", "display_name", "title", "resource_name")
_TYPE_KEYS = ("asset_type", "type", "kind", "resource_type")
_IP_KEYS = ("ip_addresses", "ips", "ip", "address")
_HOST_KEYS = ("hostnames", "hosts", "hostname", "fqdn")

_SEVERITY_ALIASES = {
    "crit": "critical",
    "critical": "critical",
    "sev1": "critical",
    "p1": "critical",
    "high": "high",
    "sev2": "high",
    "p2": "high",
    "med": "medium",
    "medium": "medium",
    "moderate": "medium",
    "sev3": "medium",
    "p3": "medium",
    "low": "low",
    "sev4": "low",
    "p4": "low",
    "info": "info",
    "informational": "info",
    "none": "info",
}


class NormalizationError(ValueError):
    """Raised when a payload cannot be mapped to a platform shape."""


def _first(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if v]
    return [str(value)]


def normalize_severity(value: Any) -> str:
    if value is None:
        return "info"
    return _SEVERITY_ALIASES.get(str(value).strip().lower(), "info")


def normalize_asset(payload: dict[str, Any], source: str = "webhook") -> Asset:
    external_id = _first(payload, _ID_KEYS)
    if external_id is None:
        raise NormalizationError("asset payload has no recognizable identifier")

    name = _first(payload, _NAME_KEYS) or str(external_id)
    asset_type = _first(payload, _TYPE_KEYS) or "unknown"
    tags = payload.get("tags") or {}
    if isinstance(tags, list):
        tags = {str(t): "" for t in tags}

    return Asset(
        external_id=str(external_id),
        name=str(name),
        asset_type=str(asset_type).lower(),
        source=source,
        ip_addresses=_as_list(_first(payload, _IP_KEYS)),
        hostnames=_as_list(_first(payload, _HOST_KEYS)),
        tags={str(k): str(v) for k, v in tags.items()},
        raw=payload,
    )


def normalize_finding(payload: dict[str, Any], source: str = "webhook") -> Finding:
    external_id = _first(payload, ("external_id", "id", "finding_id", "uuid"))
    if external_id is None:
        raise NormalizationError("finding payload has no recognizable identifier")

    asset_ref = _first(payload, ("asset_external_id", "asset_id", "asset", "resource_id"))
    if asset_ref is None:
        raise NormalizationError("finding payload is not linked to an asset")

    detected = payload.get("detected_at") or payload.get("timestamp")
    detected_at = datetime.now(UTC)
    if isinstance(detected, str):
        with contextlib.suppress(ValueError):
            detected_at = datetime.fromisoformat(detected.replace("Z", "+00:00"))

    return Finding(
        external_id=str(external_id),
        asset_external_id=str(asset_ref),
        title=str(_first(payload, ("title", "name", "summary")) or "Untitled finding"),
        severity=normalize_severity(payload.get("severity")),
        description=str(payload.get("description") or ""),
        source=source,
        detected_at=detected_at,
        raw=payload,
    )


def normalize_inbound(event: InboundEvent, source: str = "webhook") -> tuple[list[Asset], list[Finding]]:
    assets = [normalize_asset(a, source) for a in event.assets]
    findings = [normalize_finding(f, source) for f in event.findings]
    return assets, findings
