import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, List, Optional
from .models import Checkpoint, SyncResult
from .sanitizer import normalize_event_to_asset


FetchFn = Callable[[str, str], Any]


class HardenedSyncEngine:
    def __init__(
        self, 
        connector_id: str, 
        platform_client: Any, 
        lookback_buffer_seconds: int = 60,
        retry_base_delay_seconds: float = 1.0,
    ):
        self.connector_id = connector_id
        self.platform_client = platform_client
        self.lookback_buffer_seconds = lookback_buffer_seconds
        self.retry_base_delay_seconds = retry_base_delay_seconds

    async def execute_incremental_sync(
        self,
        fetch_events_fn, 
        default_lookback_days: int = 7,
        force_full: bool = False,
    ) -> SyncResult:
        errors: List[str] = []
        assets_skipped = 0
        existing_checkpoint: Optional[Checkpoint] = self.platform_client.get_checkpoint(self.connector_id)
        now = datetime.now(timezone.utc)

        if (
            force_full
            or not existing_checkpoint
            or not existing_checkpoint.last_sync_timestamp
            or existing_checkpoint.last_sync_timestamp > now
        ):
            mode = "full"
            start_time = now - timedelta(days=default_lookback_days)
        else:
            mode = "incremental"
            start_time = (
                existing_checkpoint.last_sync_timestamp
                - timedelta(seconds=self.lookback_buffer_seconds)
            )
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sync_engine.models import Asset, SyncResult, Checkpoint
from sync_engine.vault_audit import VaultAuditLogger


class HardenedSyncEngine:
    def __init__(self, connector_id: str, platform_client: Any):
        self.connector_id = connector_id
        self.platform_client = platform_client
        self.audit_logger = VaultAuditLogger(service_name="HardenedSyncEngine")

    @staticmethod
    def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Redacts sensitive credentials recursively prior to serialization/push."""
        sanitized, _ = VaultAuditLogger.recursively_sanitize(data)
        return sanitized

    @staticmethod
    def create_asset(
        asset_id: str, raw_data: Dict[str, Any], timestamp: Optional[datetime] = None
    ) -> Asset:
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        max_attempts = 3
        raw_events = None
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                raw_events = await fetch_events_fn(
                    start_time=start_time_iso,
                    end_time=now.isoformat(),
                )
                break
            except Exception as e:
                last_error = e

                if attempt < max_attempts:
                    delay = self.retry_base_delay_seconds * (2 ** (attempt - 1))

                    if delay > 0:
                        await asyncio.sleep(delay)

        if raw_events is None:
            return SyncResult(
                status="failure",
                mode=mode,
                assets_discovered=0,
                assets_pushed=0,
                checkpoint=existing_checkpoint,
                errors=[f"Failed to fetch events from source: {last_error}"],
            )

        previously_pushed_ids = set()

        if existing_checkpoint:
            previously_pushed_ids = set(
                existing_checkpoint.metadata.get("pushed_asset_ids", [])
            )
        seen_ids = set()
        assets_to_push = []
        newest_event_time = start_time

        previous_ids = set()

        if existing_checkpoint:
            previous_ids = set(
                existing_checkpoint.metadata.get("pushed_asset_ids", [])
            )

        assets_skipped = 0

        for event in raw_events:
            try:
                asset = normalize_event_to_asset(event, self.connector_id)
            except Exception as e:
                errors.append(f"Failed to normalize event: {e}")
                continue

            if asset.id in seen_ids:
                continue

            seen_ids.add(asset.id)


            if asset.id in previously_pushed_ids:
                assets_skipped += 1
                continue
            assets_to_push.append(asset)
            asset_time = asset.discoveredAt

            if asset_time.tzinfo is None:
                asset_time = asset_time.replace(tzinfo=timezone.utc)

            if asset_time > newest_event_time:
                newest_event_time = asset_time

    async def execute_incremental_sync(
        self, fetch_fn: Any, default_lookback_days: int = 1
    ) -> SyncResult:
        checkpoint = self.platform_client.get_checkpoint(self.connector_id)
        raw_events = await fetch_fn(checkpoint)

        unique_events = {
            e.get("id") or e.get("event_id"): e for e in raw_events
        }.values()
        assets = self.process_events(list(unique_events))

        if not raw_events:
             return SyncResult(
                status="success",
                mode=mode,
                assets_discovered=0,
                assets_pushed=0,
                checkpoint=existing_checkpoint,
                errors=errors,
            )

        new_pushed_ids = previously_pushed_ids | {
            asset.id for asset in assets_to_push
        }

        new_checkpoint = Checkpoint(
            connector=self.connector_id,
            last_sync_timestamp=max(newest_event_time, start_time),
            metadata={
                 "last_run_pushed_count": assets_pushed,
                 "pushed_asset_ids": list(previous_ids | seen_ids),
            },
        )

        return SyncResult(
            status="partial_failure" if errors else "success",
            mode=mode,
            assets_discovered=len(raw_events),
            assets_pushed=assets_pushed,
            assets_skipped=assets_skipped,
            checkpoint=new_checkpoint,
            errors=errors
        )
