from sync_engine.base_connector import BaseConnector
from sync_engine.models import HealthCheckResult

class ConnectorGitLab(BaseConnector):
    name = "connector-gitlab"
    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(status="healthy", message="GitLab connector online")
    async def discover(self):
        return [{"id": "gl-project-1"}]
    async def normalization(self, record):
        return {"normalized_id": record.get("id"), "source": self.name}
    async def ingest(self, records):
        return len(records)
