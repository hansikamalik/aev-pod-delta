"""
QA mirror of the Connector SDK contract (contract_v2.md).

STATUS: aligned to `contract_v2 (1).md` (Connector SDK — Integration Connector
Contract). The SDK's own base class is authoritative; this mirror exists so
contract tests can run before/without the SDK package. When the SDK import
path is known, switch imports to the SDK and keep only the test logic.

Contract surface (§3):
    name (property)                -> str
    discover()                     -> Iterable[Asset]
    ingest(assets)                 -> int          # pushes to platform
    sync()                         -> async SyncResult  (SDK default impl)
    check_health()                 -> bool
    describe_config()              -> dict (JSON schema, non-secret)
    describe_credentials()         -> dict (JSON schema, secret fields)
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


# ---------------------------------------------------------------------------
# Sync status (§15)
# ---------------------------------------------------------------------------
SYNC_STATUS_SUCCESS = "success"
SYNC_STATUS_PARTIAL = "partial"
SYNC_STATUS_FAILED = "failed"
SYNC_STATUSES = {SYNC_STATUS_SUCCESS, SYNC_STATUS_PARTIAL, SYNC_STATUS_FAILED}


# ---------------------------------------------------------------------------
# AssetType values (§8)
# ---------------------------------------------------------------------------
ASSET_TYPES = {"compute", "storage", "identity", "network", "ticket", "detection", "other"}


# ---------------------------------------------------------------------------
# Errors (§16) — secrets must never appear in error messages
# ---------------------------------------------------------------------------
class ConnectorError(Exception):
    """Base class for all connector errors."""


class AuthError(ConnectorError):
    """Invalid/expired credentials or failed authentication."""


class DiscoveryError(ConnectorError):
    """Source read failed (after retries where applicable)."""


class IngestionError(ConnectorError):
    """Platform push failed for one or more assets."""


class ConfigError(ConnectorError):
    """Connector configuration is missing or invalid."""


# ---------------------------------------------------------------------------
# Asset contract (§5-§9)
# ---------------------------------------------------------------------------
@dataclass
class Asset:
    """
    Normalized asset. All of id/source/type/name/raw/discoveredAt REQUIRED,
    tags optional. `id` must be stable across sync runs (§6); `source` must
    equal the connector's name (§7); `type` must be an SDK AssetType (§8).
    """
    id: str
    source: str
    type: str
    name: str
    raw: Dict[str, Any] = field(default_factory=dict)
    discoveredAt: Optional[str] = None   # ISO-8601
    tags: Dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# SyncResult contract (§14-§15)
# ---------------------------------------------------------------------------
@dataclass
class SyncResult:
    connector: str
    status: str                        # success | partial | failed
    assets_discovered: int
    assets_pushed: int
    errors: List[Dict[str, Any]] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Connector contract (§3)
# ---------------------------------------------------------------------------
class Connector(abc.ABC):
    """
    Every connector MUST extend this base class and MUST NOT change the
    public method names or return types.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str: ...

    @abc.abstractmethod
    def discover(self) -> Iterable[Asset]:
        """Read-only: source -> normalized Assets (§10). Must handle pagination (§21)."""
        raise NotImplementedError

    @abc.abstractmethod
    def ingest(self, assets: Iterable[Asset]) -> int:
        """Push normalized assets to the platform; return count successfully pushed (§11)."""
        raise NotImplementedError

    async def sync(self) -> SyncResult:
        """
        SDK default: discover -> ingest -> SyncResult (§13).
        Concrete connectors SHOULD NOT override unless §13 justifies it.
        The SDK owns the real implementation; this reference version exists
        so tests can exercise the default lifecycle without the SDK package.
        """
        from datetime import datetime, timezone

        started_at = datetime.now(timezone.utc).isoformat()
        try:
            assets = list(self.discover())
            pushed = self.ingest(assets)
        except Exception as exc:  # noqa: BLE001 — SDK behaviour: report, don't crash
            return SyncResult(
                connector=self.name,
                status=SYNC_STATUS_FAILED,
                assets_discovered=0,
                assets_pushed=0,
                errors=[{"operation": "sync", "error": str(exc)}],
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
        return SyncResult(
            connector=self.name,
            status=SYNC_STATUS_SUCCESS if pushed == len(assets) else SYNC_STATUS_PARTIAL,
            assets_discovered=len(assets),
            assets_pushed=pushed,
            errors=[],
            started_at=started_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

    @abc.abstractmethod
    def check_health(self) -> bool:
        """Lightweight connectivity/auth probe. Never raises (§17)."""
        raise NotImplementedError

    @abc.abstractmethod
    def describe_config(self) -> dict:
        """JSON schema of required non-secret configuration (§18)."""
        raise NotImplementedError

    @abc.abstractmethod
    def describe_credentials(self) -> dict:
        """JSON schema of required secrets; secret fields flagged (§19)."""
        raise NotImplementedError
