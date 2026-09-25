"""Core data models for the Connector SDK.

Contract references:
  - Section 5  (Asset Contract)
  - Section 6  (Asset Identity)
  - Section 7  (Asset Source)
  - Section 9  (Raw Payload)
  - Section 14 (SyncResult)

Implemented with stdlib dataclasses so the SDK stays dependency-free and
installs cleanly in every member's environment.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .enums import AssetType, SyncStatus
from .exceptions import ConnectorError, ValidationError


def utcnow() -> datetime:
    """Timezone-aware UTC now. Use this instead of ``datetime.now()``."""
    return datetime.now(timezone.utc)


def build_asset_id(source: str, resource_type: str, identifier: str) -> str:
    """Construct a deterministic asset ID (Section 6).

    Use when the source system does not expose a single natural identifier::

        <source>:<resource-type>:<stable-resource-identifier>

    The same source resource MUST produce the same ID on every sync run,
    so ``identifier`` must be stable — never a UUID, timestamp, or index.
    """
    for label, value in (("source", source), ("resource_type", resource_type), ("identifier", identifier)):
        if not value or not str(value).strip():
            raise ValidationError(f"build_asset_id requires a non-empty {label}")
    return f"{source}:{resource_type}:{identifier}"


@dataclass(slots=True)
class Asset:
    """Normalized representation of a resource discovered from a source system.

    Required fields (Section 5): ``id``, ``source``, ``type``, ``name``,
    ``raw``, ``discovered_at``. ``tags`` is optional.

    ``discovered_at`` maps to the contract's ``discoveredAt`` and is
    serialized under that name by :meth:`to_dict`.

    Notes
    -----
    * ``id`` MUST be a stable source identifier, never randomly generated.
    * ``source`` MUST equal the producing connector's ``name``. The SDK
      enforces this in :meth:`Connector.discover_validated`.
    * ``raw`` SHOULD preserve the original payload and MUST NOT contain
      credentials or secrets.
    """

    id: str
    source: str
    type: AssetType | str
    name: str
    raw: Mapping[str, Any] = field(default_factory=dict)
    discovered_at: datetime = field(default_factory=utcnow)
    tags: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Coerce the asset type into the closed enum (Section 8).
        if not isinstance(self.type, AssetType):
            try:
                self.type = AssetType(str(self.type))
            except ValueError as exc:
                allowed = ", ".join(t.value for t in AssetType)
                raise ValidationError(
                    f"Unknown asset type {self.type!r}. Allowed values: {allowed}. "
                    "Introducing a new type requires an SDK contract change.",
                    resource_id=str(self.id),
                ) from exc

        if self.discovered_at.tzinfo is None:
            self.discovered_at = self.discovered_at.replace(tzinfo=timezone.utc)

        self.validate()

    def validate(self) -> None:
        """Raise :class:`ValidationError` if a required field is missing."""
        for label in ("id", "source", "name"):
            value = getattr(self, label)
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(
                    f"Asset.{label} is required and must be a non-empty string",
                    resource_id=str(self.id) if label != "id" else None,
                )
        if self.raw is None:
            raise ValidationError("Asset.raw is required", resource_id=self.id)
        if not isinstance(self.discovered_at, datetime):
            raise ValidationError("Asset.discovered_at must be a datetime", resource_id=self.id)

    def with_source(self, source: str) -> "Asset":
        """Return a copy bound to ``source``. Used by SDK validation helpers."""
        return replace(self, source=source)

    def to_dict(self) -> dict[str, Any]:
        """Serialize using the contract's field names."""
        return {
            "id": self.id,
            "source": self.source,
            "type": str(self.type),
            "name": self.name,
            "raw": dict(self.raw),
            "discoveredAt": self.discovered_at.isoformat(),
            "tags": dict(self.tags),
        }


@dataclass(slots=True)
class SyncResult:
    """Outcome of exactly one synchronization attempt (Section 14).

    Lets the platform determine which connector ran, whether it succeeded,
    how many assets were discovered and pushed, whether errors occurred,
    and when the run started and completed.
    """

    connector: str
    status: SyncStatus | str
    assets_discovered: int = 0
    assets_pushed: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    started_at: datetime = field(default_factory=utcnow)
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        self.normalize_status()

    def normalize_status(self) -> SyncStatus:
        """Coerce ``status`` into a :class:`SyncStatus` member.

        Called on construction and by :meth:`finalize`. Connectors that
        override ``sync()`` may assign a plain string such as ``"partial"``;
        this keeps ``result.status is SyncStatus.PARTIAL`` reliable for
        callers and for the contract tests.
        """
        if not isinstance(self.status, SyncStatus):
            try:
                self.status = SyncStatus(str(self.status))
            except ValueError as exc:
                allowed = ", ".join(s.value for s in SyncStatus)
                raise ValidationError(
                    f"Unknown sync status {self.status!r}. Allowed values: {allowed}"
                ) from exc
        return self.status

    def finalize(self) -> "SyncResult":
        """Stamp ``completed_at`` and normalize ``status``. Returns self."""
        if self.completed_at is None:
            self.completed_at = utcnow()
        self.normalize_status()
        return self

    @property
    def duration_seconds(self) -> float | None:
        """Wall-clock duration of the run, or ``None`` if still open."""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def succeeded(self) -> bool:
        return self.status is SyncStatus.SUCCESS

    def add_error(self, error: ConnectorError | Mapping[str, Any] | str) -> None:
        """Record an error. Accepts a ConnectorError, a mapping, or a message."""
        if isinstance(error, ConnectorError):
            self.errors.append(error.to_dict())
        elif isinstance(error, Mapping):
            self.errors.append(dict(error))
        else:
            self.errors.append(
                {
                    "error_type": "Error",
                    "message": str(error),
                    "occurred_at": utcnow().isoformat(),
                }
            )

    @classmethod
    def derive_status(
        cls,
        *,
        discovered: int,
        pushed: int,
        errors: Sequence[Any],
    ) -> SyncStatus:
        """Apply the Section 15 status rules.

        * nothing pushed while something was expected, or nothing discovered
          and errors present -> ``failed``
        * everything pushed and no errors                       -> ``success``
        * anything else (short push count or errors present)    -> ``partial``
        """
        if discovered == 0:
            return SyncStatus.FAILED if errors else SyncStatus.SUCCESS
        if pushed == 0:
            return SyncStatus.FAILED
        if pushed >= discovered and not errors:
            return SyncStatus.SUCCESS
        return SyncStatus.PARTIAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "connector": self.connector,
            "status": str(self.status),
            "assets_discovered": self.assets_discovered,
            "assets_pushed": self.assets_pushed,
            "errors": list(self.errors),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
        }


__all__ = ["Asset", "SyncResult", "build_asset_id", "utcnow"]
