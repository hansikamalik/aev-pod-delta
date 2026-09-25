"""The custom Webhook connector.

Implements the same six-method Connector interface as every other connector in
the catalog, so the sync engine, the registry, and the TypeScript SDK all treat
it identically. The difference is directional: most connectors pull from a
vendor API, while this one both accepts inbound events and delivers outbound
ones to subscriber URLs.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from .auth import AuthError, verify_inbound
from .client import DeliveryClient
from .config import WebhookConfig
from .delivery_log import DeliveryLog, InMemoryDeliveryLog
from .models import (
    Asset,
    DeliveryRecord,
    DeliveryStatus,
    Event,
    Finding,
    InboundEvent,
    Subscription,
    SyncResult,
)
from .normalizer import normalize_inbound
from .subscriptions import InMemorySubscriptionStore, SubscriptionStore

logger = logging.getLogger(__name__)


class Connector(ABC):
    """Shared connector interface — mirrors `aev_connectors.base.Connector`."""

    name: str
    version: str

    @abstractmethod
    async def authenticate(self) -> bool: ...

    @abstractmethod
    async def health_check(self) -> dict[str, Any]: ...

    @abstractmethod
    async def discover(self) -> list[Asset]: ...

    @abstractmethod
    async def ingest(self) -> SyncResult: ...

    @abstractmethod
    def normalize(self, raw: dict[str, Any]) -> tuple[list[Asset], list[Finding]]: ...

    @abstractmethod
    async def push(self, assets: list[Asset], findings: list[Finding]) -> SyncResult: ...


class WebhookConnector(Connector):
    name = "webhook"
    version = "1.0.0"

    def __init__(
        self,
        config: WebhookConfig,
        platform_client: Any | None = None,
        subscriptions: SubscriptionStore | None = None,
        delivery_log: DeliveryLog | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config
        self.subscriptions = subscriptions or InMemorySubscriptionStore()
        self.delivery_log = delivery_log or InMemoryDeliveryLog()
        self._platform = platform_client
        self._http = http_client
        self._buffer: list[tuple[list[Asset], list[Finding]]] = []

    # ---------------------------------------------------------------- interface

    async def authenticate(self) -> bool:
        """Validate that the configured credentials are complete and usable.

        There is no vendor token exchange for a custom webhook: the config
        validation in `WebhookConfig` is the authentication contract.
        """
        return bool(self.config.signing_secret) and self.config.auth_mode in WebhookConfig.VALID_AUTH_MODES

    async def health_check(self) -> dict[str, Any]:
        async with DeliveryClient(self.config, self.delivery_log, self._http) as client:
            reachable = await client.ping()
        stats = (
            self.delivery_log.stats(self.config.org_id)
            if hasattr(self.delivery_log, "stats")
            else {}
        )
        failed = stats.get(DeliveryStatus.FAILED.value, 0) + stats.get(
            DeliveryStatus.DEAD_LETTERED.value, 0
        )
        return {
            "connector": self.name,
            "version": self.version,
            "connector_id": self.config.connector_id,
            "healthy": reachable and failed == 0,
            "target_reachable": reachable,
            "subscriptions": len(self.subscriptions.list(self.config.org_id, self.config.connector_id)),
            "delivery_stats": stats,
        }

    async def discover(self) -> list[Asset]:
        """Return the assets buffered from inbound events since the last sync.

        A webhook is push-based, so "discovery" means draining what arrived
        rather than enumerating a remote API.
        """
        return [asset for assets, _ in self._buffer for asset in assets]

    async def ingest(self) -> SyncResult:
        """Drain the inbound buffer and push it to the platform."""
        result = SyncResult(connector_id=self.config.connector_id, org_id=self.config.org_id)
        batch, self._buffer = self._buffer, []

        assets = [a for group, _ in batch for a in group]
        findings = [f for _, group in batch for f in group]
        result.assets_discovered = len(assets)

        if not assets and not findings:
            return result.finish()

        pushed = await self.push(assets, findings)
        result.assets_pushed = pushed.assets_pushed
        result.findings_pushed = pushed.findings_pushed
        result.errors.extend(pushed.errors)
        return result.finish()

    def normalize(self, raw: dict[str, Any]) -> tuple[list[Asset], list[Finding]]:
        return normalize_inbound(InboundEvent(**raw))

    async def push(self, assets: list[Asset], findings: list[Finding]) -> SyncResult:
        """Send normalized records to Beta's asset/exposure service."""
        result = SyncResult(connector_id=self.config.connector_id, org_id=self.config.org_id)
        if self._platform is None:
            result.errors.append("no platform client configured; nothing pushed")
            return result.finish()

        try:
            await self._platform.upsert_assets(self.config.org_id, assets)
            result.assets_pushed = len(assets)
            await self._platform.upsert_findings(self.config.org_id, findings)
            result.findings_pushed = len(findings)
        except Exception as exc:  # noqa: BLE001 — recorded, surfaced in SyncResult
            logger.exception("push to platform failed")
            result.errors.append(f"{type(exc).__name__}: {exc}")
        return result.finish()

    # ------------------------------------------------------------ webhook extras

    def accept_inbound(self, body: bytes, headers: dict[str, str], payload: dict[str, Any]) -> int:
        """Verify, normalize, and buffer one inbound event. Returns records buffered.

        Raises :class:`~aev_connectors.webhook.auth.AuthError` on a bad signature
        or bad credentials.
        """
        verify_inbound(self.config, body, headers)
        assets, findings = self.normalize(payload)
        self._buffer.append((assets, findings))
        return len(assets) + len(findings)

    def subscribe(self, target_url: str, event_types: list[str]) -> Subscription:
        return self.subscriptions.create(
            Subscription(
                org_id=self.config.org_id,
                connector_id=self.config.connector_id,
                target_url=target_url,
                event_types=event_types,
            )
        )

    def unsubscribe(self, subscription_id: str) -> None:
        self.subscriptions.delete(subscription_id)

    async def emit(self, event: Event) -> list[DeliveryRecord]:
        """Fan one platform event out to every matching subscription."""
        targets = self.subscriptions.matching(event.org_id, event.event_type)
        if not targets:
            return []
        async with DeliveryClient(self.config, self.delivery_log, self._http) as client:
            return [await client.deliver(event, sub) for sub in targets]

    async def redeliver(self, delivery_id: str) -> DeliveryRecord:
        """Manually re-fire a failed or dead-lettered delivery."""
        record = self.delivery_log.get(delivery_id)
        subscription = self.subscriptions.get(record.subscription_id)
        event = Event(
            id=record.event_id,
            org_id=record.org_id,
            event_type=record.event_type,
            payload={"redelivery_of": record.id},
        )
        async with DeliveryClient(self.config, self.delivery_log, self._http) as client:
            return await client.deliver(event, subscription)


__all__ = ["Connector", "WebhookConnector", "AuthError"]
