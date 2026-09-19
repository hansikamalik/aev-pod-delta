"""
Shared data models and Connector interface.

These mirror the contract frozen in Week 1 between the Integration squad
and the Connector SDK squad: every connector produces `Asset` objects and
reports back a `SyncResult`, and every connector implements the same
six-method `Connector` interface (discover, ingest, sync, health_check,
describe_config, describe_credentials).

In the real repo these live in the `connector_sdk` package. They're
reproduced here so this module is self-contained and testable on its own.
"""

from __future__ import annotations

import abc
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    USER = "user"
    GROUP = "group"


class AssetStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"


class Asset(BaseModel):
    """The normalized shape every connector must map its source data into."""

    external_id: str = Field(..., description="ID in the source system (Okta user/group id)")
    source: str = Field(..., description="Connector name, e.g. 'okta'")
    asset_type: AssetType
    name: str
    status: AssetStatus = AssetStatus.UNKNOWN
    attributes: Dict[str, Any] = Field(default_factory=dict)
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SyncResult(BaseModel):
    """What a connector returns after a sync run."""

    connector: str
    started_at: datetime
    finished_at: datetime
    assets_discovered: int
    assets_pushed: int
    errors: List[str] = Field(default_factory=list)

    @property
    def success(self) -> bool:
        return not self.errors


class Connector(abc.ABC):
    """Shared connector contract, agreed between Integration and SDK squads."""

    @abc.abstractmethod
    def discover(self) -> List[Dict[str, Any]]:
        """Pull raw records from the source system."""

    @abc.abstractmethod
    def normalize(self, raw_records: List[Dict[str, Any]]) -> List[Asset]:
        """Map raw source records into the shared Asset shape."""

    @abc.abstractmethod
    def sync(self) -> SyncResult:
        """Run discover -> normalize -> push, end to end."""

    @abc.abstractmethod
    def health_check(self) -> bool:
        """Return True if the connector can currently reach its source."""

    @abc.abstractmethod
    def describe_config(self) -> Dict[str, Any]:
        """JSON-schema-like description of this connector's config options."""

    @abc.abstractmethod
    def describe_credentials(self) -> Dict[str, Any]:
        """JSON-schema-like description of the credentials this connector needs."""
