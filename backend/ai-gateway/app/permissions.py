"""Role-based permissions for AI Gateway tools."""

ROLE_PERMISSIONS = {
    "admin": {"*"},
    "analyst": {
        "asset_search",
        "exposure_query",
        "risk_score_get",
        "report_generate",
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

BLOCKED_ROLES = {"anonymous"}


def is_allowed(role: str, tool_name: str) -> bool:
    """Return whether a role is allowed to use a tool."""

    if role in BLOCKED_ROLES:
        return False

    permissions = ROLE_PERMISSIONS.get(role, set())

    return "*" in permissions or tool_name in permissions
