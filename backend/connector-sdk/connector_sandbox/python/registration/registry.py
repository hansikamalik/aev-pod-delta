"""
Storage for registered connectors.

`ConnectorRegistry` is the seam: everything above this file (the FastAPI
route) only ever talks to this interface, never to a concrete storage
mechanism. Today that's `InMemoryConnectorRegistry`. When the platform's
real connector-registry service/database exists, write a second class
implementing the same three methods and swap it in at app construction --
nothing in routes.py changes.

This is deliberately the *only* file that needs to change once you know
what the other squads actually built.
"""
from __future__ import annotations

from typing import Protocol

from .schemas import ConnectorRecord


class ConnectorAlreadyRegistered(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"a connector named {name!r} is already registered")
        self.name = name


class ConnectorNotFound(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"no connector named {name!r} is registered")
        self.name = name


class ConnectorRegistry(Protocol):
    def register(self, record: ConnectorRecord) -> ConnectorRecord:
        """Store a new record. Raises ConnectorAlreadyRegistered on a duplicate name."""

    def get(self, name: str) -> ConnectorRecord:
        """Raises ConnectorNotFound if no such connector is registered."""

    def list(self) -> list[ConnectorRecord]: ...


class InMemoryConnectorRegistry:
    """Process-local, not persisted. Fine for a demo and for the sandbox's
    own tests; not fine for anything that needs to survive a restart or be
    shared across processes. That's exactly why it's swappable."""

    def __init__(self) -> None:
        self._records: dict[str, ConnectorRecord] = {}

    def register(self, record: ConnectorRecord) -> ConnectorRecord:
        if record.name in self._records:
            raise ConnectorAlreadyRegistered(record.name)
        self._records[record.name] = record
        return record

    def get(self, name: str) -> ConnectorRecord:
        try:
            return self._records[name]
        except KeyError:
            raise ConnectorNotFound(name) from None

    def list(self) -> list[ConnectorRecord]:
        return list(self._records.values())
