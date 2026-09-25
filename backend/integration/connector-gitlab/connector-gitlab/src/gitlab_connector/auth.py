"""
Authentication module for GitLab.

Uses a personal / group / project access token sent as the
`PRIVATE-TOKEN` header. Works against gitlab.com and self-managed GitLab
(set `api_url`; "/api/v4" is appended automatically if missing).

Est: 1 day (per plan's per-connector standard pattern)
"""

from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

import requests

DEFAULT_API_URL = "https://gitlab.com/api/v4"
API_SUFFIX = "/api/v4"


@dataclass
class GitLabAuthConfig:
    token: str
    group: str            # numeric group ID or full path, e.g. "acme" or "acme/platform"
    api_url: str = DEFAULT_API_URL

    @property
    def api_base(self) -> str:
        base = self.api_url.rstrip("/")
        return base if base.endswith(API_SUFFIX) else base + API_SUFFIX

    @property
    def group_ref(self) -> str:
        """URL-encoded group reference (paths must encode "/" as %2F)."""
        return quote(str(self.group), safe="")


class GitLabAuthError(Exception):
    pass


class GitLabAuthenticator:
    def __init__(self, config: GitLabAuthConfig, session: Optional[requests.Session] = None):
        self.config = config
        self._session = session or requests.Session()

    def auth_headers(self) -> dict:
        return {"PRIVATE-TOKEN": self.config.token, "Accept": "application/json"}

    def validate(self) -> bool:
        """
        Cheap validation: fetch the group. 200 means the token is valid and can
        see the group. Never raises; returns False on auth/network failure so
        health_check() is safe for monitoring.
        """
        try:
            resp = self._session.get(
                f"{self.config.api_base}/groups/{self.config.group_ref}",
                headers=self.auth_headers(),
                timeout=15,
            )
        except requests.RequestException:
            return False
        return resp.status_code == 200
