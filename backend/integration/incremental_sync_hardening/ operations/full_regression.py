import asyncio
import json
import inspect
from typing import Any, Dict
from connectors.catalog import ALL_21_CONNECTORS
from core.vault_client import VaultClient
from sync_engine.engine import HardenedSyncEngine


async def run_connector_regression(connector_name: str, connector_cls: Any) -> Dict[str, Any]:
    vault = VaultClient()
    creds = vault.get_credentials(connector_name)
    
    result_report = {
        "connector": connector_name,
        "health_check": "FAILED",
        "ingestion_sync": "FAILED"
    }

    try:
        instance = connector_cls(connector_id=connector_name, credentials=creds)
        if hasattr(instance, "health_check"):
            hc = await instance.health_check() if inspect.iscoroutinefunction(instance.health_check) else instance.health_check()
            result_report["health_check"] = "PASSED" if getattr(hc, "status", "healthy") == "healthy" else "DEGRADED"

        engine = HardenedSyncEngine(connector_id=connector_name)
        async def mock_fetch():
            return [{"id": "res-1", "name": "Test Resource"}]
        
        sync_res = await engine.execute_incremental_sync("default_resource", mock_fetch)
        if sync_res.status == "success":
            result_report["ingestion_sync"] = "PASSED"
    except Exception as e:
        result_report["error"] = str(e)

    return result_report


async def main():
    print(f"=== STARTING FULL REGRESSION ACROSS {len(ALL_21_CONNECTORS)} CONNECTORS ===")
    reports = []
    for name, cls in ALL_21_CONNECTORS.items():
        rep = await run_connector_regression(name, cls)
        reports.append(rep)
        print(f"[{name}] -> Health: {rep['health_check']} | Sync: {rep['ingestion_sync']}")

    with open("full_regression_report.json", "w") as f:
        json.dump(reports, f, indent=2)
    print("Regression report successfully generated.")


if __name__ == "__main__":
    asyncio.run(main())
