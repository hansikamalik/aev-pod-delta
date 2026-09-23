"""
Mock authenticator — for use by Subramani, Ashwin, and Bhawook so their
work never waits on the real Azure Authentication Module.

Implements the exact same AzureAuthenticator interface as
ServicePrincipalAuthenticator, so swapping mock -> real later is a
one-line change for downstream consumers.
"""

from __future__ import annotations

import time

from .auth import AzureAuthenticator
from .exceptions import CredentialValidationError, ThrottledError
from .token_manager import Token, TokenManager


class MockAzureAuthenticator(AzureAuthenticator):
    """Configurable mock. By default returns a fake valid token instantly.

    Example:
        auth = MockAzureAuthenticator()
        token = auth.get_token()  # works with no real credentials

        # Simulate a failure mode:
        auth = MockAzureAuthenticator(should_fail=True)
        auth.validate_credentials()  # raises CredentialValidationError
    """

    def __init__(
        self,
        *,
        should_fail: bool = False,
        should_throttle: bool = False,
        token_ttl_seconds: int = 3600,
        fake_token: str = "mock-access-token",
    ):
        self._should_fail = should_fail
        self._should_throttle = should_throttle
        self._token_ttl = token_ttl_seconds
        self._fake_token = fake_token
        self._token_manager = TokenManager(fetch_fn=self._fetch_fake_token)

    def get_token(self) -> Token:
        return self._token_manager.get_token()

    def validate_credentials(self) -> bool:
        if self._should_fail:
            raise CredentialValidationError("Mock: credentials rejected")
        if self._should_throttle:
            raise ThrottledError("Mock: throttled")
        self._token_manager.get_token(force_refresh=True)
        return True

    def is_authenticated(self) -> bool:
        token = self._token_manager.peek()
        return token is not None and not token.is_expired()

    def _fetch_fake_token(self) -> Token:
        if self._should_fail:
            raise CredentialValidationError("Mock: credentials rejected")
        if self._should_throttle:
            raise ThrottledError("Mock: throttled")
        return Token(
            access_token=self._fake_token,
            expires_at=time.time() + self._token_ttl,
        )
