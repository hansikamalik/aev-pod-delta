"""
Data models shared by every connector in the platform.

Asset       - a normalized representation of any discovered resource
              (an EC2 instance, an Okta user, a Jira ticket, etc).
SyncResult  - the outcome of running a connector's sync() method.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    """Coarse category for a discovered asset. Extend as new connectors
    introduce new kinds of resources."""

    COMPUTE = "compute"
    STORAGE = "storage"
    IDENTITY = "identity"
    NETWORK = "network"
    TICKET = "ticket"
    DETECTION = "detection"
    OTHER = "other"


class Asset(BaseModel):
    """A single normalized resource discovered by a connector.

    Every connector must translate whatever it finds (an S3 bucket, an
    Okta user, a Jira issue...) into this shape before pushing it to the
    platform's asset service.
    """

    id: str = Field(..., description="Stable unique ID, scoped to the source system")
    source: str = Field(..., description="Name of the connector/source, e.g. 'aws', 'okta'")
    type: AssetType = Field(..., description="Coarse category of the asset")
    name: str = Field(..., description="Human-readable name")
    raw: dict[str, Any] = Field(default_factory=dict, description="Original, unnormalized payload")
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: dict[str, str] = Field(default_factory=dict)


class SyncStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class SyncResult(BaseModel):
    """Outcome of a single connector sync run."""

    connector: str = Field(..., description="Name of the connector that ran")
    status: SyncStatus
    assets_discovered: int = 0
    assets_pushed: int = 0
    errors: list[str] = Field(default_factory=list)
    started_at: datetime
    finished_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def duration_seconds(self) -> float:
        return (self.finished_at - self.started_at).total_seconds()
