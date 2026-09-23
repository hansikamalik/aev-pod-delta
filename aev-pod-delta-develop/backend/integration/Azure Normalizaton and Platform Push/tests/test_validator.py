import pytest
from src.validator import AssetValidator


class TestValidatorUnit:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.validator = AssetValidator()

    def test_valid_vm_payload_passes(self):
        valid_payload = {
            "asset_id": "/subscriptions/sub-123/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm1",
            "name": "vm1",
            "cloud_provider": "azure",
            "resource_type": "compute",
            "native_type": "Microsoft.Compute/virtualMachines",
            "region": "eastus",
            "subscription_id": "sub-123",
            "resource_group": "rg1",
            "tags": {},
            "normalized_at": "2026-09-04T12:00:00Z",
            "attributes": {
                "vm_size": "Standard_D2s_v3",
                "os_type": "linux",
                "provisioning_state": "Succeeded",
                "network_interface_ids": []
            }
        }
        is_valid, errors = self.validator.validate(valid_payload)
        assert is_valid is True
        assert len(errors) == 0

    def test_invalid_payload_fails(self):
        # Missing required 'os_type' field in attributes
        invalid_payload = {
            "asset_id": "sub-123/vm1",
            "name": "vm1",
            "cloud_provider": "azure",
            "resource_type": "compute",
            "native_type": "Microsoft.Compute/virtualMachines",
            "region": "eastus",
            "normalized_at": "2026-09-04T12:00:00Z",
            "attributes": {
                "vm_size": "Standard_D2s_v3"
            }
        }
        is_valid, errors = self.validator.validate(invalid_payload)
        assert is_valid is False
        assert len(errors) > 0
