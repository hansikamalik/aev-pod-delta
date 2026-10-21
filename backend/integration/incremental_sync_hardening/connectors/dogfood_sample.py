from sync_engine.base_connector import BaseConnector
from sync_engine.models import HealthCheckResult
from typing import Dict, Any, Optional


class DogfoodSampleConnector(BaseConnector):
    """Throwaway dogfood connector built using public SDK guidelines[cite: 2]."""
    name = "dogfood_sample"

    def __init__(self, connector_id: str = "dogfood_sample", credentials: Optional[Dict[str, Any]] = None):
        super().__init__(connector_id=connector_id, credentials=credentials)

    async def health_check(self) -> HealthCheckResult:
        token = self.credentials.get("active_token")
        if not token:
            return HealthCheckResult(status="unhealthy", message="Missing active Vault token")
        return HealthCheckResult(status="healthy", message="Dogfood connector online")
