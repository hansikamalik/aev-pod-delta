from typing import Any, Dict, Optional, Iterable
from sync_engine.models import HealthCheckResult, SyncResult, Asset


class BaseConnector:
    """Unified base class for all connectors adhering to standard contracts[cite: 3]."""
    name: str = "unnamed"

    def __init__(self, connector_id: str = "base", credentials: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None):
        self.connector_id = connector_id
        self.credentials = credentials or {}
        self.config = config or {}

    def discover(self) -> Iterable[Asset]:
        raise NotImplementedError

    def ingest(self, assets: Iterable[Asset]) -> int:
        raise NotImplementedError

    def sync(self) -> SyncResult:
        raise NotImplementedError

    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(status="healthy")

    def get_config_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    def describe_credentials(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}
