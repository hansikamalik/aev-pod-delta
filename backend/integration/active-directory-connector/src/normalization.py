"""
Normalization — maps raw LDAP entries onto the platform's shared Asset
shape (FR-INT: "Normalization: Map to the shared Asset/finding shape").
"""

from __future__ import annotations

from .models import Asset

_UAC_ACCOUNTDISABLE = 0x0002


def _first(value):
    """LDAP attributes may come back as a single value or a list,
    depending on whether the schema marks them single- or multi-valued."""
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_user(entry: dict) -> Asset:
    """Map a raw LDAP user entry onto the shared Asset shape."""
    attrs = entry.get("attributes", {})
    dn = entry.get("dn") or _first(attrs.get("distinguishedName"))
    object_guid = _first(attrs.get("objectGUID"))
    sam_account_name = _first(attrs.get("sAMAccountName"))
    uac_raw = _first(attrs.get("userAccountControl"))

    enabled = True
    if uac_raw is not None:
        try:
            enabled = not (int(uac_raw) & _UAC_ACCOUNTDISABLE)
        except (TypeError, ValueError):
            enabled = True

    return Asset(
        external_id=str(object_guid or dn),
        name=sam_account_name or dn,
        type="ad_user",
        attributes={
            "distinguished_name": dn,
            "display_name": _first(attrs.get("displayName")),
            "email": _first(attrs.get("mail")),
            "enabled": enabled,
            "member_of": _as_list(attrs.get("memberOf")),
            "when_changed": _first(attrs.get("whenChanged")),
        },
        tags={"source": "active_directory", "object_class": "user"},
    )


def normalize_group(entry: dict) -> Asset:
    """Map a raw LDAP group entry onto the shared Asset shape."""
    attrs = entry.get("attributes", {})
    dn = entry.get("dn") or _first(attrs.get("distinguishedName"))
    object_guid = _first(attrs.get("objectGUID"))
    cn = _first(attrs.get("cn"))
    members = _as_list(attrs.get("member"))

    return Asset(
        external_id=str(object_guid or dn),
        name=cn or dn,
        type="ad_group",
        attributes={
            "distinguished_name": dn,
            "group_type": _first(attrs.get("groupType")),
            "member_count": len(members),
            "members": members,
            "when_changed": _first(attrs.get("whenChanged")),
        },
        tags={"source": "active_directory", "object_class": "group"},
    )
