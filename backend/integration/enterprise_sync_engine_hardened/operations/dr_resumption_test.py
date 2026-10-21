import asyncio
from datetime import datetime, timezone
from sync_engine.engine import HardenedSyncEngine
from sync_engine.checkpoint_store import CheckpointStore


async def simulate_disaster_recovery():
    print("=== STARTING DR SERVICE OUTAGE & RESUMPTION TEST ===")
    store_path = "dr_test_checkpoint.json"
    checkpoint_store = CheckpointStore(storage_path=store_path)
    
    connector_id = "splunk_connector"
    resource_type = "audit_logs"

    checkpoint_store.save_checkpoint(
        connector_id,
        resource_type,
        {"offset": 20, "high_water_mark": datetime.now(timezone.utc).isoformat()}
    )

    engine = HardenedSyncEngine(connector_id=connector_id, checkpoint_store=checkpoint_store)

    async def mock_resumed_fetch():
        return [{"id": "res-21"}, {"id": "res-22"}]

    result = await engine.execute_incremental_sync(resource_type, mock_resumed_fetch)
    print(f" -> DR Resumption Status: {result.status.upper()} | Pushed: {result.assets_pushed}")


if __name__ == "__main__":
    asyncio.run(simulate_disaster_recovery())
