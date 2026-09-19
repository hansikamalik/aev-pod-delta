"""
Azure Authentication & Credentials Module
Owner: Bhavesh K
Part of: Integration Squad — Azure Connector Workstream

Public interface consumed by:
  - Subramani (Azure Discovery) — needs an authenticated session/token
  - Ashwin (Azure Normalization & Push) — needs credential validation status
  - Abhiram (Secrets Vault) — supplies credentials via CredentialProvider
  - Bhawook (QA) — uses MockAzureAuthenticator for test fixtures

Downstream consumers should depend on `AzureAuthenticator` (the interface),
not on the concrete implementation, so they can swap in
`MockAzureAuthenticator` while developing without waiting on the real
Azure SDK integration.
"""

from .exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    TokenExpiredError,
    CredentialValidationError,
    ThrottledError,
)
from .credentials import AzureCredentials, CredentialProvider, EnvCredentialProvider
from .token_manager import TokenManager, Token
from .auth import AzureAuthenticator, ServicePrincipalAuthenticator
from .mock_auth import MockAzureAuthenticator

__all__ = [
    "AuthenticationError",
    "InvalidCredentialsError",
    "TokenExpiredError",
    "CredentialValidationError",
    "ThrottledError",
    "AzureCredentials",
    "CredentialProvider",
    "EnvCredentialProvider",
    "TokenManager",
    "Token",
    "AzureAuthenticator",
    "ServicePrincipalAuthenticator",
    "MockAzureAuthenticator",
]

__version__ = "0.1.0"