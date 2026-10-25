"""
Data models and schemas for the Integration Service Management REST API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNTESTED = "untested"


class SyncJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


# ---- Catalog Schemas --------------------------------------------------------

class CatalogItem(BaseModel):
    connector_type: str = Field(..., description="Unique connector identifier, e.g. 'aws', 'jira'")
    name: str = Field(..., description="Display name, e.g. 'Amazon Web Services'")
    category: str = Field(..., description="Category, e.g. 'cloud', 'edr', 'identity', 'itsm'")
    config_schema: Dict[str, Any] = Field(default_factory=dict)
    credential_schema: Dict[str, Any] = Field(default_factory=dict)


# ---- Integration CRUD Schemas ----------------------------------------------

class IntegrationCreate(BaseModel):
    name: str = Field(..., description="User-assigned display name for this connection")
    connector_type: str = Field(..., description="Connector identifier from the catalog")
    config: Dict[str, Any] = Field(default_factory=dict, description="Non-secret configuration")
    credentials: Dict[str, Any] = Field(default_factory=dict, description="Secret credentials")
    schedule: Optional[str] = Field(default="every 1h", description="Sync schedule frequency")
    enabled: bool = Field(default=True, description="Whether sync schedules are enabled")


class IntegrationUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    credentials: Optional[Dict[str, Any]] = None
    schedule: Optional[str] = None
    enabled: Optional[bool] = None


class IntegrationResponse(BaseModel):
    id: str
    name: str
    connector_type: str
    config: Dict[str, Any]
    credentials_configured: bool = Field(
        ..., description="True if credentials are set (secrets are masked)"
    )
    enabled: bool
    schedule: Optional[str] = None
    health_status: HealthStatus = HealthStatus.UNTESTED
    last_health_check_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    last_assets_discovered: int = 0
    created_at: datetime
    updated_at: datetime


# ---- Sync Job Schemas -------------------------------------------------------

class SyncJobResponse(BaseModel):
    job_id: str
    integration_id: str
    connector_type: str
    status: SyncJobStatus
    assets_discovered: int = 0
    assets_pushed: int = 0
    errors: List[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    started_at: datetime
    finished_at: Optional[datetime] = None


class HealthCheckResponse(BaseModel):
    integration_id: str
    connector_type: str
    healthy: bool
    status: HealthStatus
    checked_at: datetime
    message: str


# ---- Checkpoint Schemas (P1-2) ----------------------------------------------

class SyncCheckpoint(BaseModel):
    integration_id: str
    last_sync_time: datetime
    last_cursor: Optional[str] = Field(default=None, description="Incremental high-watermark or pagination cursor")
    status: str
    assets_discovered: int = 0
    assets_pushed: int = 0
    updated_at: datetime

