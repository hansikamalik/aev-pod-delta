"""Reference connector implementation (Section 27).

This is a *behavioral reference*, not production code. New connectors
SHOULD copy this structure and replace the source-specific parts:

    client.py     -> real API communication
    normalizer    -> source object to Asset mapping
    connector.py  -> wiring only

It demonstrates every contract requirement: a stable name, paginated
discovery, deterministic asset IDs, normalized asset types, preserved raw
payloads, batched ingestion with an accurate pushed count, a lightweight
health check, and separated config / credential schemas.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable, Mapping

from connector_sdk import (
    Asset,
    AssetType,
    Connector,
    DiscoveryError,
    build_asset_id,
    field,
    object_schema,
    secret_field,
)

from .client import SampleSourceClient

logger = logging.getLogger(__name__)

#: Source-specific resource kind -> normalized AssetType (Section 8).
_TYPE_MAP: dict[str, AssetType] = {
    "server": AssetType.COMPUTE,
    "bucket": AssetType.STORAGE,
    "user": AssetType.IDENTITY,
    "vnet": AssetType.NETWORK,
}

_INGEST_BATCH_SIZE = 100


class SampleConnector(Connector):
    """Reference connector against a fake paginated source system."""

    name = "sample"

    def __init__(
        self,
        config: Mapping[str, Any] | None = None,
        credentials: Mapping[str, Any] | None = None,
        *,
        client: SampleSourceClient | None = None,
        platform_client: Any | None = None,
    ) -> None:
        super().__init__(config=config, credentials=credentials)
        self._client = client or SampleSourceClient(
            region=self._config.get("region", "eastus"),
            api_key=self.get_credential("api_key"),
        )
        # Injected so tests can pass InMemoryPlatformClient.
        self._platform = platform_client

    # ------------------------------------------------------------------
    # Schemas (Sections 18, 19)
    # ------------------------------------------------------------------

    def describe_config(self) -> dict:
        return object_schema(
            {
                "region": field("string", description="Source region"),
                "page_size": field("integer", description="Resources per page", default=50),
                "include_users": field(
                    "boolean", description="Also discover identity resources", default=True
                ),
            },
            required=["region"],
        )

    def describe_credentials(self) -> dict:
        return object_schema(
            {"api_key": secret_field("Sample source API key")},
            required=["api_key"],
        )

    # ------------------------------------------------------------------
    # Health (Section 17)
    # ------------------------------------------------------------------

    def check_health(self) -> bool:
        """Lightweight ping. Never raises, never discovers."""
        try:
            return self._client.ping()
        except Exception:
            logger.warning("connector=%s health check failed", self.name)
            return False

    # ------------------------------------------------------------------
    # Discovery (Section 10)
    # ------------------------------------------------------------------

    def discover(self) -> Iterable[Asset]:
        """Yield normalized assets, walking every page of the source API."""
        page_size = int(self._config.get("page_size", 50))
        try:
            for resource in self._client.iter_resources(page_size=page_size):
                asset = self._normalize(resource)
                if asset is not None:
                    yield asset
        except DiscoveryError:
            raise
        except Exception as exc:
            # Never silently discard an API failure (Section 10).
            raise DiscoveryError(
                f"Discovery failed: {exc}",
                operation="discover",
                source=self.name,
            ) from exc

    def _normalize(self, resource: Mapping[str, Any]) -> Asset | None:
        """Map one source resource onto an :class:`Asset`."""
        kind = str(resource.get("kind", "")).lower()
        asset_type = _TYPE_MAP.get(kind, AssetType.OTHER)

        if asset_type is AssetType.IDENTITY and not self._config.get("include_users", True):
            return None

        native_id = resource.get("id")
        # Deterministic fallback when the source lacks a natural ID (Section 6).
        asset_id = (
            str(native_id)
            if native_id
            else build_asset_id(self.name, kind or "other", str(resource.get("name", "unknown")))
        )

        return Asset(
            id=asset_id,
            source=self.name,
            type=asset_type,
            name=str(resource.get("name") or asset_id),
            raw=dict(resource),
            tags=dict(resource.get("tags", {})),
        )

    # ------------------------------------------------------------------
    # Ingestion (Section 11)
    # ------------------------------------------------------------------

    def ingest(self, assets: Iterable[Asset]) -> int:
        """Batch-upsert to the platform, returning the accepted count."""
        assets = list(assets)
        if not assets:
            return 0
        if self._platform is None:
            raise DiscoveryError(
                "No platform client configured", operation="ingest", source=self.name
            )

        pushed = 0
        for start in range(0, len(assets), _INGEST_BATCH_SIZE):
            batch = assets[start : start + _INGEST_BATCH_SIZE]
            accepted = self._platform.bulk_upsert(batch)
            # Only count what the platform actually accepted.
            pushed += int(accepted) if accepted is not None else len(batch)

        logger.info("connector=%s pushed=%d of %d", self.name, pushed, len(assets))
        return pushed


__all__ = ["SampleConnector"]
