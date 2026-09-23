"""
RBAC (role-based access control) for tool calls.

This answers one question: "is this caller allowed to use this tool?"

Real user-to-role resolution belongs to Pod Alpha's auth service. This
module deliberately does NOT try to verify who someone is -- it accepts
whatever role it's given and enforces permissions against it. That way,
when Alpha's real token verification is wired in later, only the piece
that RESOLVES a role changes -- how permissions are enforced does not.
"""

from typing import Dict, Set


class PermissionDenied(Exception):
    """Raised when a role is not allowed to call a given tool."""


# Which roles can call which tools. "*" means "every registered tool".
#
# This is intentionally simple for Week 1 -- three roles, coarse-grained
# access. As real tools and real data sensitivity get defined, this is
# expected to get more specific (e.g. per-org scoping), not just
# per-role.
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "admin": {"*"},
    "analyst": {"asset_search", "exposure_query", "risk_score_get"},
    "viewer": {"asset_search"},
}

# The anonymous/default caller must never be able to use tools that
# touch real security data. A tool call has to be attributed to a real,
# identified role -- "no cross-tenant leakage" starts with "no
# unidentified caller gets data at all."
BLOCKED_ROLES: Set[str] = {"anonymous"}


def is_allowed(role: str, tool_name: str) -> bool:
    """Return True when `role` is permitted to call `tool_name`."""

    if role in BLOCKED_ROLES:
        return False

    allowed = ROLE_PERMISSIONS.get(role)
    if allowed is None:
        # Unknown role: fail closed, not open.
        return False

    return "*" in allowed or tool_name in allowed
