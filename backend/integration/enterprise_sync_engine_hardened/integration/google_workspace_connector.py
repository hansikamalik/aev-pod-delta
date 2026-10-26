from sync_engine.base_connector import BaseConnector
from sync_engine.models import HealthCheckResult

class GoogleWorkspaceConnector(BaseConnector):
    name = "google-workspace-connector"
    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(status="healthy", message="Google Workspace online")
    async def discover(self):
        return [{"id": "gw-user-1"}]
    async def normalization(self, record):
        return {"normalized_id": record.get("id"), "source": self.name}
    async def ingest(self, records):
        return len(records)
