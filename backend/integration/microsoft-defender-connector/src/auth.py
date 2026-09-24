"""
OAuth 2.0 client-credentials authentication against Azure AD, scoped to
the Microsoft Defender for Endpoint API (FR-INT-013: Microsoft Defender
— OAuth 2.0). Depends on credentials.VaultCredentialProvider for the
client_secret.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from .config import DefenderConfig
from .credentials import VaultCredentialProvider
from .exceptions import AuthenticationError

DEFENDER_API_RESOURCE = "https://api.securitycenter.microsoft.com"


@dataclass
class AccessToken:
    value: str
    expires_at: float

    @property
    def is_expired(self) -> bool:
        # Refresh 60s before actual expiry to avoid using a stale token mid-request.
        return time.time() >= (self.expires_at - 60)


class DefenderAuthClient:
    """Acquires and caches Azure AD access tokens for the Defender API."""

    def __init__(
        self,
        config: DefenderConfig,
        credential_provider: VaultCredentialProvider,
        http_client: httpx.AsyncClient,
    ):
        self._config = config
        self._credentials = credential_provider
        self._http = http_client
        self._token: AccessToken | None = None

    async def get_token(self, *, force_refresh: bool = False) -> str:
        if not force_refresh and self._token is not None and not self._token.is_expired:
            return self._token.value

        creds = await self._credentials.get_credentials(force_refresh=force_refresh)
        token_url = f"{self._config.login_base_url}{self._config.tenant_id}/oauth2/token"

        try:
            response = await self._http.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._config.client_id,
                    "client_secret": creds.client_secret,
                    "resource": DEFENDER_API_RESOURCE,
                },
                timeout=self._config.request_timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise AuthenticationError(f"Token request failed: {exc}") from exc

        if response.status_code != 200:
            # A 401/400 here usually means a rotated/invalid secret — invalidate
            # the cached credential so the next attempt re-reads Vault.
            self._credentials.invalidate()
            raise AuthenticationError(
                f"Azure AD token endpoint returned {response.status_code}: {response.text[:300]}"
            )

        payload = response.json()
        access_token = payload.get("access_token")
        expires_in = int(payload.get("expires_in", 3600))
        if not access_token:
            raise AuthenticationError("Token response missing 'access_token'")

        self._token = AccessToken(value=access_token, expires_at=time.time() + expires_in)
        return self._token.value

    async def auth_headers(self) -> dict[str, str]:
        token = await self.get_token()
        return {"Authorization": f"Bearer {token}"}
