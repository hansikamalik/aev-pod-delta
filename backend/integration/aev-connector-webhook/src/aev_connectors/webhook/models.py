"""Data shapes for the Webhook connector.

`Asset` and `SyncResult` mirror the shared platform shapes used by every other
connector in the catalog (see docs/CONNECTOR_INTERFACE_STABILITY.md).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:24]}"


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    DELIVERED = "delivered"
    RETRYING = "retrying"
    FAILED = "failed"
    DEAD_LETTERED = "dead_lettered"


class Asset(BaseModel):
    """Shared platform asset shape."""

    external_id: str
    name: str
    asset_type: str
    source: str = "webhook"
    ip_addresses: list[str] = Field(default_factory=list)
    hostnames: list[str] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)
    first_seen: datetime = Field(default_factory=_utcnow)
    last_seen: datetime = Field(default_factory=_utcnow)
    raw: dict[str, Any] = Field(default_factory=dict)


class Finding(BaseModel):
    """Shared platform exposure/finding shape."""

    external_id: str
    asset_external_id: str
    title: str
    severity: Literal["critical", "high", "medium", "low", "info"] = "info"
    description: str = ""
    source: str = "webhook"
    detected_at: datetime = Field(default_factory=_utcnow)
    raw: dict[str, Any] = Field(default_factory=dict)


class SyncResult(BaseModel):
    """Returned by ingest()/push() so the sync engine can record the run."""

    connector_id: str
    org_id: str
    started_at: datetime = Field(default_factory=_utcnow)
    finished_at: datetime | None = None
    assets_discovered: int = 0
    assets_pushed: int = 0
    findings_pushed: int = 0
    errors: list[str] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def finish(self) -> SyncResult:
        self.finished_at = _utcnow()
        return self


class Subscription(BaseModel):
    """A per-event subscription bound to one target URL."""

    id: str = Field(default_factory=lambda: _new_id("sub"))
    org_id: str
    connector_id: str
    target_url: HttpUrl
    event_types: list[str]
    active: bool = True
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    @field_validator("event_types")
    @classmethod
    def _non_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("event_types must contain at least one event type")
        return sorted(set(v))

    def matches(self, event_type: str) -> bool:
        """Exact match, or a trailing wildcard such as `asset.*`."""
        if not self.active:
            return False
        for pattern in self.event_types:
            if pattern == "*" or pattern == event_type:
                return True
            if pattern.endswith(".*") and event_type.startswith(pattern[:-1]):
                return True
        return False


class Event(BaseModel):
    """An outbound platform event delivered to a subscriber."""

    id: str = Field(default_factory=lambda: _new_id("evt"))
    org_id: str
    event_type: str
    occurred_at: datetime = Field(default_factory=_utcnow)
    payload: dict[str, Any] = Field(default_factory=dict)

    def envelope(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.event_type,
            "org_id": self.org_id,
            "occurred_at": self.occurred_at.isoformat(),
            "data": self.payload,
        }


class DeliveryAttempt(BaseModel):
    attempt: int
    at: datetime = Field(default_factory=_utcnow)
    status_code: int | None = None
    error: str | None = None
    duration_ms: int | None = None


class DeliveryRecord(BaseModel):
    """One row of the permanent delivery log."""

    id: str = Field(default_factory=lambda: _new_id("dlv"))
    org_id: str
    connector_id: str
    subscription_id: str
    event_id: str
    event_type: str
    target_url: str
    status: DeliveryStatus = DeliveryStatus.PENDING
    attempts: list[DeliveryAttempt] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    next_retry_at: datetime | None = None

    @property
    def attempt_count(self) -> int:
        return len(self.attempts)

    def record_attempt(self, attempt: DeliveryAttempt, status: DeliveryStatus) -> None:
        self.attempts.append(attempt)
        self.status = status
        self.updated_at = _utcnow()


class InboundEvent(BaseModel):
    """An event POSTed *into* the platform by an external system."""

    event_type: str
    occurred_at: datetime | None = None
    assets: list[dict[str, Any]] = Field(default_factory=list)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)
