"""
Authentication module for GitHub.

Uses a token (fine-grained PAT, classic PAT, or GitHub App installation
token) sent as `Authorization: Bearer <token>`. Works against github.com
and GitHub Enterprise Server (set `api_url`).

Est: 1 day (per plan's per-connector standard pattern)
"""

from dataclasses import dataclass
from typing import Optional

import requests

DEFAULT_API_URL = "https://api.github.com"
API_VERSION = "2022-11-28"


@dataclass
class GitHubAuthConfig:
    token: str
    org: str
    api_url: str = DEFAULT_API_URL

    @property
    def api_base(self) -> str:
        return self.api_url.rstrip("/")


class GitHubAuthError(Exception):
    pass


class GitHubAuthenticator:
    def __init__(self, config: GitHubAuthConfig, session: Optional[requests.Session] = None):
        self.config = config
        self._session = session or requests.Session()

    def auth_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.config.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
        }

    def validate(self) -> bool:
        """
        Cheap validation: fetch the org. 200 means the token is valid and
        can see the org. Never raises; returns False on auth/network failure
        so health_check() is safe for monitoring.
        """
        try:
            resp = self._session.get(
                f"{self.config.api_base}/orgs/{self.config.org}",
                headers=self.auth_headers(),
                timeout=15,
            )
        except requests.RequestException:
            return False
        return resp.status_code == 200
