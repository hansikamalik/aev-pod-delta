from typing import Dict, Any
from .base import AzureBaseNormalizer


class FunctionAppNormalizer(AzureBaseNormalizer):
    """Normalizes Microsoft.Web/sites (kind: functionapp) ARM objects."""

    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        metadata = self.extract_common_metadata(raw_data)
        properties = raw_data.get("properties", {})
        site_config = properties.get("siteConfig", {})

        # Parse runtime stack from linuxFxVersion or netFrameworkVersion
        runtime = site_config.get("linuxFxVersion") or site_config.get("netFrameworkVersion")

        # Parse comma-separated outbound IPs into an array
        outbound_ips_raw = properties.get("outboundIpAddresses", "")
        ip_list = (
            [ip.strip() for ip in outbound_ips_raw.split(",") if ip.strip()]
            if isinstance(outbound_ips_raw, str)
            else []
        )

        return {
            "asset_id": metadata["asset_id"],
            "name": metadata["name"],
            "cloud_provider": "azure",
            "resource_type": "serverless",
            "native_type": "Microsoft.Web/sites",
            "region": metadata["region"],
            "subscription_id": metadata["subscription_id"],
            "resource_group": metadata["resource_group"],
            "tags": metadata["tags"],
            "normalized_at": metadata["normalized_at"],
            "attributes": {
                "kind": raw_data.get("kind", "functionapp"),
                "state": properties.get("state"),
                "runtime": runtime,
                "https_only": properties.get("httpsOnly", True),
                "outbound_ip_addresses": ip_list,
                "default_host_name": properties.get("defaultHostName")
            }
        }
