from sync_engine.base_connector import BaseConnector
from sync_engine.models import HealthCheckResult

class Microsoft365Connector(BaseConnector):
    name = "microsoft365-connector"
    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(status="healthy", message="Microsoft 365 online")
    async def discover(self):
        return [{"id": "m365-user-1"}]
    async def normalization(self, record):
        return {"normalized_id": record.get("id"), "source": self.name}
    async def ingest(self, records):
        return len(records)
