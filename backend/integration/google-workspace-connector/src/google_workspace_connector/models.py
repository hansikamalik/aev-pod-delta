from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Asset:
    external_id: str
    name: str
    type: str
    attributes: dict[str, Any]
    tags: dict[str, str]


@dataclass(slots=True)
class SyncResult:
    records_processed: int
    records_created: int
    records_updated: int
    records_failed: int
    error: str | None = None
