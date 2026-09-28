"""
Map raw Graph objects to the shared Asset shape (see models.py).
"""

from typing import Any, Dict, List

from .exceptions import NormalizationError
from .models import Asset, AssetStatus, AssetType, Finding

SOURCE_CONNECTOR = "microsoft_365"


def _status_from_enabled(raw: Dict[str, Any]) -> AssetStatus:
    enabled = raw.get("accountEnabled")
    if enabled is True:
        return AssetStatus.ENABLED
    if enabled is False:
        return AssetStatus.DISABLED
    return AssetStatus.UNKNOWN


def normalize_user(raw: Dict[str, Any]) -> Asset:
    try:
        return Asset(
            asset_id=raw["id"],
            asset_type=AssetType.USER,
            display_name=raw.get("displayName") or raw.get("userPrincipalName", raw["id"]),
            source_connector=SOURCE_CONNECTOR,
            status=_status_from_enabled(raw),
            owner=raw.get("userPrincipalName"),
            tags=["m365", "user"],
            metadata={
                "mail": raw.get("mail"),
                "jobTitle": raw.get("jobTitle"),
                "department": raw.get("department"),
            },
        )
    except KeyError as exc:
        raise NormalizationError(f"User object missing required field: {exc}") from exc


def normalize_group(raw: Dict[str, Any]) -> Asset:
    try:
        tags = ["m365", "group"]
        if raw.get("securityEnabled"):
            tags.append("security")
        return Asset(
            asset_id=raw["id"],
            asset_type=AssetType.GROUP,
            display_name=raw.get("displayName", raw["id"]),
            source_connector=SOURCE_CONNECTOR,
            status=AssetStatus.UNKNOWN,
            tags=tags,
            metadata={
                "mailEnabled": raw.get("mailEnabled"),
                "securityEnabled": raw.get("securityEnabled"),
                "groupTypes": raw.get("groupTypes", []),
            },
        )
    except KeyError as exc:
        raise NormalizationError(f"Group object missing required field: {exc}") from exc


def normalize_device(raw: Dict[str, Any]) -> Asset:
    try:
        owners = raw.get("registeredOwners") or []
        os_name = (raw.get("operatingSystem") or "unknown").lower()
        return Asset(
            asset_id=raw["id"],
            asset_type=AssetType.DEVICE,
            display_name=raw.get("displayName", raw["id"]),
            source_connector=SOURCE_CONNECTOR,
            status=_status_from_enabled(raw),
            owner=owners[0] if owners else None,
            tags=["m365", "device", os_name],
            metadata={
                "operatingSystem": raw.get("operatingSystem"),
                "operatingSystemVersion": raw.get("operatingSystemVersion"),
                "trustType": raw.get("trustType"),
                "isCompliant": raw.get("isCompliant"),
                "isManaged": raw.get("isManaged"),
            },
        )
    except KeyError as exc:
        raise NormalizationError(f"Device object missing required field: {exc}") from exc


def normalize_domain(raw: Dict[str, Any]) -> Asset:
    try:
        tags = ["m365", "domain"]
        if raw.get("isDefault"):
            tags.append("default")
        return Asset(
            asset_id=raw["id"],
            asset_type=AssetType.DOMAIN,
            display_name=raw["id"],
            source_connector=SOURCE_CONNECTOR,
            status=AssetStatus.ENABLED if raw.get("isVerified") else AssetStatus.UNKNOWN,
            tags=tags,
            metadata={
                "isVerified": raw.get("isVerified"),
                "isDefault": raw.get("isDefault"),
                "supportedServices": raw.get("supportedServices", []),
            },
        )
    except KeyError as exc:
        raise NormalizationError(f"Domain object missing required field: {exc}") from exc


def normalize_license(raw: Dict[str, Any]) -> Asset:
    try:
        prepaid = raw.get("prepaidUnits", {})
        return Asset(
            asset_id=raw["skuId"],
            asset_type=AssetType.LICENSE,
            display_name=raw.get("skuPartNumber", raw["skuId"]),
            source_connector=SOURCE_CONNECTOR,
            status=(
                AssetStatus.ENABLED
                if raw.get("capabilityStatus") == "Enabled"
                else AssetStatus.UNKNOWN
            ),
            tags=["m365", "license"],
            metadata={
                "consumedUnits": raw.get("consumedUnits"),
                "enabledUnits": prepaid.get("enabled"),
                "suspendedUnits": prepaid.get("suspended"),
                "capabilityStatus": raw.get("capabilityStatus"),
            },
        )
    except KeyError as exc:
        raise NormalizationError(f"License object missing required field: {exc}") from exc


def normalize_audit_log(raw: Dict[str, Any]) -> Finding:
    """
    Map a Graph API directoryAudit entry to the shared Finding shape.
    This is an event, not a persistent resource, so it comes out as a
    Finding rather than an Asset (see models.py).
    """
    try:
        initiated_by = (raw.get("initiatedBy") or {}).get("user") or {}
        targets = raw.get("targetResources") or []
        target_names = [t.get("displayName") for t in targets if t.get("displayName")]
        return Finding(
            finding_id=raw["id"],
            finding_type="audit_log",
            source_connector=SOURCE_CONNECTOR,
            activity=raw.get("activityDisplayName", raw["id"]),
            actor=initiated_by.get("userPrincipalName"),
            target=", ".join(target_names) if target_names else None,
            result=raw.get("result", "unknown"),
            occurred_at=raw.get("activityDateTime"),
            metadata={
                "category": raw.get("category"),
                "resultReason": raw.get("resultReason"),
                "operationType": raw.get("operationType"),
                "loggedByService": raw.get("loggedByService"),
                "correlationId": raw.get("correlationId"),
            },
        )
    except KeyError as exc:
        raise NormalizationError(f"Audit log object missing required field: {exc}") from exc


# Resources that come out as Findings (events) rather than Assets (resources).
FINDING_RESOURCES = {"audit_log"}

_NORMALIZERS = {
    "user": normalize_user,
    "group": normalize_group,
    "device": normalize_device,
    "domain": normalize_domain,
    "license": normalize_license,
}

_FINDING_NORMALIZERS = {
    "audit_log": normalize_audit_log,
}


def normalize(raw_by_resource: Dict[str, List[Dict[str, Any]]]) -> List[Asset]:
    """Normalize the Asset-type resources in raw_by_resource (skips finding-type ones)."""
    assets: List[Asset] = []
    for resource, raw_objects in raw_by_resource.items():
        if resource in FINDING_RESOURCES:
            continue
        normalizer = _NORMALIZERS.get(resource)
        if normalizer is None:
            raise NormalizationError(f"No normalizer registered for resource: {resource}")
        assets.extend(normalizer(raw) for raw in raw_objects)
    return assets


def normalize_findings(raw_by_resource: Dict[str, List[Dict[str, Any]]]) -> List[Finding]:
    """Normalize the finding-type resources in raw_by_resource (skips asset-type ones)."""
    findings: List[Finding] = []
    for resource, raw_objects in raw_by_resource.items():
        normalizer = _FINDING_NORMALIZERS.get(resource)
        if normalizer is None:
            continue
        findings.extend(normalizer(raw) for raw in raw_objects)
    return findings
