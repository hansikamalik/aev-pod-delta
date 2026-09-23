"""Per-event subscription registry.

The in-memory implementation is what the unit tests and the Python sandbox use.
Swap in a Postgres-backed repository behind the same `SubscriptionStore`
protocol without touching the connector.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from .config import DEFAULT_EVENT_TYPES
from .models import Subscription


class SubscriptionError(Exception):
    """Raised on an unknown subscription or an unsupported event type."""


class SubscriptionStore(Protocol):
    def create(self, subscription: Subscription) -> Subscription: ...
    def get(self, subscription_id: str) -> Subscription: ...
    def list(self, org_id: str, connector_id: str | None = None) -> list[Subscription]: ...
    def update(self, subscription_id: str, **fields) -> Subscription: ...
    def delete(self, subscription_id: str) -> None: ...
    def matching(self, org_id: str, event_type: str) -> list[Subscription]: ...


class InMemorySubscriptionStore:
    """Dict-backed store. Thread-safety is the caller's concern."""

    def __init__(self, allowed_event_types: tuple[str, ...] = DEFAULT_EVENT_TYPES) -> None:
        self._rows: dict[str, Subscription] = {}
        self._allowed = set(allowed_event_types)

    def _validate_event_types(self, event_types: list[str]) -> None:
        for et in event_types:
            if et == "*" or (et.endswith(".*") and any(a.startswith(et[:-1]) for a in self._allowed)):
                continue
            if et not in self._allowed:
                raise SubscriptionError(f"unsupported event type: {et}")

    def create(self, subscription: Subscription) -> Subscription:
        self._validate_event_types(subscription.event_types)
        self._rows[subscription.id] = subscription
        return subscription

    def get(self, subscription_id: str) -> Subscription:
        try:
            return self._rows[subscription_id]
        except KeyError as exc:
            raise SubscriptionError(f"unknown subscription: {subscription_id}") from exc

    def list(self, org_id: str, connector_id: str | None = None) -> list[Subscription]:
        return [
            s
            for s in self._rows.values()
            if s.org_id == org_id and (connector_id is None or s.connector_id == connector_id)
        ]

    def update(self, subscription_id: str, **fields) -> Subscription:
        sub = self.get(subscription_id)
        if "event_types" in fields:
            self._validate_event_types(fields["event_types"])
        updated = sub.model_copy(
            update={**fields, "updated_at": datetime.now(UTC)}
        )
        self._rows[subscription_id] = updated
        return updated

    def delete(self, subscription_id: str) -> None:
        self._rows.pop(subscription_id, None)

    def matching(self, org_id: str, event_type: str) -> list[Subscription]:
        return [s for s in self._rows.values() if s.org_id == org_id and s.matches(event_type)]
