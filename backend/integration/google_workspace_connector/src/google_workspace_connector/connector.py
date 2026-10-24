from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from .auth import AuthModuleAdapter, GoogleWorkspaceAuthProvider
from .clients import GoogleWorkspaceClients
from .models import Asset, SyncResult
from .normalize import normalize_audit_event, normalize_user
from .schemas import CONFIG_SCHEMA, CREDENTIAL_SCHEMA
from .state import InMemorySyncStateStore, SyncStateStore


class GoogleWorkspaceConnector:
    """AEV Platform Google Workspace connector.

    Authentication is delegated to the project Google Workspace auth module.
    This class owns source-specific discovery, ingestion, normalization,
    health checks, and sync-state orchestration.
    """

    STATE_USERS = "google_workspace.users.last_sync_at"
    STATE_AUDIT = "google_workspace.audit.last_sync_at"

    def __init__(
        self,
        auth_provider: GoogleWorkspaceAuthProvider,
        state_store: SyncStateStore | None = None,
        client_factory=GoogleWorkspaceClients,
    ) -> None:
        self._auth = AuthModuleAdapter(auth_provider)
        self._state = state_store or InMemorySyncStateStore()
        self._client_factory = client_factory

    def _clients(
        self, config: dict[str, Any], credentials: dict[str, Any]
    ) -> GoogleWorkspaceClients:
        authorized = self._auth.get_credentials(config, credentials)
        return self._client_factory(authorized)

    async def discover(self, config: dict[str, Any]) -> AsyncIterator[Asset]:
        credentials = config["_credentials"]
        clients = self._clients(config, credentials)
        page_token = None
        sync = config.get("sync", {})
        page_size = sync.get("page_size", 100)

        while True:
            response = (
                clients.directory.users()
                .list(
                    customer=config["customer_id"],
                    maxResults=page_size,
                    orderBy="email",
                    pageToken=page_token,
                    projection="full",
                )
                .execute()
            )

            for user in response.get("users", []):
                yield normalize_user(user)

            page_token = response.get("nextPageToken")
            if not page_token:
                break

    async def ingest(self, config: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        credentials = config["_credentials"]
        clients = self._clients(config, credentials)
        sync = config.get("sync", {})
        if not sync.get("audit_logs", True):
            return

        start_time = await self._state.get(self.STATE_AUDIT) or "1970-01-01T00:00:00Z"
        application = sync.get("audit_application", "login")
        page_token = None

        while True:
            response = (
                clients.reports.activities()
                .list(
                    userKey="all",
                    applicationName=application,
                    startTime=start_time,
                    pageToken=page_token,
                )
                .execute()
            )

            for event in response.get("items", []):
                yield normalize_audit_event(event)

            page_token = response.get("nextPageToken")
            if not page_token:
                break

    async def sync(self, config: dict[str, Any], direction: str) -> SyncResult:
        if direction not in {"pull", "source_to_platform"}:
            return SyncResult(0, 0, 0, 0, f"Unsupported direction: {direction}")

        processed = created = updated = failed = 0
        error = None

        try:
            if config.get("sync", {}).get("users", True):
                async for _asset in self.discover(config):
                    processed += 1
                await self._state.set(self.STATE_USERS, datetime.now(UTC).isoformat())

            if config.get("sync", {}).get("audit_logs", True):
                async for _event in self.ingest(config):
                    processed += 1
                await self._state.set(self.STATE_AUDIT, datetime.now(UTC).isoformat())
        except Exception as exc:  # noqa: BLE001 - connector boundary
            failed += 1
            error = str(exc)

        return SyncResult(processed, created, updated, failed, error)

    async def health_check(self, config: dict[str, Any]) -> dict[str, Any]:
        try:
            clients = self._clients(config, config["_credentials"])
            clients.directory.users().list(customer=config["customer_id"], maxResults=1).execute()
            return {
                "healthy": True,
                "authenticated": True,
                "source": "google_workspace",
            }
        except Exception as exc:  # noqa: BLE001 - health boundary
            return {
                "healthy": False,
                "authenticated": False,
                "source": "google_workspace",
                "error": str(exc),
            }

    def config_schema(self) -> dict[str, Any]:
        return CONFIG_SCHEMA

    def credential_schema(self) -> dict[str, Any]:
        return CREDENTIAL_SCHEMA
