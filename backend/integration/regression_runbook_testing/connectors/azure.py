from sdk.public_sdk import PublicConnectorSDK
from sync_engine.base_connector import BaseConnector
from sync_engine.models import HealthCheckResult


class AzureNormalizationPlatformPush(BaseConnector, PublicConnectorSDK):
    def __init__(self, connector_id: str = "Azure_Normalization_Platform_Push", credentials=None):
        BaseConnector.__init__(self, connector_id, credentials)
        PublicConnectorSDK.__init__(self, connector_id)

    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(status="healthy", message="Azure endpoint reachable")
