"""
Shared data shapes for the connector.

These mirror the Connector SDK contract (Asset / SyncResult) so this
package can be dropped in against the platform's Connector ABC without
modification. Findings (alerts) are intentionally left as plain dicts,
matching ingest()'s AsyncIterator[dict] signature in the SDK contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field


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


@dataclass
class Finding:
    """Normalized shape for a Defender alert before it is pushed to the
    Exposure service. Kept as a dataclass for internal use; ingest()
    yields its .to_dict() form to match the SDK's AsyncIterator[dict].
    """

    external_id: str
    asset_external_id: str | None
    title: str
    severity: str
    status: str
    category: str
    description: str
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "external_id": self.external_id,
            "asset_external_id": self.asset_external_id,
            "title": self.title,
            "severity": self.severity,
            "status": self.status,
            "category": self.category,
            "description": self.description,
            "raw": self.raw,
        }
