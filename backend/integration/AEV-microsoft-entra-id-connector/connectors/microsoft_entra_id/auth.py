"""Microsoft Entra ID authentication — OAuth2 client credentials on Microsoft Graph.

Week 1 deliverable for the Entra ID connector: the auth module, including
token caching, refresh-before-expiry, and a token-introspection helper that
Week 2's discovery code will reuse.

Credentials (Vault path secret/connectors/microsoft_entra_id or env):
  ENTRA_TENANT_ID, ENTRA_CLIENT_ID, ENTRA_CLIENT_SECRET
Optional: ENTRA_SCOPES (default: Graph .default — application permissions).
"""
from __future__ import annotations

import time

import requests

from connectors.base.vault import get_credential

AUTHORITY = "https://login.microsoftonline.com"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"


class EntraIDAuthError(RuntimeError):
    pass


class EntraIDAuth:
    def __init__(self, tenant_id: str | None = None, client_id: str | None = None,
                 client_secret: str | None = None, scopes: str | None = None,
                 session: requests.Session | None = None):
        self.tenant_id = tenant_id or get_credential("microsoft_entra_id", "tenant_id", "ENTRA")
        self.client_id = client_id or get_credential("microsoft_entra_id", "client_id", "ENTRA")
        self.client_secret = client_secret or get_credential("microsoft_entra_id", "client_secret", "ENTRA")
        self.scopes = scopes or get_credential("microsoft_entra_id", "scopes", "ENTRA", required=False) or GRAPH_SCOPE
        self.session = session or requests.Session()
        self._token: str | None = None
        self._expires_at: float = 0.0

    def token(self, force_refresh: bool = False) -> str:
        if self._token and not force_refresh and time.time() < self._expires_at - 120:
            return self._token
        url = f"{AUTHORITY}/{self.tenant_id}/oauth2/v2.0/token"
        resp = self.session.post(url, data={
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.scopes,
            "grant_type": "client_credentials",
        }, timeout=30)
        if resp.status_code != 200:
            raise EntraIDAuthError(f"Token request failed: {resp.status_code} {resp.text[:200]}")
        body = resp.json()
        self._token = body["access_token"]
        self._expires_at = time.time() + int(body.get("expires_in", 3600))
        return self._token

    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token()}"}

    def introspect(self) -> dict:
        """Lightweight check the token is usable against Graph (Week 2 uses this
        as the health-check basis)."""
        resp = self.session.get("https://graph.microsoft.com/v1.0/organization",
                                headers=self.headers(), timeout=30)
        if resp.status_code != 200:
            raise EntraIDAuthError(f"Graph introspection failed: {resp.status_code}")
        return resp.json()
