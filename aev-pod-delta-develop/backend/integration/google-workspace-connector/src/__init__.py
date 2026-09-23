"""Google Workspace connector: auth, discovery, normalization, and push."""

from .auth import (
    GoogleWorkspaceAuthConfig,
    GoogleWorkspaceAuthenticator,
    GoogleWorkspaceAuthError,
)
from .base import Asset, Connector, Finding, SyncResult
from .connector import GoogleWorkspaceConnector
from .credentials import (
    CredentialError,
    DEFAULT_SCOPES,
    MockVaultClient,
    VaultClientProtocol,
    load_google_workspace_credentials,
)
from .discovery import GoogleWorkspaceDiscovery
from .normalization import normalize, normalize_findings
from .push import BetaPlatformPusher

__all__ = [
    "GoogleWorkspaceConnector",
    "GoogleWorkspaceAuthenticator",
    "GoogleWorkspaceAuthError",
    "GoogleWorkspaceAuthConfig",
    "GoogleWorkspaceDiscovery",
    "BetaPlatformPusher",
    "VaultClientProtocol",
    "MockVaultClient",
    "CredentialError",
    "DEFAULT_SCOPES",
    "load_google_workspace_credentials",
    "normalize",
    "normalize_findings",
    "Asset",
    "Finding",
    "SyncResult",
    "Connector",
]
