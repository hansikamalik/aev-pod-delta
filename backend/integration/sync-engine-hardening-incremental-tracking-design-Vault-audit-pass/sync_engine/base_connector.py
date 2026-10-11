from abc import ABC, abstractmethod
from typing import List, Dict, Any
from sync_engine.models import HealthCheckResult, SyncResult
from sync_engine.vault_audit import VaultAuditLogger


class BaseConnector(ABC):
    def __init__(self, connector_id: str, platform_client: Any):
        self.connector_id = connector_id
        self.platform_client = platform_client
        self.audit_logger = VaultAuditLogger(service_name=connector_id)

    @abstractmethod
    async def health_check(self) -> HealthCheckResult:
        pass

    @abstractmethod
    async def discover(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def ingest(self, start_time: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def sync(self) -> SyncResult:
        pass
