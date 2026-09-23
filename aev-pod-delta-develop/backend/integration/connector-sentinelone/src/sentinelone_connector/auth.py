"""
Authentication module for SentinelOne.

SentinelOne's Management Console REST API (v2.1) authenticates with a
long-lived API token sent as:

    Authorization: ApiToken <token>

There is no OAuth exchange, so "auth" here means: build the headers,
normalise the console URL, and validate the token with a cheap
authenticated call.

Est: 1 day (per plan's per-connector standard pattern)
"""

from dataclasses import dataclass
from typing import Optional

import requests

API_PATH = "/web/api/v2.1"


@dataclass
class SentinelOneAuthConfig:
    base_url: str   # e.g. https://usea1-acme.sentinelone.net
    api_token: str

    @property
    def api_base(self) -> str:
        return self.base_url.rstrip("/") + API_PATH


class SentinelOneAuthError(Exception):
    pass


class SentinelOneAuthenticator:
    def __init__(self, config: SentinelOneAuthConfig, session: Optional[requests.Session] = None):
        self.config = config
        self._session = session or requests.Session()

    def auth_headers(self) -> dict:
        return {
            "Authorization": f"ApiToken {self.config.api_token}",
            "Content-Type": "application/json",
        }

    def validate(self) -> bool:
        """
        Cheap validation: request a single agent. 200 means the token
        is valid and has at least read access to agents. Never raises;
        returns False on any auth/network failure so health_check()
        can be used safely by monitoring.
        """
        try:
            resp = self._session.get(
                f"{self.config.api_base}/agents",
                headers=self.auth_headers(),
                params={"limit": 1},
                timeout=15,
            )
        except requests.RequestException:
            return False
        return resp.status_code == 200
