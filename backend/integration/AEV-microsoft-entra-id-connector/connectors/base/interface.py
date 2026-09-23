"""The 6-method Connector ABC every AEV connector implements."""
from __future__ import annotations

from abc import ABC, abstractmethod

from .models import Asset, Finding, HealthStatus, SyncResult


class Connector(ABC):
    """Contract for all platform connectors.

    The TypeScript SDK mirrors this interface method-for-method.
    """

    name: str = "base"

    @abstractmethod
    def authenticate(self) -> None:
        """Obtain vendor tokens / establish an authenticated session."""

    @abstractmethod
    def health_check(self) -> HealthStatus:
        """Vendor reachability + credential validity probe."""

    @abstractmethod
    def discover(self) -> list[Asset]:
        """Enumerate assets from the source system."""

    @abstractmethod
    def ingest(self) -> list[Finding]:
        """Pull findings (alerts / offenses / vulnerabilities)."""

    @abstractmethod
    def normalize(self, raw: dict) -> Asset | Finding:
        """Map one raw vendor record to the shared Asset/Finding shape."""

    @abstractmethod
    def push(self, assets: list[Asset], findings: list[Finding]) -> dict:
        """Send normalized data to the Beta platform asset/exposure service."""

    def run_sync(self) -> SyncResult:
        """Convenience: full discover → ingest → normalize → push cycle."""
        result = SyncResult(connector=self.name)
        try:
            self.authenticate()
            assets = self.discover()
            findings = self.ingest()
            result.assets_discovered = len(assets)
            result.findings_ingested = len(findings)
            pushed = self.push(assets, findings)
            result.assets_pushed = pushed.get("assets", 0)
            result.findings_pushed = pushed.get("findings", 0)
        except Exception as exc:  # noqa: BLE001 — sync runner must not raise
            result.errors.append(f"{type(exc).__name__}: {exc}")
        return result.finish()
