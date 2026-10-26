import asyncio
import json
import os
import time
from sync_engine.engine import HardenedSyncEngine
from sync_engine.checkpoint_store import CheckpointStore


async def run_benchmark():
    os.makedirs("docs/evidence", exist_ok=True)
    print("=== STARTING SYNC BENCHMARK (10K synthetic records) ===")
    
    engine = HardenedSyncEngine(connector_id="benchmark_connector", checkpoint_store=CheckpointStore("bench_checkpoint.json"))
    
    async def mock_large_fetch():
        return [{"id": f"rec-{i}", "name": f"Record Number {i}"} for i in range(10000)]

    start_time = time.time()
    result = await engine.execute_incremental_sync("bulk_data", mock_large_fetch)
    duration = time.time() - start_time

    target_seconds = 300.0  # 5-minute target
    passed = duration <= target_seconds and result.status == "success"

    report = {
        "records_processed": 10000,
        "duration_seconds": round(duration, 4),
        "target_seconds": target_seconds,
        "status": "PASSED" if passed else "FAILED",
        "assets_pushed": result.assets_pushed
    }

    with open("docs/evidence/benchmark_results.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f" -> Benchmark Completed in {duration:.2f}s (Target: <300s). Status: {report['status']}")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
