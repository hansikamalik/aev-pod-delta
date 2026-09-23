import os
import shutil
import pytest
import requests_mock
from src.pipeline import AzureNormalizationPipeline


class TestEndToEndPipelineIntegration:

    @pytest.fixture(autouse=True)
    def setup_directories(self):
        self.dlq_dir = "tests/integration_dlq_output"
        os.makedirs(self.dlq_dir, exist_ok=True)
        yield
        if os.path.exists(self.dlq_dir):
            shutil.rmtree(self.dlq_dir)

    def _generate_mock_dataset(self) -> list:
        """Generates 55 mixed raw Azure asset payloads including edge cases."""
        payloads = []

        # 10 VMs
        for i in range(10):
            payloads.append({
                "id": f"/subscriptions/sub-01/resourceGroups/rg-compute/providers/Microsoft.Compute/virtualMachines/vm-{i}",
                "name": f"vm-{i}",
                "type": "Microsoft.Compute/virtualMachines",
                "location": "eastus",
                "properties": {
                    "hardwareProfile": {"vmSize": "Standard_D2s_v3"},
                    "storageProfile": {"osDisk": {"osType": "Linux"}},
                    "provisioningState": "Succeeded"
                }
            })

        # 10 Storage Accounts
        for i in range(10):
            payloads.append({
                "id": f"/subscriptions/sub-01/resourceGroups/rg-storage/providers/Microsoft.Storage/storageAccounts/st{i}",
                "name": f"st{i}",
                "type": "Microsoft.Storage/storageAccounts",
                "location": "westeurope",
                "sku": {"name": "Standard_LRS"},
                "properties": {"supportsHttpsTrafficOnly": True}
            })

        # 10 AAD Users
        for i in range(10):
            payloads.append({
                "id": f"aad-user-guid-{i}",
                "userPrincipalName": f"user{i}@company.com",
                "displayName": f"User {i}",
                "accountEnabled": True
            })

        # 10 SQL Databases
        for i in range(10):
            payloads.append({
                "id": f"/subscriptions/sub-01/resourceGroups/rg-db/providers/Microsoft.Sql/servers/sql-srv/databases/db-{i}",
                "name": f"db-{i}",
                "type": "Microsoft.Sql/servers/databases",
                "location": "eastus2",
                "sku": {"tier": "GeneralPurpose"},
                "properties": {"status": "Online"}
            })

        # 10 Function Apps
        for i in range(10):
            payloads.append({
                "id": f"/subscriptions/sub-01/resourceGroups/rg-func/providers/Microsoft.Web/sites/func-{i}",
                "name": f"func-{i}",
                "type": "Microsoft.Web/sites",
                "kind": "functionapp",
                "properties": {"httpsOnly": True}
            })

        # 5 Malformed Edge-Case Payloads (Designed to trigger DLQ)
        for i in range(5):
            payloads.append({
                "id": f"unsupported-type-{i}",
                "type": "Microsoft.Unknown/unsupportedResources",
                "location": "global"
            })

        return payloads

    def test_full_pipeline_e2e(self, requests_mock):
        endpoint = "https://platform.api.com/v1/ingest"
        requests_mock.post(endpoint, status_code=200, json={"status": "received"})

        dataset = self._generate_mock_dataset()
        assert len(dataset) == 55

        pipeline = AzureNormalizationPipeline(
            endpoint_url=endpoint,
            api_key="integration-test-key",
            dlq_dir=self.dlq_dir
        )

        results = pipeline.process_raw_payloads(dataset)

        # Verification Assertions
        assert results["total"] == 50  # 50 valid normalized assets
        assert results["successful"] == 50
        assert results["failed"] == 0
        assert results["validation_failed_count"] == 5  # 5 invalid landed in DLQ
        assert len(results["dlq_files"]) == 1
        assert os.path.exists(results["dlq_files"][0])
