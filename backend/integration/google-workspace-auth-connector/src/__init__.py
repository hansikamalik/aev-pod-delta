"""Secure OAuth authentication for a Google Workspace security connector."""

from .connector import GOOGLE_WORKSPACE_SECURITY_SCOPES, GoogleWorkspaceAuthConnector
from .errors import OAuthError
from .models import (
    GoogleWorkspaceAuthConfig,
    GoogleWorkspaceConnection,
    OAuthStateStore,
    PendingAuthorization,
    TokenStore,
)

__all__ = [
    "GOOGLE_WORKSPACE_SECURITY_SCOPES",
    "GoogleWorkspaceAuthConnector",
    "GoogleWorkspaceAuthConfig",
    "GoogleWorkspaceConnection",
    "OAuthError",
    "OAuthStateStore",
    "PendingAuthorization",
    "TokenStore",
]
