"""
ActiveDirectoryConnector — full implementation of the platform
Connector interface for on-prem Active Directory (FR-INT-010).

Wires together: auth (LDAP simple bind) -> credentials (Vault) ->
discovery (paged LDAP search over users/groups) -> normalization
(shared Asset shape) -> push (Beta's asset service).
"""

from __future__ import annotations

from typing import AsyncIterator

import httpx

from .auth import ADAuthClient
from .config import ActiveDirectoryConfig
from .credentials import VaultClient, VaultCredentialProvider
from .discovery import iter_groups, iter_users
from .exceptions import LDAPBindError, LDAPSearchError, PushError, VaultAccessError
from .models import Asset, SyncResult
from .normalization import normalize_group, normalize_user
from .push import PlatformPushClient
from .schemas import CONFIG_SCHEMA, CREDENTIAL_SCHEMA
from .sdk_interface import Connector


class ActiveDirectoryConnector(Connector):
    def __init__(
        self,
        integration_id: str,
        credentials_ref: str,
        vault_client: VaultClient,
        asset_ingest_url: str,
        http_client: httpx.AsyncClient | None = None,
        ldap_client_strategy: str | None = None,
    ):
        self._integration_id = integration_id
        self._credential_provider = VaultCredentialProvider(vault_client, credentials_ref)
        self._http = http_client or httpx.AsyncClient()
        self._owns_http_client = http_client is None
        self._asset_ingest_url = asset_ingest_url
        # Only ever set in tests, to swap in ldap3's in-memory MOCK_SYNC strategy.
        self._ldap_client_strategy = ldap_client_strategy

    async def aclose(self) -> None:
        if self._owns_http_client:
            await self._http.aclose()

    # -- Connector interface -------------------------------------------------

    async def discover(self, config: dict) -> AsyncIterator[Asset]:
        cfg = ActiveDirectoryConfig(**config)
        auth = ADAuthClient(cfg, self._credential_provider, client_strategy=self._ldap_client_strategy)

        async for entry in iter_users(cfg, auth):
            yield normalize_user(entry)

        if cfg.sync_groups:
            async for entry in iter_groups(cfg, auth):
                yield normalize_group(entry)

    async def ingest(self, config: dict) -> AsyncIterator[dict]:
        """Active Directory has no separate alert/finding stream (unlike
        e.g. Microsoft Defender), so this intentionally yields nothing.
        User/group data is fully covered by discover(). This method
        exists only to satisfy the Connector interface contract.
        """
        return
        yield  # pragma: no cover - makes this an async generator

    async def sync(self, config: dict, direction: str = "pull") -> SyncResult:
        if direction != "pull":
            return SyncResult(
                records_processed=0,
                records_created=0,
                records_updated=0,
                records_failed=0,
                error=f"Active Directory connector only supports 'pull' sync, got '{direction}'",
            )

        cfg = ActiveDirectoryConfig(**config)
        pusher = PlatformPushClient(
            http_client=self._http,
            integration_id=self._integration_id,
            asset_ingest_url=self._asset_ingest_url,
            request_timeout_seconds=cfg.receive_timeout_seconds,
        )

        processed = created = failed = 0
        error: str | None = None

        try:
            async for asset in self.discover(config):
                processed += 1
                try:
                    await pusher.push_asset(asset)
                    created += 1
                except PushError:
                    failed += 1
        except (LDAPBindError, VaultAccessError, LDAPSearchError) as exc:
            error = str(exc)

        return SyncResult(
            records_processed=processed,
            records_created=created,
            records_updated=0,
            records_failed=failed,
            error=error,
        )

    async def health_check(self, config: dict) -> dict:
        cfg = ActiveDirectoryConfig(**config)
        auth = ADAuthClient(cfg, self._credential_provider, client_strategy=self._ldap_client_strategy)

        try:
            connection = await auth.get_connection(force_rebind=True)
        except VaultAccessError as exc:
            return {"healthy": False, "reason": "vault_unreachable", "detail": str(exc)}
        except LDAPBindError as exc:
            return {"healthy": False, "reason": "bind_failed", "detail": str(exc)}

        if not connection.bound:
            return {"healthy": False, "reason": "bind_failed", "detail": "connection not bound"}

        auth.unbind()
        return {"healthy": True, "reason": None, "detail": "LDAP bind succeeded"}

    def config_schema(self) -> dict:
        return CONFIG_SCHEMA

    def credential_schema(self) -> dict:
        return CREDENTIAL_SCHEMA
