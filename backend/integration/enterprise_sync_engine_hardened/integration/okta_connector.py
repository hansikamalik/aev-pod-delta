from sync_engine.base_connector import BaseConnector
from sync_engine.models import HealthCheckResult

class OktaConnector(BaseConnector):
    name = "okta_connector"
    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(status="healthy", message="Okta online")
    async def discover(self):
        return [{"id": "okta-user-1"}]
    async def normalization(self, record):
        return {"normalized_id": record.get("id"), "source": self.name}
    async def ingest(self, records):
        return len(records)
