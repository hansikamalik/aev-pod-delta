from sync_engine.base_connector import BaseConnector
from sync_engine.models import HealthCheckResult

class ConnectorSentinelOne(BaseConnector):
    name = "connector-sentinelone"
    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(status="healthy", message="SentinelOne online")
    async def discover(self):
        return [{"id": "s1-agent-1"}]
    async def normalization(self, record):
        return {"normalized_id": record.get("id"), "source": self.name}
    async def ingest(self, records):
        return len(records)
