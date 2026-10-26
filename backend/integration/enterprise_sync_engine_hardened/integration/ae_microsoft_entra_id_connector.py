from sync_engine.base_connector import BaseConnector
from sync_engine.models import HealthCheckResult

class MicrosoftEntraIDConnector(BaseConnector):
    name = "AEV-microsoft-entra-id-connector"
    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(status="healthy", message="Entra ID online")
    async def discover(self):
        return [{"id": "entra-user-1", "upn": "user@domain.com"}]
    async def normalization(self, record):
        return {"normalized_id": record.get("id"), "source": self.name}
    async def ingest(self, records):
        return len(records)
