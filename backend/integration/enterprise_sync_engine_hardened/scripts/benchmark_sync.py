import asyncio
import json
import os
import time
from sync_engine.engine import HardenedSyncEngine
from sync_engine.checkpoint_store import CheckpointStore


class MockPlatformClient:
    def __init__(self):
        self.assets_received = 0

    async def push_assets(self, assets):
        self.assets_received += len(assets)
        return len(assets)


async def run_benchmark():
    os.makedirs("docs/evidence", exist_ok=True)
    print("=== STARTING SYNC BENCHMARK (10K synthetic records) ===")

    platform_client = MockPlatformClient()
    engine = HardenedSyncEngine(
        connector_id="benchmark_connector",
        platform_client=platform_client,
        checkpoint_store=CheckpointStore("bench_checkpoint.json"),
    )
    
    async def mock_large_fetch():
        return [{"id": f"rec-{i}", "name": f"Record Number {i}"} for i in range(10000)]

    start_time = time.time()
    result = await engine.execute_incremental_sync("bulk_data", mock_large_fetch)
    duration = time.time() - start_time

    target_seconds = 300.0  # 5-minute target
    expected_assets = 10000
    passed = (
        result.status == "success"
        and result.assets_pushed == expected_assets
        and platform_client.assets_received == expected_assets
        and duration <= target_seconds
    )

    report = {
        "records_processed": expected_assets,
        "duration_seconds": round(duration, 4),
        "target_seconds": target_seconds,
        "status": "PASSED" if passed else "FAILED",
        "assets_pushed": platform_client.assets_received,
        "engine_reported_assets_pushed": result.assets_pushed,
    }

    if passed:
        with open("docs/evidence/benchmark_results.json", "w") as f:
            json.dump(report, f, indent=2)

    print(
        f" -> Benchmark Completed in {duration:.2f}s (Target: <300s). "
        f"Status: {report['status']}; Assets received: "
        f"{platform_client.assets_received}/{expected_assets}"
    )
    return passed


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(run_benchmark()) else 1)
