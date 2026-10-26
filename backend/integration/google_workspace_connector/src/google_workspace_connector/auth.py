from __future__ import annotations

from typing import Any, Protocol


class GoogleWorkspaceAuthProvider(Protocol):
    """Project auth-module contract."""

    def credentials(self, config: dict[str, Any], credentials: dict[str, Any]) -> Any:
        """Return authorized Google credentials for the configured admin user."""
        ...


class AuthModuleAdapter:
    """Adapter for the project Google Workspace auth module."""

    def __init__(self, provider: GoogleWorkspaceAuthProvider):
        self._provider = provider

    def get_credentials(self, config: dict[str, Any], credentials: dict[str, Any]) -> Any:
        return self._provider.credentials(config, credentials)
