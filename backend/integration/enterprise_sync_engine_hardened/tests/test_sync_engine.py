import pytest
import asyncio
from sync_engine.engine import HardenedSyncEngine
from sync_engine.checkpoint_store import CheckpointStore
from sync_engine.distributed_lock import DistributedLockManager

class MockPlatformClient:
    async def push_assets(self, assets):
        return len(assets)

@pytest.mark.asyncio
async def test_incremental_sync_and_deduplication(tmp_path):
    store_path = str(tmp_path / "checkpoint.json")
    checkpoint_store = CheckpointStore(storage_path=store_path)
    lock_manager = DistributedLockManager()

    engine = HardenedSyncEngine(
        connector_id="test_connector",
        platform_client=MockPlatformClient(),
        checkpoint_store=checkpoint_store,
        lock_manager=lock_manager
    )

    async def mock_fetch():
        return [
            {"id": "asset-1", "name": "Server A"},
            {"id": "asset-1", "name": "Server A Duplicate"},
            {"id": "asset-2", "name": "Server B"}
        ]

    result = await engine.execute_incremental_sync("servers", mock_fetch)

    assert result.status == "success"
    assert result.assets_discovered == 3
    assert result.assets_pushed == 2
    assert result.vault_audit_passed is True
    assert result.last_sync_at is not None


@pytest.mark.asyncio
async def test_distributed_lock_concurrency(tmp_path):
    store_path = str(tmp_path / "checkpoint.json")
    checkpoint_store = CheckpointStore(storage_path=store_path)
    lock_manager = DistributedLockManager()

    engine = HardenedSyncEngine(
        connector_id="locked_connector",
        checkpoint_store=checkpoint_store,
        lock_manager=lock_manager
    )

    async def slow_fetch():
        await asyncio.sleep(0.1)
        return [{"id": "asset-1"}]

    assert lock_manager.acquire_lock("locked_connector") is True

    result = await engine.execute_incremental_sync("resources", slow_fetch)
    assert result.status == "failed"
    assert "Concurrency violation" in result.errors[0]

    lock_manager.release_lock("locked_connector")
    result_retry = await engine.execute_incremental_sync("resources", slow_fetch)
    assert result_retry.status == "success"
