"""
MicrosoftDefenderConnector — full implementation of the platform
Connector interface for Microsoft Defender for Endpoint
(FR-INT-013).

Wires together: auth (OAuth 2.0) -> credentials (Vault) ->
discovery/ingestion (Defender API) -> normalization (shared Asset/
finding shape) -> push (Beta's asset/exposure services).
"""

from __future__ import annotations

from typing import AsyncIterator

import httpx

from .auth import DefenderAuthClient
from .config import DefenderConfig
from .credentials import VaultClient, VaultCredentialProvider
from .discovery import iter_machines
from .exceptions import AuthenticationError, DefenderAPIError, PushError, VaultAccessError
from .ingestion import iter_alerts
from .models import Asset, SyncResult
from .normalization import normalize_alert, normalize_machine
from .push import PlatformPushClient
from .schemas import CONFIG_SCHEMA, CREDENTIAL_SCHEMA
from .sdk_interface import Connector


class MicrosoftDefenderConnector(Connector):
    def __init__(
        self,
        integration_id: str,
        credentials_ref: str,
        vault_client: VaultClient,
        asset_ingest_url: str,
        exposure_ingest_url: str,
        http_client: httpx.AsyncClient | None = None,
    ):
        self._integration_id = integration_id
        self._credential_provider = VaultCredentialProvider(vault_client, credentials_ref)
        self._http = http_client or httpx.AsyncClient()
        self._owns_http_client = http_client is None
        self._asset_ingest_url = asset_ingest_url
        self._exposure_ingest_url = exposure_ingest_url

    async def aclose(self) -> None:
        if self._owns_http_client:
            await self._http.aclose()

    # -- Connector interface -------------------------------------------------

    async def discover(self, config: dict) -> AsyncIterator[Asset]:
        cfg = DefenderConfig(**config)
        auth = DefenderAuthClient(cfg, self._credential_provider, self._http)
        async for machine in iter_machines(cfg, auth, self._http):
            yield normalize_machine(machine)

    async def ingest(self, config: dict) -> AsyncIterator[dict]:
        cfg = DefenderConfig(**config)
        auth = DefenderAuthClient(cfg, self._credential_provider, self._http)
        async for alert in iter_alerts(cfg, auth, self._http):
            yield normalize_alert(alert).to_dict()

    async def sync(self, config: dict, direction: str = "pull") -> SyncResult:
        if direction != "pull":
            return SyncResult(
                records_processed=0,
                records_created=0,
                records_updated=0,
                records_failed=0,
                error=f"Microsoft Defender connector only supports 'pull' sync, got '{direction}'",
            )

        cfg = DefenderConfig(**config)
        pusher = PlatformPushClient(
            http_client=self._http,
            integration_id=self._integration_id,
            asset_ingest_url=self._asset_ingest_url,
            exposure_ingest_url=self._exposure_ingest_url,
            request_timeout_seconds=cfg.request_timeout_seconds,
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

            async for finding in self.ingest(config):
                processed += 1
                try:
                    await pusher.push_finding_dict(finding)
                    created += 1
                except PushError:
                    failed += 1
        except (AuthenticationError, VaultAccessError, DefenderAPIError) as exc:
            error = str(exc)

        return SyncResult(
            records_processed=processed,
            records_created=created,
            records_updated=0,
            records_failed=failed,
            error=error,
        )

    async def health_check(self, config: dict) -> dict:
        cfg = DefenderConfig(**config)
        auth = DefenderAuthClient(cfg, self._credential_provider, self._http)

        try:
            await auth.get_token(force_refresh=True)
        except VaultAccessError as exc:
            return {"healthy": False, "reason": "vault_unreachable", "detail": str(exc)}
        except AuthenticationError as exc:
            return {"healthy": False, "reason": "auth_failed", "detail": str(exc)}

        try:
            headers = await auth.auth_headers()
            response = await self._http.get(
                f"{cfg.api_base_url}api/machines",
                headers=headers,
                params={"$top": 1},
                timeout=cfg.request_timeout_seconds,
            )
        except httpx.HTTPError as exc:
            return {"healthy": False, "reason": "api_unreachable", "detail": str(exc)}

        if response.status_code != 200:
            return {
                "healthy": False,
                "reason": "api_error",
                "detail": f"{response.status_code}: {response.text[:200]}",
            }

        return {"healthy": True, "reason": None, "detail": "token acquired; machines API reachable"}

    def config_schema(self) -> dict:
        return CONFIG_SCHEMA

    def credential_schema(self) -> dict:
        return CREDENTIAL_SCHEMA
