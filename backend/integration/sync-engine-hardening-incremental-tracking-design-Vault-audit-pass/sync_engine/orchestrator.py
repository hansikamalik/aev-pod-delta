import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List

from sync_engine.engine import FetchFn, HardenedSyncEngine
from sync_engine.models import SyncResult

logger = logging.getLogger(__name__)


@dataclass
class ConnectorSyncConfig:
    connector_id: str
    fetch_events_fn: FetchFn  # async (start_time: str, end_time: str) -> list of raw events
    default_lookback_days: int = 7
    lookback_buffer_seconds: int = 60
    enabled: bool = True


class SyncRegistry:
    """Maps a connector_id to the config the engine needs to sync it."""

    def __init__(self) -> None:
        self._configs: Dict[str, ConnectorSyncConfig] = {}

    def register(self, config: ConnectorSyncConfig) -> None:
        if config.connector_id in self._configs:
            raise ValueError(f"Connector already registered: {config.connector_id}")
        self._configs[config.connector_id] = config

    def get(self, connector_id: str) -> ConnectorSyncConfig:
        if connector_id not in self._configs:
            raise KeyError(f"Unknown connector: {connector_id}")
        return self._configs[connector_id]

    def names(self) -> List[str]:
        return [n for n, c in self._configs.items() if c.enabled]


async def sync_connector(
    registry: SyncRegistry,
    platform_client: Any,
    connector_id: str,
    force_full: bool = False,
) -> SyncResult:
    config = registry.get(connector_id)
    engine = HardenedSyncEngine(
        connector_id=config.connector_id,
        platform_client=platform_client,
        lookback_buffer_seconds=config.lookback_buffer_seconds,
    )
    return await engine.execute_incremental_sync(
        config.fetch_events_fn,
        default_lookback_days=config.default_lookback_days,
        force_full=force_full,
    )


async def sync_all_connectors(
    registry: SyncRegistry,
    platform_client: Any,
    force_full: bool = False,
    max_concurrency: int = 4,
) -> Dict[str, SyncResult]:
    """
    Run every enabled connector concurrently (bounded by max_concurrency).
    One connector crashing never stops or fails the others.
    """
    semaphore = asyncio.Semaphore(max_concurrency)

    async def _run(name: str) -> SyncResult:
        async with semaphore:
            try:
                return await sync_connector(registry, platform_client, name, force_full)
            except Exception as e:
                logger.exception("[%s] sync crashed", name)
                return SyncResult(status="failure", errors=[f"Unhandled error: {e}"])

    names = registry.names()
    results = await asyncio.gather(*(_run(n) for n in names))
    summary = dict(zip(names, results))

    for name, r in summary.items():
        logger.info(
            "[%s] %s (%s) discovered=%d pushed=%d skipped=%d errors=%d",
            name, r.status, r.mode, r.assets_discovered,
            r.assets_pushed, r.assets_skipped, len(r.errors),
        )
    return summary
