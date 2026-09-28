"""
The shared Connector contract.

Every connector (AWS, Azure, GCP, CrowdStrike, Splunk, Jira, Okta, ...)
must subclass Connector and implement these 6 methods. This is the
contract frozen jointly with the Integration squad in Week 1 -- once
frozen, no connector should need to change its shape.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Iterable

from .models import Asset, SyncResult, SyncStatus


class Connector(ABC):
    """Abstract base class every connector must implement."""

    #: Short unique name for this connector, e.g. "aws", "okta".
    name: str = "unnamed"

    # ---- 1. Discover ----------------------------------------------------
    @abstractmethod
    def discover(self) -> Iterable[Asset]:
        """Find and return all assets currently visible to this connector.

        Should not have side effects on the platform -- just reads from
        the source system and yields/returns normalized Asset objects.
        """
        raise NotImplementedError

    # ---- 2. Ingest --------------------------------------------------------
    @abstractmethod
    def ingest(self, assets: Iterable[Asset]) -> int:
        """Push a batch of discovered assets into the platform's asset
        service. Returns the number of assets successfully pushed.
        """
        raise NotImplementedError

    # ---- 3. Sync ------------------------------------------------------
    def sync(self) -> SyncResult:
        """Run a full discover -> ingest cycle and report the outcome.

        This has a default implementation built on discover()/ingest(),
        but connectors may override it if they need custom batching,
        retries, or incremental sync logic.
        """
        started_at = datetime.now(timezone.utc)
        errors: list[str] = []
        assets: list[Asset] = []

        try:
            assets = list(self.discover())
        except Exception as exc:  # noqa: BLE001 - surface any discovery failure
            errors.append(f"discover() failed: {exc}")

        pushed = 0
        if assets:
            try:
                pushed = self.ingest(assets)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"ingest() failed: {exc}")

        if errors and pushed == 0:
            status = SyncStatus.FAILED
        elif errors:
            status = SyncStatus.PARTIAL
        else:
            status = SyncStatus.SUCCESS

        return SyncResult(
            connector=self.name,
            status=status,
            assets_discovered=len(assets),
            assets_pushed=pushed,
            errors=errors,
            started_at=started_at,
        )

    # ---- 4. Health check ------------------------------------------------
    @abstractmethod
    def check_health(self) -> bool:
        """Return True if the connector can currently reach its source
        system (credentials valid, network reachable, etc).
        """
        raise NotImplementedError

    # ---- 5. Describe config ----------------------------------------------
    @abstractmethod
    def describe_config(self) -> dict[str, Any]:
        """Return a JSON-schema-like dict describing what configuration
        fields this connector needs (excluding credentials).
        """
        raise NotImplementedError

    # ---- 6. Describe credentials -------------------------------------
    @abstractmethod
    def describe_credentials(self) -> dict[str, Any]:
        """Return a JSON-schema-like dict describing what credential
        fields this connector needs (e.g. api_key, access_key/secret_key).
        """
        raise NotImplementedError
