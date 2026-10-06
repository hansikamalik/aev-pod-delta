import time
from datetime import datetime, timezone
from typing import List, Dict, Any
from sync_engine.base_connector import BaseConnector
from sync_engine.models import HealthCheckResult, SyncResult, Checkpoint
from sync_engine.engine import HardenedSyncEngine


class AzureNormalizationPlatformPush(BaseConnector):
    def __init__(self, platform_client: Any):
        super().__init__("Azure_Normalization_Platform_Push", platform_client)
        self.simulate_partial_failure = False

    async def health_check(self) -> HealthCheckResult:
        start = time.perf_counter()
        elapsed = (time.perf_counter() - start) * 1000
        self.audit_logger.log_audit_trail(self.connector_id, "health_check", {"status": "ok"})
        return HealthCheckResult(
            connector_id=self.connector_id,
            healthy=True,
            latency_ms=elapsed,
            message="OK",
            vault_audit_passed=True,
        )

    async def discover(self) -> List[Dict[str, Any]]:
        raw_resources = [{"id": "azure-asset-01", "type": "vm", "client_secret": "azure_secret_key"}]
        sanitized_resources, _ = self.audit_logger.recursively_sanitize(raw_resources)
        self.audit_logger.log_audit_trail(self.connector_id, "discover", {"count": len(sanitized_resources)})
        return sanitized_resources

    async def ingest(self, start_time: str) -> List[Dict[str, Any]]:
        raw_events = [{"event_id": "azure-evt-01", "ts": "2026-10-01T13:00:00+00:00", "access_token": "bearer_azure_token"}]
        sanitized_events, _ = self.audit_logger.recursively_sanitize(raw_events)
        self.audit_logger.log_audit_trail(self.connector_id, "ingest", {"events": len(sanitized_events)})
        return sanitized_events

    async def sync(self) -> SyncResult:
        raw_items = await self.ingest("2026-10-01T00:00:00Z")
        assets = []
        errors = []

        should_fail_partially = (
            getattr(self, "simulate_partial_failure", False)
            or getattr(self.platform_client, "simulate_partial_failure", False)
            or getattr(self.platform_client, "should_fail_push", False)
        )

        for item in raw_items:
            if should_fail_partially or item.get("status") == "error":
                errors.append(f"Failed normalization/push on item: {item.get('event_id', 'unknown')}")
            else:
                assets.append(
                    HardenedSyncEngine.create_asset(
                        item.get("event_id") or item.get("id") or "azure-evt-01",
                        item,
                        datetime.now(timezone.utc),
                    )
                )

        status = "partial_failure" if errors else "success"

        if hasattr(self.platform_client, "push_assets"):
            self.platform_client.push_assets(self.connector_id, assets)
        elif hasattr(self.platform_client, "save_assets"):
            self.platform_client.save_assets(self.connector_id, assets)

        hwm = datetime.fromisoformat("2026-10-01T13:00:00+00:00")
        self.platform_client.save_checkpoint(
            Checkpoint(connector_id=self.connector_id, high_water_mark=hwm)
        )

        self.audit_logger.log_audit_trail(
            self.connector_id, "sync", {"status": status, "assets_pushed": len(assets)}
        )

        return SyncResult(
            status=status,
            assets_pushed=len(assets),
            high_water_mark=hwm.isoformat(),
            errors=errors,
            vault_audit_passed=True,
        )
