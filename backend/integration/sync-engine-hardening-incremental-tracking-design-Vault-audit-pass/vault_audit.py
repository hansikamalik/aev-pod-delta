import asyncio
from sync_engine.vault import VaultClient
from sync_engine.engine import SENSITIVE_KEYS
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

CONNECTORS = [
    "Azure_Normalization_Platform_Push",
    "cyberark_auth_module",
    "cyberark-discovery-integration",
    "elastic_connector",
    "qradar_connector",
    "splunk_connector",
    "vault-enterprise-framework",
]

def audit_vault_credentials():
    print("==================================================================")
    print(" 1. VAULT CREDENTIAL AUDIT")
    print("==================================================================")
    vc = VaultClient()
    for cid in CONNECTORS:
        try:
            creds = vc.get_connector_credentials(cid)
            print(f" [+] [PASS] {cid:<36} -> Registered Keys: {list(creds.keys())}")
        except Exception as e:
            print(f" [-] [FAIL] {cid:<36} -> Error: {e}")

async def audit_secret_redaction():
    print("\n==================================================================")
    print(" 2. SECRET REDACTION & LEAKAGE AUDIT")
    print("==================================================================")
    platform = MockPlatformClient()
    instances = [
        AzureNormalizationPlatformPush(platform_client=platform),
        CyberArkAuthModule(platform_client=platform),
        CyberArkDiscoveryIntegration(platform_client=platform),
        ElasticConnector(platform_client=platform),
        QRadarConnector(platform_client=platform),
        SplunkConnector(platform_client=platform),
        VaultEnterpriseFramework(platform_client=platform),
    ]

    for connector in instances:
        await connector.sync()
        assets = platform.ingested_assets.get(connector.connector_id, [])
        leaks = []
        for asset in assets:
            for key in asset.raw.keys():
                if key.lower() in SENSITIVE_KEYS:
                    leaks.append(key)
        
        if leaks:
            print(f" [-] [FAIL] {connector.connector_id:<36} -> LEAK DETECTED! Keys: {leaks}")
        else:
            print(f" [+] [PASS] {connector.connector_id:<36} -> Clean (All sensitive keys redacted)")

if __name__ == "__main__":
    audit_vault_credentials()
    asyncio.run(audit_secret_redaction())
