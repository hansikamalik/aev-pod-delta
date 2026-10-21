from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from sync_engine.models import HealthCheckResult


class BaseConnector(ABC):
    """Abstract base connector for all 21 enterprise integrations."""

    def __init__(self, connector_id: str, credentials: Optional[Dict[str, Any]] = None):
        self.connector_id = connector_id
        self.credentials = credentials or {}

    @abstractmethod
    async def health_check(self) -> HealthCheckResult:
        pass
