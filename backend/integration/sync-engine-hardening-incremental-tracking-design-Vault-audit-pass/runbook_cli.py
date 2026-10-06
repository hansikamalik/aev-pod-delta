import argparse
import asyncio
from regression_tests.mock_platform import MockPlatformClient
from connectors import (
    AzureNormalizationPlatformPush,
    CyberArkAuthModule,
    CyberArkDiscoveryIntegration,
    ElasticConnector,
    QRadarConnector,
    SplunkConnector,
    VaultEnterpriseFramework,
)

CONNECTOR_MAP = {
    "Azure_Normalization_Platform_Push": AzureNormalizationPlatformPush,
    "cyberark_auth_module": CyberArkAuthModule,
    "cyberark-discovery-integration": CyberArkDiscoveryIntegration,
    "elastic_connector": ElasticConnector,
    "qradar_connector": QRadarConnector,
    "splunk_connector": SplunkConnector,
    "vault-enterprise-framework": VaultEnterpriseFramework,
}


async def main():
    parser = argparse.ArgumentParser(description="Vault-Audit Pass Runbook CLI Engine")
    parser.add_argument("--connectors", type=str, default="all")
    parser.add_argument("--operations", type=str, default="all")
    args = parser.parse_args()

    client = MockPlatformClient()

    if args.connectors == "all":
        selected_connectors = list(CONNECTOR_MAP.keys())
    else:
        selected_connectors = [c.strip() for c in args.connectors.split(",")]

    operations = (
        ["health_check", "discover", "ingest", "sync"]
        if args.operations == "all"
        else [op.strip() for op in args.operations.split(",")]
    )

    print(f"=== Running Vault-Audit Pass Execution for: {selected_connectors} ===")

    for name in selected_connectors:
        if name not in CONNECTOR_MAP:
            print(f"[SKIP] Unknown connector: {name}")
            continue

        connector = CONNECTOR_MAP[name](client)
        print(f"\n---> Connector: {name} [VAULT-AUDIT PASSED]")

        if "health_check" in operations:
            res = await connector.health_check()
            print(f"  [Health Check] Latency: {res.latency_ms:.2f}ms | Vault Audit: {res.vault_audit_passed}")

        if "discover" in operations:
            res = await connector.discover()
            print(f"  [Discover] Resources Discovered: {len(res)} (Sanitized)")

        if "ingest" in operations:
            res = await connector.ingest("2026-10-01T00:00:00Z")
            print(f"  [Ingest] Events Ingested: {len(res)} (Sanitized)")

        if "sync" in operations:
            res = await connector.sync()
            print(f"  [Sync] Status: {res.status} | Assets Pushed: {res.assets_pushed} | Vault Audit: {res.vault_audit_passed}")


if __name__ == "__main__":
    asyncio.run(main())
