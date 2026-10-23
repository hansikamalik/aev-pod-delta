"""
Azure AD app-only authentication (OAuth2 client-credentials flow) against
Microsoft Graph.
"""

import time
from dataclasses import dataclass
from typing import Optional

import requests

from .exceptions import AuthenticationError


@dataclass
class GraphToken:
    access_token: str
    expires_at: float  # epoch seconds

    def is_valid(self, skew_seconds: float = 60.0) -> bool:
        return time.time() < (self.expires_at - skew_seconds)


class GraphAuthenticator:
    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        scope: str = "https://graph.microsoft.com/.default",
        token_url_template: str = (
            "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        ),
        timeout: float = 10.0,
    ):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.token_url = token_url_template.format(tenant_id=tenant_id)
        self.timeout = timeout
        self._token: Optional[GraphToken] = None

    def get_token(self) -> GraphToken:
        if self._token and self._token.is_valid():
            return self._token

        try:
            resp = requests.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": self.scope,
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise AuthenticationError(f"Graph token request failed: {exc}") from exc

        body = resp.json()
        try:
            access_token = body["access_token"]
            expires_in = float(body["expires_in"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AuthenticationError("Unexpected token response shape") from exc

        self._token = GraphToken(
            access_token=access_token,
            expires_at=time.time() + expires_in,
        )
        return self._token
