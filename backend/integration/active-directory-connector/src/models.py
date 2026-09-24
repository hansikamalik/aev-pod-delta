"""
Shared data shapes for the connector.

These mirror the Connector SDK contract (Asset / SyncResult) so this
package can be dropped in against the platform's Connector ABC without
modification.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Asset:
    external_id: str
    name: str
    type: str
    attributes: dict
    tags: dict


@dataclass
class SyncResult:
    records_processed: int
    records_created: int
    records_updated: int
    records_failed: int
    error: str | None = None
