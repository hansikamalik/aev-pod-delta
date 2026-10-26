from sync_engine.base_connector import BaseConnector
from sync_engine.models import HealthCheckResult

class ServiceNowConnector(BaseConnector):
    name = "servicenow-connector"
    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(status="healthy", message="ServiceNow online")
    async def discover(self):
        return [{"id": "INC0001"}]
    async def normalization(self, record):
        return {"normalized_id": record.get("id"), "source": self.name}
    async def ingest(self, records):
        return len(records)
