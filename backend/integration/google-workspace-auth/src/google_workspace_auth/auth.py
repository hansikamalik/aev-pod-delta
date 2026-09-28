from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

import jwt
import requests

from .exceptions import AuthenticationError, ConfigurationError


DEFAULT_TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_SCOPE = "https://www.googleapis.com/auth/admin.directory.user.readonly"


@dataclass(frozen=True)
class GoogleToken:
    """An OAuth access token returned by Google."""

    access_token: str
    expires_at: float
    token_type: str = "Bearer"

    def is_valid(self, clock_skew_seconds: int = 60) -> bool:
        return time.time() < (self.expires_at - clock_skew_seconds)


class GoogleWorkspaceAuthenticator:
    """Obtain Google OAuth 2.0 tokens using service-account DWD."""

    def __init__(
        self,
        client_email: str,
        private_key: str,
        delegated_subject: str,
        scopes: Iterable[str] | None = None,
        token_url: str = DEFAULT_TOKEN_URL,
        timeout_seconds: float = 15.0,
        clock_skew_seconds: int = 60,
        http_post: Optional[Callable[..., requests.Response]] = None,
    ) -> None:
        if not client_email:
            raise ConfigurationError("client_email is required")
        if not private_key:
            raise ConfigurationError("private_key is required")
        if not delegated_subject:
            raise ConfigurationError("delegated_subject is required")

        self.client_email = client_email
        self.private_key = private_key
        self.delegated_subject = delegated_subject
        self.scopes = tuple(scopes or (DEFAULT_SCOPE,))
        self.token_url = token_url
        self.timeout_seconds = timeout_seconds
        self.clock_skew_seconds = clock_skew_seconds
        self._http_post = http_post or requests.post
        self._token: GoogleToken | None = None

    def _build_assertion(self) -> str:
        now = int(time.time())
        claims = {
            "iss": self.client_email,
            "scope": " ".join(self.scopes),
            "aud": self.token_url,
            "iat": now,
            "exp": now + 3600,
            "sub": self.delegated_subject,
        }
        try:
            return jwt.encode(claims, self.private_key, algorithm="RS256")
        except Exception as exc:
            raise AuthenticationError("Unable to create Google JWT assertion") from exc

    def get_token(self) -> GoogleToken:
        """Return a cached valid token or obtain a new one."""
        if self._token and self._token.is_valid(self.clock_skew_seconds):
            return self._token

        assertion = self._build_assertion()
        payload = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        }

        try:
            response = self._http_post(
                self.token_url,
                data=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            raise AuthenticationError("Google token request failed") from exc
        except ValueError as exc:
            raise AuthenticationError("Google returned invalid JSON") from exc

        access_token = data.get("access_token")
        expires_in = data.get("expires_in")

        if not access_token or not isinstance(expires_in, (int, float)):
            raise AuthenticationError("Google token response is missing required fields")
        if expires_in <= 0:
            raise AuthenticationError("Google returned an invalid token lifetime")

        self._token = GoogleToken(
            access_token=access_token,
            expires_at=time.time() + float(expires_in),
            token_type=data.get("token_type", "Bearer"),
        )
        return self._token

    def invalidate(self) -> None:
        self._token = None

    def authorization_header(self) -> dict[str, str]:
        token = self.get_token()
        return {"Authorization": f"{token.token_type} {token.access_token}"}
