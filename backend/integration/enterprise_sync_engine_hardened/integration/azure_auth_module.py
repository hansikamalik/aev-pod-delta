from sync_engine.base_connector import BaseConnector
from sync_engine.models import HealthCheckResult

class AzureAuthModule(BaseConnector):
    name = "azure-auth-module"
    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(status="healthy", message="Azure Auth online")
    async def discover(self):
        return [{"id": "az-token-1"}]
    async def normalization(self, record):
        return {"normalized_id": record.get("id"), "source": self.name}
    async def ingest(self, records):
        return len(records)
