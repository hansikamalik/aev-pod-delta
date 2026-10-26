from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Asset(BaseModel):
    id: str
    source: str
    type: str = "other"
    name: str
    raw: Dict[str, Any] = Field(default_factory=dict)
    tags: Dict[str, str] = Field(default_factory=dict)


class SyncResult(BaseModel):
    connector: str = "default_connector"
    status: str = "success"
    assets_pushed: int = 0
    assets_discovered: int = 0
    assets_skipped: int = 0
    high_water_mark: Optional[str] = None
    last_sync_at: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    vault_audit_passed: bool = True
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class HealthCheckResult(BaseModel):
    status: str = "healthy"
    message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class Checkpoint(BaseModel):
    high_water_mark: Optional[str] = None
    last_sync_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

