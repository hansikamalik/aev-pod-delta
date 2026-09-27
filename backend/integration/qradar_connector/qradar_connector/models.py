from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

# SDK Normalized Asset Category standard enum values
ASSET_TYPE_COMPUTE = "compute"
ASSET_TYPE_STORAGE = "storage"
ASSET_TYPE_IDENTITY = "identity"
ASSET_TYPE_NETWORK = "network"
ASSET_TYPE_TICKET = "ticket"
ASSET_TYPE_DETECTION = "detection"
ASSET_TYPE_OTHER = "other"


@dataclass
class Asset:
    """SDK standard Asset representation."""
    id: str
    source: str
    type: str
    name: str
    raw: Dict[str, Any]
    discoveredAt: datetime = field(default_factory=datetime.now)
    tags: Optional[Dict[str, str]] = field(default_factory=dict)


@dataclass
class SyncResult:
    """SDK standard outcome of a sync run."""
    connector: str
    status: str  # "success" | "partial" | "failed"
    assets_discovered: int
    assets_pushed: int
    errors: list
    started_at: datetime
    completed_at: datetime
