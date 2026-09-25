"""
Authentication module for Microsoft Sentinel.

Sentinel sits on top of Azure Log Analytics / Azure Resource Manager,
so auth is OAuth2 client-credentials against Azure AD (Entra ID),
scoped to the Log Analytics / Sentinel management API.

Est: 1 day (per plan's per-connector standard pattern)
"""

import time
from dataclasses import dataclass
from typing import Optional

import requests

AZURE_AD_TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
DEFAULT_SCOPE = "https://management.azure.com/.default"


@dataclass
class SentinelAuthConfig:
    tenant_id: str
    client_id: str
    client_secret: str
    subscription_id: str
    resource_group: str
    workspace_name: str
    scope: str = DEFAULT_SCOPE


class SentinelAuthError(Exception):
    pass


class SentinelAuthenticator:
    """
    Handles OAuth2 client-credentials flow against Azure AD and caches
    the bearer token until it's close to expiry.
    """

    def __init__(self, config: SentinelAuthConfig, session: Optional[requests.Session] = None):
        self.config = config
        self._session = session or requests.Session()
        self._token: Optional[str] = None
        self._expires_at: float = 0.0

    def get_token(self) -> str:
        if self._token and time.time() < self._expires_at - 60:
            return self._token
        return self._refresh_token()

    def _refresh_token(self) -> str:
        url = AZURE_AD_TOKEN_URL.format(tenant_id=self.config.tenant_id)
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "scope": self.config.scope,
        }
        resp = self._session.post(url, data=payload, timeout=15)
        if resp.status_code != 200:
            raise SentinelAuthError(
                f"Azure AD token request failed: {resp.status_code} {resp.text[:200]}"
            )
        data = resp.json()
        self._token = data["access_token"]
        self._expires_at = time.time() + int(data.get("expires_in", 3600))
        return self._token

    def auth_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.get_token()}",
            "Content-Type": "application/json",
        }

    def validate(self) -> bool:
        """Cheap validation: force a token fetch and confirm it's non-empty."""
        try:
            token = self.get_token()
            return bool(token)
        except SentinelAuthError:
            return False
