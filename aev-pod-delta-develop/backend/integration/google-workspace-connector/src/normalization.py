"""
Maps raw Google Workspace records into the shared Asset/Finding shape.

Users (from the Directory API) become Assets. Admin audit log activities
(from the Reports API) become Findings — each activity record can contain
multiple discrete events, so one activity can produce several findings.
"""

from typing import Any, Dict, List

from .base import Asset, Finding

SOURCE = "google_workspace"

# Event names that get flagged high severity rather than informational.
_HIGH_RISK_EVENTS = {
    "GRANT_ADMIN_PRIVILEGE",
    "REVOKE_ADMIN_PRIVILEGE",
    "CHANGE_PASSWORD",
    "DELETE_USER",
    "SUSPEND_USER",
    "2SV_DISABLE",
}


def normalize(raw_records: List[Dict[str, Any]]) -> List[Asset]:
    """Map raw Directory API user records into Assets."""
    assets: List[Asset] = []
    for record in raw_records:
        assets.append(
            Asset(
                external_id=record["id"],
                source=SOURCE,
                asset_type="user",
                name=record.get("primaryEmail", record["id"]),
                raw=record,
                tags=_derive_user_tags(record),
                first_seen=record.get("creationTime"),
                last_seen=record.get("lastLoginTime"),
            )
        )
    return assets


def normalize_findings(raw_activities: List[Dict[str, Any]]) -> List[Finding]:
    """Map raw Reports API activity records into Findings."""
    findings: List[Finding] = []
    for activity in raw_activities:
        activity_id = activity.get("id", {})
        actor = activity.get("actor", {})

        for event in activity.get("events", [{}]):
            event_name = event.get("name", "unknown_event")
            findings.append(
                Finding(
                    external_id=f"{activity_id.get('uniqueQualifier', '')}-{event_name}",
                    source=SOURCE,
                    severity=_severity_for_event(event_name),
                    title=event_name,
                    description=(
                        f"{actor.get('email', 'unknown actor')} triggered {event_name}"
                    ),
                    asset_external_id=actor.get("profileId"),
                    raw=activity,
                    detected_at=activity_id.get("time"),
                )
            )
    return findings


def _derive_user_tags(record: Dict[str, Any]) -> List[str]:
    tags: List[str] = []
    if record.get("isAdmin"):
        tags.append("admin")
    if record.get("suspended"):
        tags.append("suspended")
    tags.append("2sv-enrolled" if record.get("isEnrolledIn2Sv") else "2sv-not-enrolled")
    return tags


def _severity_for_event(event_name: str) -> str:
    return "high" if event_name in _HIGH_RISK_EVENTS else "informational"
