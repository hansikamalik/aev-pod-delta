from __future__ import annotations

from typing import Protocol


class SyncStateStore(Protocol):
    """Minimal state boundary for the platform sync engine."""

    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str) -> None: ...


class InMemorySyncStateStore:
    """State store for tests/local development only."""

    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._values.get(key)

    async def set(self, key: str, value: str) -> None:
        self._values[key] = value
