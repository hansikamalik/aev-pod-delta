
"""Role-based permissions for Copilot tools."""

from typing import Dict, Set


ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "admin": {"*"},

    "analyst": {
        "asset_search",
        "exposure_query",
        "risk_score_get",
        "policy_check",
        "integration_list",
    },

    "viewer": {
        "asset_search",
        "integration_list",
    },

    "auditor": {
        "audit_query",
    },
}


# Anonymous users cannot execute tools, regardless of requested tool.
BLOCKED_ROLES: Set[str] = {"anonymous"}


def is_allowed(role: str, tool_name: str) -> bool:
    """Return whether a role is permitted to execute a tool."""
    if role in BLOCKED_ROLES:
        return False

    allowed = ROLE_PERMISSIONS.get(role)
    if allowed is None:
        return False

    return "*" in allowed or tool_name in allowed
