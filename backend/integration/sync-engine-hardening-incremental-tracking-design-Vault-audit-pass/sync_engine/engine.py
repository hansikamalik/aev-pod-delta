from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional
from sync_engine.models import Checkpoint, SyncResult
from sync_engine.sanitizer import normalize_event_to_asset


class HardenedSyncEngine:
    def __init__(
        self, 
        connector_id: str, 
        platform_client: Any, 
        lookback_buffer_seconds: int = 60
    ):
        self.connector_id = connector_id
        self.platform_client = platform_client
        self.lookback_buffer_seconds = lookback_buffer_seconds

    async def execute_incremental_sync(
        self, 
        fetch_events_fn, 
        default_lookback_days: int = 7
    ) -> SyncResult:
        errors: List[str] = []
        
        existing_checkpoint: Optional[Checkpoint] = self.platform_client.get_checkpoint(self.connector_id)
        
        now = datetime.now(timezone.utc)
        if existing_checkpoint and existing_checkpoint.last_sync_timestamp:
            start_time = existing_checkpoint.last_sync_timestamp - timedelta(seconds=self.lookback_buffer_seconds)
        else:
            start_time = now - timedelta(days=default_lookback_days)

        start_time_iso = start_time.isoformat()

        try:
            raw_events = await fetch_events_fn(start_time=start_time_iso, end_time=now.isoformat())
        except Exception as e:
            return SyncResult(
                status="failure",
                assets_discovered=0,
                assets_pushed=0,
                checkpoint=existing_checkpoint,
                errors=[f"Failed to fetch events from source: {e}"]
            )

        seen_ids = set()
        assets_to_push = []
        newest_event_time = start_time

        for event in raw_events:
            asset = normalize_event_to_asset(event, self.connector_id)
            if asset.id in seen_ids:
                continue
            seen_ids.add(asset.id)
            assets_to_push.append(asset)

            if asset.discoveredAt > newest_event_time:
                newest_event_time = asset.discoveredAt

        assets_pushed = 0
        if assets_to_push:
            try:
                self.platform_client.push_assets(assets_to_push)
                assets_pushed = len(assets_to_push)
            except Exception as e:
                errors.append(f"Asset ingestion pipeline error: {e}")
                return SyncResult(
                    status="partial_failure",
                    assets_discovered=len(raw_events),
                    assets_pushed=0,
                    checkpoint=existing_checkpoint,
                    errors=errors
                )

        new_checkpoint = Checkpoint(
            connector=self.connector_id,
            last_sync_timestamp=max(newest_event_time, start_time),
            metadata={"last_run_pushed_count": assets_pushed}
        )
        
        self.platform_client.save_checkpoint(new_checkpoint)

        return SyncResult(
            status="success",
            assets_discovered=len(raw_events),
            assets_pushed=assets_pushed,
            checkpoint=new_checkpoint,
            errors=errors
        )
