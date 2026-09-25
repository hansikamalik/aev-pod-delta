"""
PLACEHOLDER Connector interface.

IMPORTANT: This is NOT the official contract. The real interface is owned
by Vatsal Thummar (Integration Squad lead) and Sai Kumar Dungala (SDK Squad
lead) and must be agreed between both squads by end of Week 1.

This stub exists so Harshal + Bhavesh can build the dummy connector and
contract test *now*, without blocking on that sign-off. Once the real
interface is frozen, replace this file's contents (or import it directly
from the shared SDK package) and re-run the contract test - if the dummy
connector still passes, the swap was clean.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Asset:
    id: str
    type: str
    name: str
    metadata: dict = field(default_factory=dict)


@dataclass
class SyncResult:
    success: bool
    records_synced: int
    errors: list = field(default_factory=list)


class Connector(ABC):
    """Every connector (AWS, Azure, CrowdStrike, Jira, ...) implements this."""

    @abstractmethod
    def discover(self) -> list[Asset]:
        """Find assets available from the source system."""
        ...

    @abstractmethod
    def ingest(self) -> list[Asset]:
        """Pull full asset data for discovered assets."""
        ...

    @abstractmethod
    def sync(self) -> SyncResult:
        """Run a full discover -> ingest -> push cycle."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Confirm the connector can reach its source system."""
        ...

    @abstractmethod
    def get_config_schema(self) -> dict:
        """Describe the non-secret config this connector needs."""
        ...

    @abstractmethod
    def get_credential_schema(self) -> dict:
        """Describe the credentials this connector needs."""
        ...
