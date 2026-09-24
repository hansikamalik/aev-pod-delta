"""Microsoft Entra ID normalization ΓÇö Week 2 deliverable.

Maps raw Graph objects onto the shared Asset/Finding models defined in
connectors/base/models.py. Every user/group/service principal becomes
an Asset(asset_type=IDENTITY). A small set of Findings is raised for
identity hygiene issues (disabled-but-present accounts, credential-less
service principals) ΓÇö these are illustrative, low-volume checks; deeper
risk scoring belongs to AI Context / AI Gateway, not this connector.
"""
from __future__ import annotations

from connectors.base.models import Asset, AssetType, Finding, Severity

CONNECTOR_NAME = "microsoft_entra_id"


def normalize_asset(raw: dict) -> Asset:
    """Map one raw Graph object (user, group, or service principal) to an Asset."""
    object_type = raw.get("_object_type", "unknown")
    external_id = raw.get("id", "")
    name = raw.get("displayName") or external_id or "unknown"

    metadata = {"entra_object_type": object_type}
    if object_type == "user":
        metadata.update({
            "email": raw.get("mail") or raw.get("userPrincipalName"),
            "account_enabled": raw.get("accountEnabled"),
            "user_principal_name": raw.get("userPrincipalName"),
        })
    elif object_type == "group":
        metadata.update({
            "mail_enabled": raw.get("mailEnabled"),
            "security_enabled": raw.get("securityEnabled"),
        })
    elif object_type == "service_principal":
        metadata.update({
            "app_id": raw.get("appId"),
            "account_enabled": raw.get("accountEnabled"),
            "publisher_name": raw.get("publisherName"),
        })

    return Asset(
        name=name,
        asset_type=AssetType.IDENTITY,
        vendor="microsoft_entra_id",
        external_id=external_id,
        environment="",
        owner="",
        metadata=metadata,
    )


def normalize_assets(raw_items: list[dict]) -> list[Asset]:
    return [normalize_asset(item) for item in raw_items]


def _disabled_account_finding(raw: dict) -> Finding | None:
    """Flag users/service principals that exist but are disabled ΓÇö
    stale/orphaned identities are a common audit finding."""
    object_type = raw.get("_object_type")
    if object_type not in ("user", "service_principal"):
        return None
    if raw.get("accountEnabled") is not False:
        return None

    display = raw.get("displayName") or raw.get("id")
    return Finding(
        title=f"Disabled {object_type.replace('_', ' ')} present: {display}",
        severity=Severity.LOW,
        asset_external_id=raw.get("id", ""),
        status="open",
        description=(
            f"{object_type} '{display}' is disabled in Entra ID but has not "
            f"been removed. Review for cleanup."
        ),
        source=CONNECTOR_NAME,
        external_id=raw.get("id", ""),
        remediation="Remove or archive the disabled identity if no longer needed.",
        metadata={"entra_object_type": object_type},
    )


def normalize_findings(raw_items: list[dict]) -> list[Finding]:
    """Derive findings from the same raw item set discovery already pulled."""
    findings: list[Finding] = []
    for item in raw_items:
        finding = _disabled_account_finding(item)
        if finding:
            findings.append(finding)
    return findings
