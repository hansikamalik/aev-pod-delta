"""
Credential configuration and validation.

DEPENDENCY NOTE:
CredentialProvider is the seam where Abhiram's Secrets Vault plugs in.
Per the checklist item "no credentials hardcoded", nothing in this module
reads a client secret from a constant or config file directly — it always
goes through a CredentialProvider.

Until the real Vault module lands, use EnvCredentialProvider (reads from
environment variables) so development is never blocked on Abhiram.
Swapping in a VaultCredentialProvider later should require no changes to
auth.py or token_manager.py.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from .exceptions import InvalidCredentialsError


@dataclass(frozen=True)
class AzureCredentials:
    """Service-principal credentials for a single Azure AD tenant/app."""

    tenant_id: str
    client_id: str
    client_secret: str
    subscription_id: str = ""

    def validate_shape(self) -> None:
        """Structural validation only — does NOT call Azure AD.

        Real validation against Azure AD happens in
        ServicePrincipalAuthenticator.validate_credentials().
        """
        missing = [
            name
            for name, value in (
                ("tenant_id", self.tenant_id),
                ("client_id", self.client_id),
                ("client_secret", self.client_secret),
            )
            if not value
        ]
        if missing:
            raise InvalidCredentialsError(
                f"Missing required credential field(s): {', '.join(missing)}"
            )


class CredentialProvider(Protocol):
    """Interface for anything that can supply AzureCredentials.

    Implement this against the real Secrets Vault when Abhiram's module
    is ready. Any object with a `get_credentials()` method satisfies this
    protocol — no inheritance required.
    """

    def get_credentials(self) -> AzureCredentials:
        ...


class EnvCredentialProvider:
    """Reads credentials from environment variables.

    Default provider for local development and CI. Expects:
      AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET,
      AZURE_SUBSCRIPTION_ID (optional)
    """

    def get_credentials(self) -> AzureCredentials:
        creds = AzureCredentials(
            tenant_id=os.environ.get("AZURE_TENANT_ID", ""),
            client_id=os.environ.get("AZURE_CLIENT_ID", ""),
            client_secret=os.environ.get("AZURE_CLIENT_SECRET", ""),
            subscription_id=os.environ.get("AZURE_SUBSCRIPTION_ID", ""),
        )
        creds.validate_shape()
        return creds
