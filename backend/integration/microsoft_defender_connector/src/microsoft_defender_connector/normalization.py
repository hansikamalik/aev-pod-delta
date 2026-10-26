"""
Normalization — maps raw Defender API payloads onto the platform's
shared Asset/finding shape (FR-INT: "Normalization: Map to the shared
Asset/finding shape").
"""

from __future__ import annotations

from .models import Asset, Finding

_SEVERITY_MAP = {
    "Informational": "info",
    "Low": "low",
    "Medium": "medium",
    "High": "high",
}


def normalize_machine(machine: dict) -> Asset:
    """Map a raw /api/machines record onto the shared Asset shape."""
    return Asset(
        external_id=machine["id"],
        name=machine.get("computerDnsName") or machine.get("id"),
        type="endpoint",
        attributes={
            "os_platform": machine.get("osPlatform"),
            "os_version": machine.get("version"),
            "health_status": machine.get("healthStatus"),
            "risk_score": machine.get("riskScore"),
            "exposure_level": machine.get("exposureLevel"),
            "last_seen": machine.get("lastSeen"),
            "ip_addresses": machine.get("ipAddresses"),
            "onboarding_status": machine.get("onboardingStatus"),
        },
        tags={
            "source": "microsoft_defender",
            "machine_group": machine.get("rbacGroupName"),
        },
    )


def normalize_alert(alert: dict) -> Finding:
    """Map a raw /api/alerts record onto the shared Finding shape."""
    return Finding(
        external_id=alert["id"],
        asset_external_id=alert.get("machineId"),
        title=alert.get("title", "Untitled Defender alert"),
        severity=_SEVERITY_MAP.get(alert.get("severity"), "unknown"),
        status=alert.get("status", "unknown"),
        category=alert.get("category", "uncategorized"),
        description=alert.get("description", ""),
        raw=alert,
    )
