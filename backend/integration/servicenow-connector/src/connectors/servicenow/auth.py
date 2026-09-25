"""ServiceNow authentication: HTTP Basic and OAuth2 client-credentials."""

from __future__ import annotations

import base64
import threading
import time
from dataclasses import dataclass, field
from typing import Optional, Tuple

import requests


class ServiceNowAuthError(Exception):
    """Raised when authentication against ServiceNow fails."""


@dataclass
class TokenState:
    access_token: str = ""
    expires_at: float = 0.0
    lock: threading.Lock = field(default_factory=threading.Lock)


class ServiceNowAuth:
    """Handles auth material for a ServiceNow instance.

    Supports two methods:
      * ``basic``  - HTTP Basic auth header on every request.
      * ``oauth``  - OAuth2 token endpoint (password grant or refresh of a
                     cached token); token is cached until 60s before expiry.
    """

    TOKEN_REFRESH_SKEW_SECONDS = 60

    def __init__(
        self,
        instance_url: str,
        method: str = "basic",
        username: Optional[str] = None,
        password: Optional[str] = None,
        oauth_client_id: Optional[str] = None,
        oauth_client_secret: Optional[str] = None,
        timeout: int = 30,
        session: Optional[requests.Session] = None,
    ) -> None:
        if method not in ("basic", "oauth"):
            raise ValueError(f"unsupported auth method: {method}")
        self.instance_url = instance_url.rstrip("/")
        self.method = method
        self.username = username
        self.password = password
        self.oauth_client_id = oauth_client_id
        self.oauth_client_secret = oauth_client_secret
        self.timeout = timeout
        self.session = session or requests.Session()
        self._token = TokenState()

        if method == "basic" and not (username and password):
            raise ServiceNowAuthError("basic auth requires username and password")
        if method == "oauth" and not (username and password):
            raise ServiceNowAuthError("oauth (password grant) requires username and password")

    # ------------------------------------------------------------------ #
    def auth_headers(self) -> dict:
        """Return headers to attach to an outgoing ServiceNow request."""
        if self.method == "basic":
            raw = f"{self.username}:{self.password}".encode("utf-8")
            return {"Authorization": "Basic " + base64.b64encode(raw).decode("ascii")}
        return {"Authorization": f"Bearer {self._get_access_token()}"}

    # ------------------------------------------------------------------ #
    def _get_access_token(self) -> str:
        with self._token.lock:
            if self._token.access_token and time.time() < self._token.expires_at:
                return self._token.access_token
            return self._fetch_token()

    def _fetch_token(self) -> str:
        url = f"{self.instance_url}/oauth_token.do"
        payload = {
            "grant_type": "password",
            "client_id": self.oauth_client_id,
            "client_secret": self.oauth_client_secret,
            "username": self.username,
            "password": self.password,
        }
        resp = self.session.post(url, data=payload, timeout=self.timeout)
        if resp.status_code != 200:
            raise ServiceNowAuthError(
                f"token request failed: {resp.status_code} {resp.text[:200]}"
            )
        data = resp.json()
        token = data.get("access_token")
        if not token:
            raise ServiceNowAuthError("token response missing access_token")
        ttl = int(data.get("expires_in", 1800))
        self._token.access_token = token
        self._token.expires_at = time.time() + ttl - self.TOKEN_REFRESH_SKEW_SECONDS
        return token

    # ------------------------------------------------------------------ #
    def verify(self) -> Tuple[bool, str]:
        """Cheap liveness check: hit /api/now/table/sys_user with limit 1."""
        url = f"{self.instance_url}/api/now/table/sys_user"
        try:
            resp = self.session.get(
                url, headers=self.auth_headers(),
                params={"sysparm_limit": 1}, timeout=self.timeout,
            )
        except requests.RequestException as exc:
            return False, f"connection error: {exc}"
        if resp.status_code == 200:
            return True, "ok"
        return False, f"unexpected status {resp.status_code}"
