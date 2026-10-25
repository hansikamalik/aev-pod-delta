"""
The shared Canonical Connector contract (P1-5 Reconciliation).

Provides:
- Connector: Universal base class supporting synchronous and asynchronous execution.
- AsyncConnector: First-class asynchronous base class for modern high-concurrency connectors.
- Automated lifecycle bridge: inspects discover()/ingest() and bridges sync <-> async event loops seamlessly.
- Backward compatibility aliases: check_health <-> health_check, describe_config <-> get_config_schema.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, AsyncIterable, Iterable, List, Optional, Union

from .exceptions import ConnectorError, ContractViolation
from .models import Asset, SyncResult, SyncStatus, utcnow

logger = logging.getLogger("connector_sdk.connector")


def _run_coroutine_sync(coro: Any) -> Any:
    """Safely execute a coroutine from synchronous code."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        # In a running loop; spawn in new thread executor
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


class Connector(ABC):
    """
    Abstract base class every connector in the platform implements.

    Standardized for both synchronous and asynchronous execution pipelines.
    Subclasses can implement either synchronous discover()/ingest() or
    asynchronous async def discover()/ingest().
    """

    #: Short unique name for this connector, e.g. "aws", "gcp", "crowdstrike", "jira".
    name: str = "unnamed"

    def __init__(self, **kwargs: Any) -> None:
        self._extra_args = kwargs

    # ---- 1. Discover ----------------------------------------------------
    @abstractmethod
    def discover(self) -> Union[Iterable[Asset], AsyncIterable[Asset]]:
        """Find and return all assets visible to this connector."""
        raise NotImplementedError

    # ---- 2. Ingest --------------------------------------------------------
    @abstractmethod
    def ingest(self, assets: Iterable[Asset]) -> Union[int, Any]:
        """Push a batch of discovered assets into the platform. Returns pushed count."""
        raise NotImplementedError

    # ---- 3. Health check ------------------------------------------------
    def check_health(self) -> Union[bool, Any]:
        """Return True if connector can reach its remote source system."""
        if hasattr(self, "health_check") and callable(getattr(self, "health_check")):
            return self.health_check()
        return True

    def health_check(self) -> bool:
        """Alias for check_health for backward compatibility with integration stubs."""
        res = self.check_health()
        return bool(res)

    # ---- 4. Describe config ----------------------------------------------
    def describe_config(self) -> dict[str, Any]:
        """Return JSON-schema dict describing non-secret configuration fields."""
        if hasattr(self, "get_config_schema") and callable(getattr(self, "get_config_schema")):
            return self.get_config_schema()
        return {"type": "object", "properties": {}, "required": []}

    def get_config_schema(self) -> dict[str, Any]:
        """Alias for describe_config."""
        return self.describe_config()

    # ---- 5. Describe credentials -----------------------------------------
    def describe_credentials(self) -> dict[str, Any]:
        """Return JSON-schema dict describing credential fields (e.g. api_key, tokens)."""
        if hasattr(self, "get_credential_schema") and callable(getattr(self, "get_credential_schema")):
            return self.get_credential_schema()
        return {"type": "object", "properties": {}, "required": []}

    def get_credential_schema(self) -> dict[str, Any]:
        """Alias for describe_credentials."""
        return self.describe_credentials()

    # ---- 6. Synchronous Sync --------------------------------------------
    def sync(self) -> SyncResult:
        """
        Run a full discover -> ingest cycle synchronously.
        Bridges async implementations automatically when needed.
        """
        started_at = utcnow()
        errors: List[str] = []
        assets: List[Asset] = []

        # 1. Discover
        try:
            raw_disc = self.discover()
            if inspect.isasyncgen(raw_disc):
                async def _consume_gen():
                    items = []
                    async for item in raw_disc:
                        items.append(item)
                    return items
                assets = _run_coroutine_sync(_consume_gen())
            elif inspect.isawaitable(raw_disc):
                assets = list(_run_coroutine_sync(raw_disc))
            else:
                assets = list(raw_disc)
        except Exception as exc:
            logger.error("Connector %s discover failed: %s", self.name, exc)
            errors.append(f"discover() failed: {exc}")

        # 2. Ingest
        pushed = 0
        if assets:
            try:
                raw_ingest = self.ingest(assets)
                if inspect.isawaitable(raw_ingest):
                    res = _run_coroutine_sync(raw_ingest)
                else:
                    res = raw_ingest

                if isinstance(res, int):
                    pushed = res
                elif isinstance(res, (list, tuple)):
                    pushed = len(res)
                else:
                    pushed = len(assets)
            except Exception as exc:
                logger.error("Connector %s ingest failed: %s", self.name, exc)
                errors.append(f"ingest() failed: {exc}")

        # 3. Derive status
        if errors and pushed == 0:
            status = SyncStatus.FAILED
        elif errors:
            status = SyncStatus.PARTIAL
        else:
            status = SyncStatus.SUCCESS

        return SyncResult(
            connector=self.name,
            status=status,
            assets_discovered=len(assets),
            assets_pushed=pushed,
            errors=errors,
            started_at=started_at,
            finished_at=utcnow(),
        )

    # ---- 7. Canonical Asynchronous Sync (P1-5) ---------------------------
    async def async_sync(self) -> SyncResult:
        """
        Canonical Asynchronous synchronization contract.
        Allows modern async orchestrators to run high-concurrency ingestion without blocking threads.
        """
        started_at = utcnow()
        errors: List[str] = []
        assets: List[Asset] = []

        try:
            raw_disc = self.discover()
            if inspect.isasyncgen(raw_disc):
                async for item in raw_disc:
                    assets.append(item)
            elif inspect.isawaitable(raw_disc):
                res = await raw_disc
                assets = list(res)
            else:
                assets = list(raw_disc)
        except Exception as exc:
            errors.append(f"async discover() failed: {exc}")

        pushed = 0
        if assets:
            try:
                raw_ingest = self.ingest(assets)
                if inspect.isawaitable(raw_ingest):
                    res = await raw_ingest
                else:
                    res = raw_ingest

                if isinstance(res, int):
                    pushed = res
                elif isinstance(res, (list, tuple)):
                    pushed = len(res)
                else:
                    pushed = len(assets)
            except Exception as exc:
                errors.append(f"async ingest() failed: {exc}")

        if errors and pushed == 0:
            status = SyncStatus.FAILED
        elif errors:
            status = SyncStatus.PARTIAL
        else:
            status = SyncStatus.SUCCESS

        return SyncResult(
            connector=self.name,
            status=status,
            assets_discovered=len(assets),
            assets_pushed=pushed,
            errors=errors,
            started_at=started_at,
            finished_at=utcnow(),
        )


class AsyncConnector(Connector):
    """
    Dedicated base class for explicitly asynchronous connectors.
    Provides `async def sync()` as its primary interface while retaining
    synchronous fallback via `sync_sync()`.
    """

    @abstractmethod
    async def discover(self) -> AsyncIterable[Asset]:  # type: ignore[override]
        """Asynchronously yield or return discovered assets."""
        raise NotImplementedError

    @abstractmethod
    async def ingest(self, assets: Iterable[Asset]) -> int:  # type: ignore[override]
        """Asynchronously push assets and return pushed count."""
        raise NotImplementedError

    async def check_health(self) -> bool:  # type: ignore[override]
        """Asynchronous health check."""
        return True

    async def sync(self) -> SyncResult:  # type: ignore[override]
        """Primary asynchronous sync contract."""
        return await self.async_sync()

    def sync_sync(self) -> SyncResult:
        """Synchronous wrapper for legacy synchronous callers."""
        return _run_coroutine_sync(self.async_sync())
