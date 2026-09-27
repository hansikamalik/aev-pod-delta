from abc import ABC
from datetime import datetime
import logging
from typing import Any, Dict, Iterable, List

from qradar_connector.client import MockPlatformClient, QRadarClient
from qradar_connector.config import get_config_schema, get_credentials_schema
from qradar_connector.models import (
    ASSET_TYPE_COMPUTE,
    ASSET_TYPE_DETECTION,
    ASSET_TYPE_NETWORK,
    ASSET_TYPE_OTHER,
    Asset,
    SyncResult
)

logger = logging.getLogger(__name__)


class Connector(ABC):
    """Abstract Connector base matching the SDK lifecycle contract."""
    pass


class QRadarConnector(Connector):
    """QRadar Connector implementation adhering strictly to SDK Contract v2."""

    name = "qradar"

    def __init__(self, config: Dict[str, Any], credentials: Dict[str, Any]):
        self.config = config
        self.credentials = credentials
        
        self.client = QRadarClient(
            host=self.config.get("host", ""),
            sec_token=self.credentials.get("sec_token", ""),
            verify_ssl=self.config.get("verify_ssl", True),
            api_version=self.config.get("api_version", "19.0")
        )
        self.platform_client = MockPlatformClient()

    def check_health(self) -> bool:
        """Lightweight connectivity check."""
        return self.client.ping()

    def describe_config(self) -> dict:
        """Returns non-secret JSON schema for configuration."""
        return get_config_schema()

    def describe_credentials(self) -> dict:
        """Returns JSON schema for required secrets."""
        return get_credentials_schema()

    def _normalize_asset_type(self, raw_asset: Dict[str, Any]) -> str:
        """Maps QRadar specific resource fields into standard SDK AssetType categories."""
        interfaces = raw_asset.get("interfaces", [])
        has_ip = any(ip.get("ip_address") for interface in interfaces for ip in interface.get("ip_addresses", []))
        
        if raw_asset.get("offense_count", 0) > 0:
            return ASSET_TYPE_DETECTION
        elif has_ip:
            return ASSET_TYPE_NETWORK
        elif raw_asset.get("host_names"):
            return ASSET_TYPE_COMPUTE
        return ASSET_TYPE_OTHER

    def _extract_name(self, raw_asset: Dict[str, Any], asset_id: str) -> str:
        """Extracts human-readable name from QRadar asset payload."""
        hostnames = raw_asset.get("host_names", [])
        if hostnames and len(hostnames) > 0:
            name = hostnames[0].get("name")
            if name:
                return name
        
        interfaces = raw_asset.get("interfaces", [])
        for net_if in interfaces:
            for ip in net_if.get("ip_addresses", []):
                if ip.get("ip_address"):
                    return ip["ip_address"]
                    
        return f"QRadar-Asset-{asset_id}"

    def discover(self) -> Iterable[Asset]:
        """Reads asset records from QRadar, converts them into normalized Assets, and yields them."""
        for raw_item in self.client.list_assets():
            qradar_id = raw_item.get("id")
            if qradar_id is None:
                continue

            asset_id = str(qradar_id)
            asset_type = self._normalize_asset_type(raw_item)
            asset_name = self._extract_name(raw_item, asset_id)

            tags = {}
            if "domain_id" in raw_item:
                tags["domain_id"] = str(raw_item["domain_id"])

            yield Asset(
                id=asset_id,
                source=self.name,
                type=asset_type,
                name=asset_name,
                raw=raw_item,
                discoveredAt=datetime.now(),
                tags=tags
            )

    def ingest(self, assets: Iterable[Asset]) -> int:
        """Pushes normalized assets to the platform service."""
        asset_list = list(assets)
        if not asset_list:
            return 0
            
        pushed_count = self.platform_client.bulk_upsert(asset_list)
        return pushed_count

    async def sync(self) -> SyncResult:
        """Executes the standard sync workflow: discover -> ingest -> SyncResult."""
        started_at = datetime.now()
        errors = []
        discovered_assets: List[Asset] = []
        pushed_count = 0

        try:
            discovered_assets = list(self.discover())
        except Exception as exc:
            logger.error(f"Error during QRadar discovery phase: {exc}")
            errors.append({
                "operation": "discover",
                "source": self.name,
                "message": str(exc),
                "timestamp": datetime.now().isoformat()
            })

        if discovered_assets and not errors:
            try:
                pushed_count = self.ingest(discovered_assets)
            except Exception as exc:
                logger.error(f"Error during platform ingestion phase: {exc}")
                errors.append({
                    "operation": "ingest",
                    "source": self.name,
                    "message": str(exc),
                    "timestamp": datetime.now().isoformat()
                })

        if not errors and len(discovered_assets) == pushed_count:
            status = "success"
        elif pushed_count > 0 and pushed_count < len(discovered_assets):
            status = "partial"
        else:
            status = "failed"

        return SyncResult(
            connector=self.name,
            status=status,
            assets_discovered=len(discovered_assets),
            assets_pushed=pushed_count,
            errors=errors,
            started_at=started_at,
            completed_at=datetime.now()
        )
