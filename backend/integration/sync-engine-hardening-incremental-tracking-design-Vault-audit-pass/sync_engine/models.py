from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Asset(BaseModel):
    id: str
    source: str
    type: str = "detection"
    name: str
    raw: Dict[str, Any] = Field(default_factory=dict)
    discoveredAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: Dict[str, Any] = Field(default_factory=dict)


class Checkpoint(BaseModel):
    connector: str
    last_sync_timestamp: Optional[datetime] = None
    cursor: Optional[str] = None
    high_water_mark_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SyncResult(BaseModel):
    status: str
    assets_discovered: int = 0
    assets_pushed: int = 0
    checkpoint: Optional[Checkpoint] = None
    errors: List[str] = Field(default_factory=list)
