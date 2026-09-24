import json
import os
import pytest

from src.normalizers.vm import VMNormalizer
from src.normalizers.storage import StorageNormalizer
from src.normalizers.aad import AADNormalizer
from src.normalizers.sql import SQLNormalizer
from src.normalizers.functions import FunctionAppNormalizer
from src.validator import AssetValidator

# Locate fixtures directory relative to this test file
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(filename: str) -> dict:
    """Helper utility to read JSON mock files from tests/fixtures/."""
    file_path = os.path.join(FIXTURES_DIR, filename)
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestFixtureNormalizers:

    @pytest.fixture(autouse=True)
    def setup_validator(self):
        """Initializes the AssetValidator before running test cases."""
        schema_path = os.path.join(
            os.path.dirname(__file__), "..", "contracts", "azure_cam_schema.json"
        )
        if os.path.exists(schema_path):
            self.validator = AssetValidator(schema_path=schema_path)
        else:
            # Fallback to default class-level validation rules if schema file path is not set
            self.validator = AssetValidator

    def test_normalize_vm_fixture(self):
        # 1. Load mock JSON
        raw_payload = load_fixture("vm_raw.json")

        # 2. Normalize
        normalizer = VMNormalizer()
        normalized = normalizer.normalize(raw_payload)

        # 3. Assert schema validity
        is_valid, errors = self.validator.validate(normalized)
        assert is_valid, f"VM normalization schema validation failed: {errors}"

        # 4. Assert specific mapped fields
        assert normalized["resource_type"] == "compute"
        assert normalized["native_type"] == "Microsoft.Compute/virtualMachines"
        assert normalized["subscription_id"] == "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"
        assert normalized["resource_group"] == "rg-compute-prod"
        assert normalized["attributes"]["vm_size"] == "Standard_D4s_v5"
        assert normalized["attributes"]["os_type"] == "linux"
        assert len(normalized["attributes"]["network_interface_ids"]) == 1

    def test_normalize_storage_fixture(self):
        raw_payload = load_fixture("storage_raw.json")

        normalizer = StorageNormalizer()
        normalized = normalizer.normalize(raw_payload)

        is_valid, errors = self.validator.validate(normalized)
        assert is_valid, f"Storage normalization schema validation failed: {errors}"

        assert normalized["resource_type"] == "storage"
        assert normalized["native_type"] == "Microsoft.Storage/storageAccounts"
        assert normalized["attributes"]["sku_name"] == "Standard_GRS"
        assert normalized["attributes"]["supports_https_only"] is True
        assert normalized["attributes"]["access_tier"] is None  # Verifies edge case handling

    def test_normalize_aad_user_fixture(self):
        raw_payload = load_fixture("aad_user_raw.json")

        normalizer = AADNormalizer()
        normalized = normalizer.normalize(raw_payload)

        is_valid, errors = self.validator.validate(normalized)
        assert is_valid, f"AAD User normalization schema validation failed: {errors}"

        assert normalized["resource_type"] == "identity"
        assert normalized["native_type"] == "Microsoft.Graph/users"
        assert normalized["attributes"]["object_id"] == "e4d3c2b1-0a9b-8c7d-6e5f-4a3b2c1d0e9f"
        assert normalized["attributes"]["account_enabled"] is False  # Verifies disabled user edge case
        assert normalized["attributes"]["user_type"] == "Guest"

    def test_normalize_sql_db_fixture(self):
        raw_payload = load_fixture("sql_db_raw.json")

        normalizer = SQLNormalizer()
        normalized = normalizer.normalize(raw_payload)

        is_valid, errors = self.validator.validate(normalized)
        assert is_valid, f"SQL Database normalization schema validation failed: {errors}"

        assert normalized["resource_type"] == "database"
        assert normalized["native_type"] == "Microsoft.Sql/servers/databases"
        assert normalized["attributes"]["edition"] == "GeneralPurpose"
        assert normalized["attributes"]["status"] == "Restoring"  # Verifies state edge case
        assert normalized["attributes"]["max_size_bytes"] is None

    def test_normalize_function_app_fixture(self):
        raw_payload = load_fixture("function_app_raw.json")

        normalizer = FunctionAppNormalizer()
        normalized = normalizer.normalize(raw_payload)

        is_valid, errors = self.validator.validate(normalized)
        assert is_valid, f"Function App normalization schema validation failed: {errors}"

        assert normalized["resource_type"] == "serverless"
        assert normalized["native_type"] == "Microsoft.Web/sites"
        assert normalized["attributes"]["https_only"] is True
        assert normalized["attributes"]["runtime"] == "PYTHON|3.11"
        assert len(normalized["attributes"]["outbound_ip_addresses"]) == 3
