"""
Vendored copy of the platform's Connector SDK contract
(AEV Platform Module 1 — Pod Delta Build Guide, section 7.5).

In production this connector depends on the shared `connector-sdk`
package published by the SDK squad (Delta-4) instead of this file.
It is vendored here so this repository builds, lints, and tests
standalone without a private package registry dependency.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from .models import Asset, SyncResult

__all__ = ["Connector", "Asset", "SyncResult"]


class Connector(ABC):
    @abstractmethod
    async def discover(self, config: dict) -> AsyncIterator[Asset]:
        """Discover assets from the source system."""

    @abstractmethod
    async def ingest(self, config: dict) -> AsyncIterator[dict]:
        """Ingest events/findings from the source system."""

    @abstractmethod
    async def sync(self, config: dict, direction: str) -> SyncResult:
        """Bidirectional sync (if supported)."""

    @abstractmethod
    async def health_check(self, config: dict) -> dict:
        """Check connector health and credential validity."""

    @abstractmethod
    def config_schema(self) -> dict:
        """Return JSON schema for connector configuration."""

    @abstractmethod
    def credential_schema(self) -> dict:
        """Return JSON schema for connector credentials (stored in Vault)."""
