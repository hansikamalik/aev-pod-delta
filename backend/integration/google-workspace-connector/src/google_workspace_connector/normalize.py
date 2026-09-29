from __future__ import annotations

from typing import Any

from .models import Asset


def normalize_user(user: dict[str, Any]) -> Asset:
    """Map a Google Workspace Directory user into the shared Asset shape."""
    external_id = str(user["id"])
    name = user.get("name", {}).get("fullName") or user.get("primaryEmail") or external_id
    return Asset(
        external_id=external_id,
        name=name,
        type="google_workspace_user",
        attributes={
            "primary_email": user.get("primaryEmail"),
            "suspended": user.get("suspended", False),
            "is_admin": user.get("isAdmin", False),
            "org_unit_path": user.get("orgUnitPath"),
            "creation_time": user.get("creationTime"),
            "last_login_time": user.get("lastLoginTime"),
        },
        tags={"source": "google_workspace", "resource_type": "user"},
    )


def normalize_audit_event(event: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Reports API event while preserving the source payload."""
    actor = event.get("actor", {})
    event_id = event.get("id", {})
    return {
        "external_id": f"{event_id.get('time', '')}:{actor.get('email', '')}",
        "type": "google_workspace_audit_event",
        "timestamp": event_id.get("time"),
        "actor": actor,
        "application": event_id.get("applicationName"),
        "events": event.get("events", []),
        "source": "google_workspace",
        "raw": event,
    }
