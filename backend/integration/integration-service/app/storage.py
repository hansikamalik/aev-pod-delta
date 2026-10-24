"""
In-memory and database-backed repository for Integration Service state.
Stores integration configurations and sync execution job history.
"""

from __future__ import annotations

import copy
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.models import HealthStatus, IntegrationCreate, IntegrationResponse, IntegrationUpdate, SyncJobResponse, SyncJobStatus

logger = logging.getLogger(__name__)


class IntegrationRecord:
    def __init__(
        self,
        id: str,
        name: str,
        connector_type: str,
        config: Dict[str, Any],
        credentials: Dict[str, Any],
        schedule: Optional[str] = "every 1h",
        enabled: bool = True,
    ):
        self.id = id
        self.name = name
        self.connector_type = connector_type
        self.config = config
        self.credentials = credentials
        self.schedule = schedule
        self.enabled = enabled
        self.health_status: HealthStatus = HealthStatus.UNTESTED
        self.last_health_check_at: Optional[datetime] = None
        self.last_sync_at: Optional[datetime] = None
        self.last_sync_status: Optional[str] = None
        self.last_assets_discovered: int = 0
        now = datetime.now(timezone.utc)
        self.created_at: datetime = now
        self.updated_at: datetime = now

    def to_response(self) -> IntegrationResponse:
        return IntegrationResponse(
            id=self.id,
            name=self.name,
            connector_type=self.connector_type,
            config=copy.deepcopy(self.config),
            credentials_configured=bool(self.credentials),
            enabled=self.enabled,
            schedule=self.schedule,
            health_status=self.health_status,
            last_health_check_at=self.last_health_check_at,
            last_sync_at=self.last_sync_at,
            last_sync_status=self.last_sync_status,
            last_assets_discovered=self.last_assets_discovered,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class IntegrationStorage:
    """Thread-safe state repository for integrations and sync jobs."""

    def __init__(self):
        self._integrations: Dict[str, IntegrationRecord] = {}
        self._sync_jobs: List[SyncJobResponse] = []

    def clear(self):
        self._integrations.clear()
        self._sync_jobs.clear()

    # ---- Integration Operations ---------------------------------------------

    def create(self, payload: IntegrationCreate) -> IntegrationResponse:
        integration_id = f"int-{uuid4().hex[:8]}"
        record = IntegrationRecord(
            id=integration_id,
            name=payload.name,
            connector_type=payload.connector_type,
            config=payload.config,
            credentials=payload.credentials,
            schedule=payload.schedule,
            enabled=payload.enabled,
        )
        self._integrations[integration_id] = record
        return record.to_response()

    def list_all(self, connector_type: Optional[str] = None, enabled: Optional[bool] = None) -> List[IntegrationResponse]:
        results: List[IntegrationResponse] = []
        for record in self._integrations.values():
            if connector_type and record.connector_type != connector_type:
                continue
            if enabled is not None and record.enabled != enabled:
                continue
            results.append(record.to_response())
        # Sort by created_at descending
        results.sort(key=lambda r: r.created_at, reverse=True)
        return results

    def get(self, integration_id: str) -> Optional[IntegrationResponse]:
        record = self._integrations.get(integration_id)
        return record.to_response() if record else None

    def get_record(self, integration_id: str) -> Optional[IntegrationRecord]:
        return self._integrations.get(integration_id)

    def update(self, integration_id: str, payload: IntegrationUpdate) -> Optional[IntegrationResponse]:
        record = self._integrations.get(integration_id)
        if not record:
            return None

        if payload.name is not None:
            record.name = payload.name
        if payload.config is not None:
            record.config.update(payload.config)
        if payload.credentials is not None:
            record.credentials.update(payload.credentials)
        if payload.schedule is not None:
            record.schedule = payload.schedule
        if payload.enabled is not None:
            record.enabled = payload.enabled

        record.updated_at = datetime.now(timezone.utc)
        return record.to_response()

    def delete(self, integration_id: str) -> bool:
        if integration_id in self._integrations:
            del self._integrations[integration_id]
            return True
        return False

    def update_health(self, integration_id: str, healthy: bool):
        record = self._integrations.get(integration_id)
        if record:
            record.health_status = HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY
            record.last_health_check_at = datetime.now(timezone.utc)
            record.updated_at = datetime.now(timezone.utc)

    def update_sync_results(self, integration_id: str, status: str, assets_discovered: int):
        record = self._integrations.get(integration_id)
        if record:
            record.last_sync_at = datetime.now(timezone.utc)
            record.last_sync_status = status.upper()
            record.last_assets_discovered = assets_discovered
            record.updated_at = datetime.now(timezone.utc)

    # ---- Sync Job Operations ------------------------------------------------

    def record_job(self, job: SyncJobResponse):
        self._sync_jobs.append(job)

    def get_jobs_for_integration(self, integration_id: str, limit: int = 50) -> List[SyncJobResponse]:
        jobs = [j for j in self._sync_jobs if j.integration_id == integration_id]
        jobs.sort(key=lambda j: j.started_at, reverse=True)
        return jobs[:limit]

    def list_all_jobs(self, limit: int = 100) -> List[SyncJobResponse]:
        jobs = list(self._sync_jobs)
        jobs.sort(key=lambda j: j.started_at, reverse=True)
        return jobs[:limit]


# Global storage singleton
storage = IntegrationStorage()
