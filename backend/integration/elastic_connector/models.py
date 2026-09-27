from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AssetType(str, Enum):
    COMPUTE = "compute"
    STORAGE = "storage"
    IDENTITY = "identity"
    NETWORK = "network"
    TICKET = "ticket"
    DETECTION = "detection"
    OTHER = "other"


class Asset(BaseModel):
    id: str = Field(..., description="Stable, deterministic asset identifier")
    source: str = Field(..., description="Connector identity name")
    type: AssetType = Field(..., description="Normalized SDK asset category")
    name: str = Field(..., description="Human-readable asset name")
    raw: Dict[str, Any] = Field(..., description="Unmodified original payload")
    discoveredAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: Optional[Dict[str, str]] = None


class SyncResult(BaseModel):
    connector: str
    status: str  # "success" | "partial" | "failed"
    assets_discovered: int
    assets_pushed: int
    errors: List[Dict[str, Any]] = []
    started_at: datetime
    completed_at: datetime
