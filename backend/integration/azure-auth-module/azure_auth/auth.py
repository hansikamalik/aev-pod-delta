"""
Azure service-principal authentication.

AzureAuthenticator is the abstract interface. Publish this interface to
the team on Day 1 so:
  - Subramani (Discovery) can code against `.get_session()` / `.get_token()`
  - Ashwin (Normalization/Push) can code against `.is_authenticated()`
without waiting for ServicePrincipalAuthenticator's real implementation.
MockAzureAuthenticator (see mock_auth.py) implements the same interface.

DEPENDENCIES:
  - Needs a CredentialProvider (see credentials.py). Real Vault-backed
    provider comes from Abhiram; until then, use EnvCredentialProvider.
  - Real token acquisition requires the `azure-identity` package
    (ClientSecretCredential). If it isn't installed yet, this module
    still imports fine — the ImportError is deferred until you actually
    try to fetch a real token, so mocks are never blocked by it.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

from .credentials import AzureCredentials, CredentialProvider
from .exceptions import (
    CredentialValidationError,
    InvalidCredentialsError,
    ThrottledError,
)
from .token_manager import Token, TokenManager

MAX_VALIDATION_RETRIES = 3
BACKOFF_BASE_SECONDS = 2


class AzureAuthenticator(ABC):
    """Interface every authenticator (real or mock) implements."""

    @abstractmethod
    def get_token(self) -> Token:
        """Return a valid (non-expired) access token, refreshing if needed."""

    @abstractmethod
    def validate_credentials(self) -> bool:
        """Confirm credentials are accepted by Azure AD. Raises on failure."""

    @abstractmethod
    def is_authenticated(self) -> bool:
        """Cheap check: do we currently hold a non-expired token?"""


class ServicePrincipalAuthenticator(AzureAuthenticator):
    """Authenticates against Azure AD using a service principal
    (client ID + client secret + tenant ID).
    """

    def __init__(self, credential_provider: CredentialProvider):
        self._provider = credential_provider
        self._creds: AzureCredentials | None = None
        self._token_manager = TokenManager(fetch_fn=self._fetch_token)

    # -- public interface -------------------------------------------------

    def get_token(self) -> Token:
        return self._token_manager.get_token()

    def validate_credentials(self) -> bool:
        """Structural check, then a live check against Azure AD with retry
        + exponential backoff on throttling.
        """
        creds = self._load_credentials()

        last_error: Exception | None = None
        for attempt in range(1, MAX_VALIDATION_RETRIES + 1):
            try:
                self._token_manager.get_token(force_refresh=True)
                return True
            except ThrottledError as exc:
                last_error = exc
                if attempt < MAX_VALIDATION_RETRIES:
                    time.sleep(BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))
            except CredentialValidationError as exc:
                # Not retryable — Azure AD actively rejected these creds.
                raise exc

        raise last_error or CredentialValidationError()

    def is_authenticated(self) -> bool:
        token = self._token_manager.peek()
        return token is not None and not token.is_expired()

    # -- internals ----------------------------------------------------------

    def _load_credentials(self) -> AzureCredentials:
        if self._creds is None:
            self._creds = self._provider.get_credentials()
            self._creds.validate_shape()
        return self._creds

    def _fetch_token(self) -> Token:
        """Fetch a real token via azure-identity. Import is deferred so
        this module works even before the dependency is installed.
        """
        try:
            from azure.identity import ClientSecretCredential
            from azure.core.exceptions import ClientAuthenticationError
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "azure-identity is required for real authentication. "
                "Install it with `pip install azure-identity`, or use "
                "MockAzureAuthenticator during development."
            ) from exc

        creds = self._load_credentials()

        try:
            credential = ClientSecretCredential(
                tenant_id=creds.tenant_id,
                client_id=creds.client_id,
                client_secret=creds.client_secret,
            )
            result = credential.get_token("https://management.azure.com/.default")
            return Token(access_token=result.token, expires_at=result.expires_on)
        except ClientAuthenticationError as exc:
            message = str(exc)
            if "429" in message or "throttl" in message.lower():
                raise ThrottledError() from exc
            raise CredentialValidationError(message) from exc
        except InvalidCredentialsError:
            raise
