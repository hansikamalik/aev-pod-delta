"""
Shared Asset/finding shape.

Two shapes come out of this connector, matching the sprint plan's
"map to the shared Asset/finding shape":
- Asset: a persistent resource (user, group, device, domain, license).
- Finding: an event (currently: a Graph API directory audit log entry).

Both are this connector's best guess at the real shared schema — confirm
against whatever Normalization/AI Context actually ship before merging.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class AssetType(str, Enum):
    USER = "user"
    GROUP = "group"
    DEVICE = "device"
    DOMAIN = "domain"
    LICENSE = "license"


class AssetStatus(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


@dataclass
class Asset:
    asset_id: str
    asset_type: AssetType
    display_name: str
    source_connector: str
    status: AssetStatus = AssetStatus.UNKNOWN
    owner: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    discovered_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type.value,
            "display_name": self.display_name,
            "source_connector": self.source_connector,
            "status": self.status.value,
            "owner": self.owner,
            "tags": self.tags,
            "metadata": self.metadata,
            "discovered_at": self.discovered_at,
        }


@dataclass
class Finding:
    finding_id: str
    finding_type: str  # e.g. "audit_log"
    source_connector: str
    activity: str
    actor: Optional[str] = None
    target: Optional[str] = None
    result: str = "unknown"  # "success" | "failure" | "unknown"
    occurred_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    discovered_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "finding_type": self.finding_type,
            "source_connector": self.source_connector,
            "activity": self.activity,
            "actor": self.actor,
            "target": self.target,
            "result": self.result,
            "occurred_at": self.occurred_at,
            "metadata": self.metadata,
            "discovered_at": self.discovered_at,
        }
