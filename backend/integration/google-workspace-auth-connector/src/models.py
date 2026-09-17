from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PendingAuthorization:
    state: str
    code_verifier: str
    nonce: str
    session_id: str
    created_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class GoogleWorkspaceConnection:
    connection_id: str
    access_token: str
    refresh_token: str | None
    expires_at: datetime
    scope: tuple[str, ...]
    created_at: datetime
    updated_at: datetime
    google_subject: str | None = None
    workspace_domain: str | None = None


@dataclass(frozen=True, slots=True)
class GoogleWorkspaceAuthConfig:
    client_id: str
    client_secret: str
    redirect_uri: str
    allowed_workspace_domains: frozenset[str] = frozenset()
    authorization_ttl_seconds: int = 600


class OAuthStateStore(Protocol):
    def put(self, authorization: PendingAuthorization) -> None:
        """Persist a short-lived authorization attempt."""

    def consume(self, state: str) -> PendingAuthorization | None:
        """Atomically return and delete state, preventing replay."""


class TokenStore(Protocol):
    """Implement with envelope encryption and tenant-level access controls."""

    def save(self, connection: GoogleWorkspaceConnection) -> None: ...

    def get(self, connection_id: str) -> GoogleWorkspaceConnection | None: ...

    def delete(self, connection_id: str) -> None: ...
