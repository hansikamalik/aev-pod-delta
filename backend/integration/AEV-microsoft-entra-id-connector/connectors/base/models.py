"""Shared normalization shapes for every AEV connector.

Every connector maps raw vendor data into these models before pushing
to the Beta platform asset/exposure service. Field names are stable —
do not rename without a platform contract review.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AssetType(str, Enum):
    ENDPOINT = "endpoint"
    SERVER = "server"
    IDENTITY = "identity"
    APPLICATION = "application"
    CLOUD_RESOURCE = "cloud_resource"
    NETWORK_DEVICE = "network_device"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Asset:
    """A normalized asset (device, identity, service) seen by a connector."""
    name: str
    asset_type: AssetType = AssetType.UNKNOWN
    vendor: str = ""
    external_id: str = ""                     # id in the source system
    ip_addresses: list[str] = field(default_factory=list)
    hostname: str = ""
    environment: str = ""                     # prod / staging / dev
    owner: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    first_seen: datetime = field(default_factory=_utcnow)
    last_seen: datetime = field(default_factory=_utcnow)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        d = asdict(self)
        d["asset_type"] = self.asset_type.value
        d["first_seen"] = self.first_seen.isoformat()
        d["last_seen"] = self.last_seen.isoformat()
        return d


@dataclass
class Finding:
    """A normalized security finding tied to an asset."""
    title: str
    severity: Severity = Severity.INFO
    asset_external_id: str = ""               # links back to Asset.external_id
    status: str = "open"                      # open / in_progress / resolved
    description: str = ""
    source: str = ""                          # connector name, e.g. "microsoft_defender"
    external_id: str = ""                     # id in the source system
    detected_at: datetime = field(default_factory=_utcnow)
    remediation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        d = asdict(self)
        d["severity"] = self.severity.value
        d["detected_at"] = self.detected_at.isoformat()
        return d


@dataclass
class HealthStatus:
    ok: bool
    message: str = ""
    latency_ms: Optional[float] = None
    checked_at: datetime = field(default_factory=_utcnow)


@dataclass
class SyncResult:
    """Result of one full connector sync (discover + ingest + push)."""
    connector: str
    started_at: datetime = field(default_factory=_utcnow)
    finished_at: Optional[datetime] = None
    assets_discovered: int = 0
    findings_ingested: int = 0
    assets_pushed: int = 0
    findings_pushed: int = 0
    errors: list[str] = field(default_factory=list)
    status: str = "running"                   # running / success / partial / failed

    def finish(self, status: Optional[str] = None) -> "SyncResult":
        self.finished_at = _utcnow()
        if status:
            self.status = status
        elif self.errors:
            self.status = "partial" if (self.assets_pushed or self.findings_pushed) else "failed"
        else:
            self.status = "success"
        return self
