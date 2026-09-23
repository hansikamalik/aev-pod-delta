"""Google Workspace connector — Week 1 scope: auth module only."""

from .auth import (
    GoogleWorkspaceAuthConfig,
    GoogleWorkspaceAuthenticator,
    GoogleWorkspaceAuthError,
)
from .credentials import (
    CredentialError,
    DEFAULT_SCOPES,
    MockVaultClient,
    VaultClientProtocol,
    load_google_workspace_credentials,
)

__all__ = [
    "GoogleWorkspaceAuthenticator",
    "GoogleWorkspaceAuthError",
    "GoogleWorkspaceAuthConfig",
    "VaultClientProtocol",
    "MockVaultClient",
    "CredentialError",
    "DEFAULT_SCOPES",
    "load_google_workspace_credentials",
]
