from sync_engine.base_connector import BaseConnector
from sync_engine.models import HealthCheckResult
from typing import Dict, Any, Optional


class AzureNormalizationPlatformPush(BaseConnector):
    name = "Azure_Normalization_Platform_Push"

    def __init__(self, connector_id: str = "Azure_Normalization_Platform_Push", credentials: Optional[Dict[str, Any]] = None):
        super().__init__(connector_id=connector_id, credentials=credentials)

    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(status="healthy", message="Azure connector online")
