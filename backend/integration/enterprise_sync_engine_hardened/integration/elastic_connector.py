from sync_engine.base_connector import BaseConnector
from sync_engine.models import HealthCheckResult

class ElasticConnector(BaseConnector):
    name = "elastic_connector"
    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(status="healthy", message="Elastic online")
    async def discover(self):
        return [{"id": "es-doc-1"}]
    async def normalization(self, record):
        return {"normalized_id": record.get("id"), "source": self.name}
    async def ingest(self, records):
        return len(records)
