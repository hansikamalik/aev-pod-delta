from sync_engine.base_connector import BaseConnector
from sync_engine.models import HealthCheckResult

class ActiveDirectoryConnector(BaseConnector):
    name = "active-directory-connector"
    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(status="healthy", message="Active Directory online")
    async def discover(self):
        return [{"id": "ad-sid-1", "samAccountName": "admin"}]
    async def normalization(self, record):
        return {"normalized_id": record.get("id"), "source": self.name}
    async def ingest(self, records):
        return len(records)
