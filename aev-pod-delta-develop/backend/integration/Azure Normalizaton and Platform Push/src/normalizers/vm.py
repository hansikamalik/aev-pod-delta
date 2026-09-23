from typing import Dict, Any
from .base import AzureBaseNormalizer


class VMNormalizer(AzureBaseNormalizer):
    """Normalizes Microsoft.Compute/virtualMachines ARM objects."""

    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        metadata = self.extract_common_metadata(raw_data)
        properties = raw_data.get("properties", {})
        hardware_profile = properties.get("hardwareProfile", {})
        storage_profile = properties.get("storageProfile", {})
        os_disk = storage_profile.get("osDisk", {})
        network_profile = properties.get("networkProfile", {})

        # Parse array of Network Interface IDs
        nic_ids = [
            nic.get("id") 
            for nic in network_profile.get("networkInterfaces", []) 
            if nic.get("id")
        ]

        os_type_raw = os_disk.get("osType", "unknown")
        os_type = os_type_raw.lower() if isinstance(os_type_raw, str) else "unknown"

        return {
            "asset_id": metadata["asset_id"],
            "name": metadata["name"],
            "cloud_provider": "azure",
            "resource_type": "compute",
            "native_type": "Microsoft.Compute/virtualMachines",
            "region": metadata["region"],
            "subscription_id": metadata["subscription_id"],
            "resource_group": metadata["resource_group"],
            "tags": metadata["tags"],
            "normalized_at": metadata["normalized_at"],
            "attributes": {
                "vm_size": hardware_profile.get("vmSize"),
                "os_type": os_type,
                "provisioning_state": properties.get("provisioningState"),
                "vm_id": properties.get("vmId"),
                "network_interface_ids": nic_ids
            }
        }
