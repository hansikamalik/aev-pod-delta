import inspect
import json
import datetime
import time
from typing import Any, Callable, Dict, Optional
from sync_engine.models import SyncResult
from sync_engine.checkpoint_store import CheckpointStore
from sync_engine.distributed_lock import DistributedLockManager
from monitoring.metrics_alerter import MetricsAlerter
from monitoring.monitoring_api import SyncMonitoringAPI
from core.vault_client import VaultClient
from core.audit_sanitizer import VaultAuditSanitizer


class HardenedSyncEngine:
    """Enterprise sync engine implementing incremental tracking, idempotency, distributed locking, and integrated monitoring telemetry."""

    def __init__(
        self,
        connector_id: Optional[str] = None,
        platform_client: Optional[Any] = None,
        lookback_buffer_seconds: int = 0,
        checkpoint_store: Optional[CheckpointStore] = None,
        lock_manager: Optional[DistributedLockManager] = None,
        monitoring_api: Optional[SyncMonitoringAPI] = None,
        *args,
        **kwargs
    ):
        self.connector_id = connector_id or "default_connector"
        self.platform_client = platform_client
        self.lookback_buffer_seconds = lookback_buffer_seconds
        self.checkpoint_store = checkpoint_store or CheckpointStore()
        self.lock_manager = lock_manager or DistributedLockManager()
        self.alerter = MetricsAlerter()
        self.monitoring_api = monitoring_api or SyncMonitoringAPI()
        self.vault_client = VaultClient()
        self.audit_sanitizer = VaultAuditSanitizer()

    async def execute_incremental_sync(
        self,
        resource_type_or_fn: Any,
        fetch_events_fn: Optional[Callable[..., Any]] = None,
        *args,
        **kwargs,
    ) -> SyncResult:
        if callable(resource_type_or_fn):
            resource_type = "default_resource"
            fetch_fn = resource_type_or_fn
        else:
            resource_type = str(resource_type_or_fn)
            fetch_fn = fetch_events_fn

        start_time = datetime.datetime.now(datetime.timezone.utc)
        start_ts = time.time()

        if not self.lock_manager.acquire_lock(self.connector_id):
            err_msg = (
                f"Concurrency violation: Connector "
                f"{self.connector_id} is already syncing."
            )
            elapsed = time.time() - start_ts
            self.alerter.report_sync_failure(self.connector_id, err_msg)
            self.monitoring_api.record_sync_event(
                self.connector_id, "failed", elapsed, 0, error=err_msg
            )
            return SyncResult(
                connector=self.connector_id,
                status="failed",
                errors=[err_msg],
            )

        try:
            checkpoint = self.checkpoint_store.load_checkpoint(
                self.connector_id, resource_type
            )
            metadata = checkpoint.get("metadata", {})
            processed_ids = set(metadata.get("processed_event_ids", []))

            events = await fetch_fn() if callable(fetch_fn) else []
            assets_discovered = len(events)

            # Deduplicate within this batch and against previous successful syncs.
            unique_events = []
            batch_ids = set()
            assets_skipped = 0

            for event in events:
                event_id = event.get("id") or event.get("asset_id")

                if event_id is None:
                    event_id = event

                event_key = json.dumps(
                    event_id,
                    sort_keys=True,
                    default=str,
                )

                if event_key in batch_ids or event_key in processed_ids:
                    assets_skipped += 1
                    continue

                batch_ids.add(event_key)
                unique_events.append((event_key, event))

            # Do not advance the checkpoint if the platform rejects the push.
            if unique_events:
                assets = [event for _, event in unique_events]

                try:
                    push_result = self.platform_client.push_assets(assets)

                    if inspect.isawaitable(push_result):
                        await push_result
                except Exception as exc:
                    message = f"Platform push failed: {exc}"
                    elapsed = time.time() - start_ts

                    self.alerter.report_sync_failure(
                        self.connector_id, message
                    )
                    self.monitoring_api.record_sync_event(
                        self.connector_id,
                        "partial_failure",
                        elapsed,
                        0,
                        error=message,
                    )

                    return SyncResult(
                        connector=self.connector_id,
                        status="partial_failure",
                        assets_discovered=assets_discovered,
                        assets_pushed=0,
                        assets_skipped=assets_skipped,
                        errors=[message],
                    )

            # Verify Vault token redaction before advancing the checkpoint.
            try:
                credentials = self.vault_client.get_credentials(self.connector_id)
                token = credentials["active_token"]

                audit_message = (
                    f"Connector {self.connector_id} authenticated using token {token}"
                )
                sanitized_message = self.audit_sanitizer.sanitize(audit_message)

                vault_audit_passed = (
                    bool(token)
                    and token not in sanitized_message
                    and "[REDACTED]" in sanitized_message
                )

                if not vault_audit_passed:
                    message = "Vault audit verification failed; checkpoint not advanced."

                    self.alerter.report_sync_failure(self.connector_id, message)
                    self.monitoring_api.record_sync_event(
                        self.connector_id,
                        "failed",
                        time.time() - start_ts,
                        0,
                        error=message,
                    )

                    return SyncResult(
                        connector=self.connector_id,
                        status="failed",
                        assets_discovered=assets_discovered,
                        assets_pushed=0,
                        assets_skipped=assets_skipped,
                        errors=[message],
                        vault_audit_passed=vault_audit_passed,
                    )

            except Exception as exc:
                message = f"Vault audit verification failed: {exc}"

                self.alerter.report_sync_failure(self.connector_id, message)
                self.monitoring_api.record_sync_event(
                    self.connector_id,
                    "failed",
                    time.time() - start_ts,
                    0,
                    error=message,
                )

                return SyncResult(
                    connector=self.connector_id,
                    status="failed",
                    assets_discovered=assets_discovered,
                    assets_pushed=0,
                    assets_skipped=assets_skipped,
                    errors=[message],
                    vault_audit_passed=vault_audit_passed,
                )

            # Only mark events as processed after push and audit succeed.
            processed_ids.update(batch_ids)

            now_iso = datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat()

            new_checkpoint = {
                "high_water_mark": now_iso,
                "last_sync_at": now_iso,
                "metadata": {
                    "processed_event_ids": sorted(processed_ids),
                },
            }

            # Save the internal checkpoint after a successful push.
            self.checkpoint_store.save_checkpoint(
                self.connector_id,
                resource_type,
                new_checkpoint,
            )

            # Update the platform checkpoint only after successful processing.
            if self.platform_client is not None:
                save_platform_checkpoint = getattr(
                    self.platform_client, "save_checkpoint", None
                )
                if callable(save_platform_checkpoint):
                    save_platform_checkpoint(new_checkpoint)

            elapsed = time.time() - start_ts
            duration = (
                datetime.datetime.now(datetime.timezone.utc) - start_time
            ).total_seconds()

            assets_pushed = len(unique_events)

            self.alerter.report_sync_success(
                self.connector_id,
                resource_type,
                duration,
                assets_pushed,
            )
            self.monitoring_api.record_sync_event(
                self.connector_id,
                "success",
                elapsed,
                assets_pushed,
            )

            return SyncResult(
                connector=self.connector_id,
                status="success",
                assets_discovered=assets_discovered,
                assets_pushed=assets_pushed,
                assets_skipped=assets_skipped,
                high_water_mark=now_iso,
                last_sync_at=now_iso,
                errors=[],
                vault_audit_passed=vault_audit_passed,
                started_at=start_time.isoformat(),
                finished_at=now_iso,
            )

        except Exception as exc:
            elapsed = time.time() - start_ts
            message = str(exc)

            self.alerter.report_sync_failure(self.connector_id, message)
            self.monitoring_api.record_sync_event(
                self.connector_id,
                "failed",
                elapsed,
                0,
                error=message,
            )

            return SyncResult(
                connector=self.connector_id,
                status="failed",
                errors=[message],
            )

        finally:
            self.lock_manager.release_lock(self.connector_id)

    def sync_resource(self, resource_type: str, total_records: int = 50, fail_at_offset: int = -1, *args, **kwargs) -> Dict[str, Any]:
        if fail_at_offset >= 0 and fail_at_offset < total_records:
            raise RuntimeError(f"Simulated mid-sync crash at offset {fail_at_offset}")
        return {"status": "SUCCESS", "records_synced": total_records}
