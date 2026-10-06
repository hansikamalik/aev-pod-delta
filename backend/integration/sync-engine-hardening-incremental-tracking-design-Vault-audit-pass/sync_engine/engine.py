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

        sanitized_raw = HardenedSyncEngine.sanitize_dict(raw_data)
        VaultAuditLogger.assert_vault_compliant(sanitized_raw)

        return Asset(
            asset_id=str(asset_id),
            raw=sanitized_raw,
            timestamp=timestamp,
        )

    def _push_to_platform(self, connector_id: str, assets: List[Asset]) -> None:
        # Audit validation before emitting assets to target platform
        for asset in assets:
            VaultAuditLogger.assert_vault_compliant(asset.raw)

        if hasattr(self.platform_client, "push_assets"):
            self.platform_client.push_assets(connector_id, assets)
        elif hasattr(self.platform_client, "save_assets"):
            self.platform_client.save_assets(connector_id, assets)

    def process_events(self, events: List[Dict[str, Any]]) -> List[Asset]:
        assets = []
        for evt in events:
            evt_id = evt.get("id") or evt.get("event_id") or "unknown_id"
            ts = evt.get("timestamp") or evt.get("ts") or datetime.now(timezone.utc)
            assets.append(HardenedSyncEngine.create_asset(evt_id, evt, ts))
        return assets

    async def execute_incremental_sync(
        self, fetch_fn: Any, default_lookback_days: int = 1
    ) -> SyncResult:
        checkpoint = self.platform_client.get_checkpoint(self.connector_id)
        raw_events = await fetch_fn(checkpoint)

        unique_events = {
            e.get("id") or e.get("event_id"): e for e in raw_events
        }.values()
        assets = self.process_events(list(unique_events))

        self._push_to_platform(self.connector_id, assets)

        new_hwm = datetime.now(timezone.utc).isoformat()
        self.platform_client.save_checkpoint(
            Checkpoint(
                connector_id=self.connector_id,
                high_water_mark=datetime.fromisoformat(new_hwm),
            )
        )

        return SyncResult(
            status="success",
            assets_pushed=len(assets),
            high_water_mark=new_hwm,
            errors=[],
            vault_audit_passed=True,
        )
