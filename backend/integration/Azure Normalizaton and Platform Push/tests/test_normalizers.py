import pytest
from src.normalizers.vm import VMNormalizer
from src.normalizers.storage import StorageNormalizer
from src.normalizers.aad import AADNormalizer
from src.normalizers.sql import SQLNormalizer
from src.normalizers.functions import FunctionAppNormalizer


class TestNormalizersUnit:

    def test_vm_normalizer_malformed_missing_fields(self):
        # Raw VM payload missing properties block completely
        raw_malformed = {
            "id": "/subscriptions/sub-123/resourceGroups/rg-1/providers/Microsoft.Compute/virtualMachines/vm-broken",
            "name": "vm-broken",
            "location": "westus"
        }
        normalizer = VMNormalizer()
        result = normalizer.normalize(raw_malformed)

        assert result["asset_id"] == raw_malformed["id"]
        assert result["attributes"]["os_type"] == "unknown"
        assert result["attributes"]["vm_size"] is None
        assert result["attributes"]["network_interface_ids"] == []

    def test_storage_normalizer_standard(self):
        raw_storage = {
            "id": "/subscriptions/sub-123/resourceGroups/rg-1/providers/Microsoft.Storage/storageAccounts/st01",
            "name": "st01",
            "location": "eastus",
            "sku": {"name": "Standard_LRS", "tier": "Standard"},
            "properties": {"supportsHttpsTrafficOnly": True, "accessTier": "Hot"}
        }
        normalizer = StorageNormalizer()
        result = normalizer.normalize(raw_storage)

        assert result["resource_type"] == "storage"
        assert result["attributes"]["sku_name"] == "Standard_LRS"
        assert result["attributes"]["supports_https_only"] is True

    def test_aad_normalizer_user_and_group(self):
        raw_user = {"id": "user-guid-123", "userPrincipalName": "user@domain.com", "accountEnabled": True}
        normalizer = AADNormalizer()
        user_result = normalizer.normalize(raw_user)

        assert user_result["native_type"] == "Microsoft.Graph/users"
        assert user_result["asset_id"] == "azure:aad:user-guid-123"

    def test_sql_normalizer_standard(self):
        raw_sql = {
            "id": "/subscriptions/sub-123/resourceGroups/rg-1/providers/Microsoft.Sql/servers/srv1/databases/db1",
            "name": "db1",
            "location": "eastus",
            "sku": {"tier": "GeneralPurpose", "name": "GP_Gen5_2"},
            "properties": {"status": "Online"}
        }
        normalizer = SQLNormalizer()
        result = normalizer.normalize(raw_sql)

        assert result["resource_type"] == "database"
        assert result["attributes"]["edition"] == "GeneralPurpose"

    def test_function_app_normalizer_runtime_parsing(self):
        raw_func = {
            "id": "/subscriptions/sub-123/resourceGroups/rg-1/providers/Microsoft.Web/sites/func1",
            "name": "func1",
            "kind": "functionapp,linux",
            "properties": {
                "siteConfig": {"linuxFxVersion": "PYTHON|3.11"},
                "outboundIpAddresses": "10.0.0.1, 10.0.0.2"
            }
        }
        normalizer = FunctionAppNormalizer()
        result = normalizer.normalize(raw_func)

        assert result["attributes"]["runtime"] == "PYTHON|3.11"
        assert len(result["attributes"]["outbound_ip_addresses"]) == 2
