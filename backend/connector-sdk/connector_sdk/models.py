"""
Data models shared by every connector across the platform.

Asset       - Normalized representation of any discovered resource
              (EC2 instance, Okta user, Jira ticket, GCP bucket, Falcon host).
SyncResult  - Comprehensive outcome of a connector's sync execution.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from .exceptions import ValidationError


def utcnow() -> datetime:
    """Timezone-aware UTC current timestamp."""
    return datetime.now(timezone.utc)


class AssetType(str, Enum):
    """Normalized asset categories across all platform connectors."""

    COMPUTE = "compute"
    STORAGE = "storage"
    IDENTITY = "identity"
    NETWORK = "network"
    TICKET = "ticket"
    DETECTION = "detection"
    DATABASE = "database"
    APPLICATION = "application"
    OTHER = "other"


class Asset(BaseModel):
    """
    A single normalized resource discovered by any connector.

    Reconciles snake_case (discovered_at, raw) with camelCase (discoveredAt, rawPayload)
    so both modern and legacy connectors interoperate cleanly.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        extra="allow",
    )

    id: str = Field(..., description="Stable unique ID scoped to the source system")
    source: str = Field(default="generic", description="Name of the connector / source, e.g. 'aws', 'jira'")
    type: Union[AssetType, str] = Field(..., description="Category of the asset")
    name: str = Field(..., description="Human-readable resource name")
    raw: dict[str, Any] = Field(default_factory=dict, alias="raw_payload", description="Original source payload")
    discovered_at: datetime = Field(default_factory=utcnow, alias="discoveredAt", description="Discovery timestamp")
    tags: dict[str, str] = Field(default_factory=dict, description="Metadata tags")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Secondary metadata dictionary")

    @property
    def discoveredAt(self) -> datetime:
        """CamelCase alias for discovered_at."""
        return self.discovered_at

    @discoveredAt.setter
    def discoveredAt(self, value: datetime) -> None:
        self.discovered_at = value

    @property
    def raw_payload(self) -> dict[str, Any]:
        """Alias for raw source dictionary."""
        return self.raw

    def __eq__(self, other: Any) -> bool:
        """Equality comparison based on asset identity and data payload."""
        if not isinstance(other, Asset):
            return False
        return (
            self.id == other.id
            and self.source == other.source
            and str(self.type.value if hasattr(self.type, "value") else self.type)
            == str(other.type.value if hasattr(other.type, "value") else other.type)
            and self.name == other.name
            and self.raw == other.raw
            and self.tags == other.tags
            and self.metadata == other.metadata
        )

    def to_dict(self, camel_case: bool = False) -> dict[str, Any]:
        """
        Serialize using dual-key compatibility.
        Provides both discovered_at and discoveredAt to eliminate schema drift across squads.
        """
        disc_iso = self.discovered_at.isoformat() if hasattr(self.discovered_at, "isoformat") else str(self.discovered_at)
        type_str = self.type.value if hasattr(self.type, "value") else str(self.type)
        return {
            "id": self.id,
            "source": self.source,
            "type": type_str,
            "name": self.name,
            "raw": dict(self.raw) if self.raw else {},
            "raw_payload": dict(self.raw) if self.raw else {},
            "discovered_at": disc_iso,
            "discoveredAt": disc_iso,
            "tags": dict(self.tags) if self.tags else {},
            "metadata": dict(self.metadata) if self.metadata else {},
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Asset":
        """Instantiate an Asset from either camelCase or snake_case dictionary."""
        raw_data = dict(data)
        aid = raw_data.get("id")
        if not aid:
            raise ValidationError("Asset dictionary must contain an 'id'")
        atype = raw_data.get("type", AssetType.OTHER)
        name = raw_data.get("name", str(aid))
        source = raw_data.get("source", "generic")
        raw = raw_data.get("raw", raw_data.get("raw_payload", raw_data.get("rawPayload", {})))
        disc = raw_data.get("discovered_at", raw_data.get("discoveredAt"))
        disc_dt = utcnow()
        if isinstance(disc, datetime):
            disc_dt = disc if disc.tzinfo else disc.replace(tzinfo=timezone.utc)
        elif isinstance(disc, str):
            try:
                disc_dt = datetime.fromisoformat(disc.replace("Z", "+00:00"))
            except Exception:
                disc_dt = utcnow()
        tags = raw_data.get("tags", {})
        meta = raw_data.get("metadata", {})
        return cls(
            id=str(aid),
            source=str(source),
            type=atype,
            name=str(name),
            raw=dict(raw) if isinstance(raw, dict) else {},
            discovered_at=disc_dt,
            tags=dict(tags) if isinstance(tags, dict) else {},
            metadata=dict(meta) if isinstance(meta, dict) else {},
        )


class SyncStatus(str, Enum):
    """Status states for a connector synchronization execution."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class SyncResult(BaseModel):
    """
    Unified outcome of a single connector synchronization execution.

    Compatible with both Delta-4 SDK model attributes and legacy integration-hub stubs:
    - duration_seconds
    - success boolean
    - records_synced count
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="allow",
    )

    connector: str = Field(default="generic", description="Name of connector that executed")
    status: Union[SyncStatus, str] = Field(default=SyncStatus.SUCCESS)
    assets_discovered: int = 0
    assets_pushed: int = 0
    errors: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime = Field(default_factory=utcnow)

    def __init__(
        self,
        connector: Optional[str] = None,
        status: Optional[Union[SyncStatus, str]] = None,
        assets_discovered: Optional[int] = None,
        assets_pushed: Optional[int] = None,
        errors: Optional[list[str]] = None,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        success: Optional[bool] = None,
        records_synced: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        # Reconcile legacy parameters (success, records_synced)
        resolved_connector = connector or kwargs.get("source", "generic")
        resolved_errors = list(errors or kwargs.get("error_list", []))

        if status is not None:
            resolved_status = status
        elif success is not None:
            resolved_status = SyncStatus.SUCCESS if success else SyncStatus.FAILED
        else:
            resolved_status = SyncStatus.SUCCESS

        resolved_discovered = assets_discovered if assets_discovered is not None else (records_synced or 0)
        resolved_pushed = assets_pushed if assets_pushed is not None else resolved_discovered

        now = utcnow()
        start = started_at or kwargs.get("start_time", now)
        finish = finished_at or kwargs.get("end_time", now)

        super().__init__(
            connector=resolved_connector,
            status=resolved_status,
            assets_discovered=resolved_discovered,
            assets_pushed=resolved_pushed,
            errors=resolved_errors,
            started_at=start,
            finished_at=finish,
            **kwargs,
        )

    @property
    def duration_seconds(self) -> float:
        """Execution duration in seconds."""
        return (self.finished_at - self.started_at).total_seconds()

    @property
    def success(self) -> bool:
        """Legacy boolean check: True if status is SUCCESS with no recorded errors."""
        st = self.status.value if hasattr(self.status, "value") else str(self.status)
        return st.lower() == "success" and len(self.errors) == 0

    @property
    def records_synced(self) -> int:
        """Legacy attribute alias for assets_discovered."""
        return self.assets_discovered

    def add_error(self, error: Union[str, Exception]) -> None:
        """Add an error message and adjust sync status accordingly."""
        msg = str(error)
        self.errors.append(msg)
        if self.assets_pushed > 0:
            self.status = SyncStatus.PARTIAL
        else:
            self.status = SyncStatus.FAILED

    def to_dict(self) -> dict[str, Any]:
        """Serialize SyncResult into dictionary."""
        st = self.status.value if hasattr(self.status, "value") else str(self.status)
        return {
            "connector": self.connector,
            "status": st,
            "assets_discovered": self.assets_discovered,
            "assets_pushed": self.assets_pushed,
            "records_synced": self.records_synced,
            "success": self.success,
            "errors": list(self.errors),
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "duration_seconds": self.duration_seconds,
        }
