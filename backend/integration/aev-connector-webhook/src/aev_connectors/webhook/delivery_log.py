"""Delivery log.

Every delivery attempt is recorded — status code, duration, error, attempt
number — so an operator can answer "did event X reach the customer, and if not,
why" without reading application logs. Rows follow the same 1-year retention
rule as `ai_interactions`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol

from .models import DeliveryRecord, DeliveryStatus

RETENTION_DAYS = 365


class DeliveryLogError(Exception):
    """Raised when a delivery record cannot be found."""


class DeliveryLog(Protocol):
    def append(self, record: DeliveryRecord) -> DeliveryRecord: ...
    def get(self, delivery_id: str) -> DeliveryRecord: ...
    def list(
        self,
        org_id: str,
        status: DeliveryStatus | None = None,
        limit: int = 100,
    ) -> list[DeliveryRecord]: ...
    def due_for_retry(self, now: datetime | None = None) -> list[DeliveryRecord]: ...
    def purge_expired(self, now: datetime | None = None) -> int: ...


class InMemoryDeliveryLog:
    """Dict-backed delivery log used by tests and the Python sandbox."""

    def __init__(self, retention_days: int = RETENTION_DAYS) -> None:
        self._rows: dict[str, DeliveryRecord] = {}
        self._retention_days = retention_days

    def append(self, record: DeliveryRecord) -> DeliveryRecord:
        self._rows[record.id] = record
        return record

    def get(self, delivery_id: str) -> DeliveryRecord:
        try:
            return self._rows[delivery_id]
        except KeyError as exc:
            raise DeliveryLogError(f"unknown delivery: {delivery_id}") from exc

    def list(
        self,
        org_id: str,
        status: DeliveryStatus | None = None,
        limit: int = 100,
    ) -> list[DeliveryRecord]:
        rows = [
            r
            for r in self._rows.values()
            if r.org_id == org_id and (status is None or r.status == status)
        ]
        rows.sort(key=lambda r: r.created_at, reverse=True)
        return rows[:limit]

    def due_for_retry(self, now: datetime | None = None) -> list[DeliveryRecord]:
        current = now or datetime.now(UTC)
        return [
            r
            for r in self._rows.values()
            if r.status == DeliveryStatus.RETRYING
            and r.next_retry_at is not None
            and r.next_retry_at <= current
        ]

    def purge_expired(self, now: datetime | None = None) -> int:
        cutoff = (now or datetime.now(UTC)) - timedelta(days=self._retention_days)
        expired = [k for k, r in self._rows.items() if r.created_at < cutoff]
        for key in expired:
            del self._rows[key]
        return len(expired)

    def stats(self, org_id: str) -> dict[str, int]:
        """Counts per status — the shape the fallback/health dashboard consumes."""
        counts = {status.value: 0 for status in DeliveryStatus}
        for record in self._rows.values():
            if record.org_id == org_id:
                counts[record.status.value] += 1
        return counts
