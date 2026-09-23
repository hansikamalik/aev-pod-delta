"""
Shared Connector interface.

TODO(Bhavesh): Replace this stub with the real import from the shared
Connector SDK package once you have the path, e.g.:

    from connector_sdk.base import Connector, Asset, Finding, SyncResult

This stub exists so the module is runnable/testable standalone before
wiring to the shared package. Method signatures mirror the 6-method
Python ABC referenced in the Connector SDK squad's plan (the same
interface the TypeScript SDK is built to match).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class Asset:
    """Normalized asset shape shared across all connectors."""
    external_id: str
    source: str
    asset_type: str
    name: str
    raw: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None


@dataclass
class Finding:
    """Normalized finding/alert shape shared across all connectors."""
    external_id: str
    source: str
    severity: str
    title: str
    description: str
    asset_external_id: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)
    detected_at: Optional[str] = None


@dataclass
class SyncResult:
    connector: str
    started_at: str
    finished_at: str
    assets_count: int
    findings_count: int
    errors: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class Connector(ABC):
    """
    Abstract base all connectors implement. Six required methods,
    matching the pattern used across the Integration squad's connectors
    and mirrored by the TypeScript SDK.
    """

    name: str = "base"

    @abstractmethod
    def authenticate(self) -> bool:
        """Establish/validate auth against the vendor API."""
        raise NotImplementedError

    @abstractmethod
    def discover(self) -> List[Dict[str, Any]]:
        """Enumerate raw entities from the vendor (pre-normalization)."""
        raise NotImplementedError

    @abstractmethod
    def ingest(self) -> List[Dict[str, Any]]:
        """Pull full detail records for discovered entities."""
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw_records: List[Dict[str, Any]]) -> List[Asset]:
        """Map vendor-shaped records into the shared Asset/Finding shape."""
        raise NotImplementedError

    @abstractmethod
    def push(self, assets: List[Asset]) -> SyncResult:
        """Send normalized records to Beta's asset/exposure service."""
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> bool:
        """Lightweight check that auth + API reachability are OK."""
        raise NotImplementedError


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
