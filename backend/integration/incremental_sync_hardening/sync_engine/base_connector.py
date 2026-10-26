from typing import Any, Dict, Optional, Iterable
from sync_engine.models import HealthCheckResult, SyncResult


class BaseConnector:
    """Base class for all connectors adhering to SDK specifications[cite: 2]."""
    name: str = "unnamed"

    def __init__(self, connector_id: str = "base", credentials: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None):
        self.connector_id = connector_id
        self.credentials = credentials or {}
        self.config = config or {}

    def discover(self) -> Iterable[Any]:
        raise NotImplementedError

    def ingest(self, assets: Iterable[Any]) -> int:
        raise NotImplementedError

    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(status="healthy")

    def describe_config(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    def describe_credentials(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}
