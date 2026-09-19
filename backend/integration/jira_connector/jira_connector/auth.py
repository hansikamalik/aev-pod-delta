"""
API-token authentication for the Jira connector.

Jira Cloud uses HTTP Basic Auth with the account email as the username
and an API token (not the account password) as the password. This is
the "Authentication module (API token)" sub-task in Week 3's Jira
connector breakdown.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass


class JiraAuthError(Exception):
    """Raised when Jira credentials are missing or malformed."""


@dataclass
class JiraTokenAuth:
    email: str
    api_token: str

    def validate(self) -> bool:
        if not self.email or "@" not in self.email:
            raise JiraAuthError("email is missing or invalid")
        if not self.api_token:
            raise JiraAuthError("api_token is missing")
        return True

    def basic_auth_header(self) -> dict[str, str]:
        """Build the Authorization header Jira's REST API expects."""
        self.validate()
        raw = f"{self.email}:{self.api_token}".encode()
        encoded = base64.b64encode(raw).decode("ascii")
        return {"Authorization": f"Basic {encoded}"}
