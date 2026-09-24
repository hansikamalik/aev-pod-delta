"""Microsoft Entra ID connector ΓÇö Week 2 deliverable (Abhiram).

Implements the standard Connector ABC (connectors/base/interface.py) by
wiring together Week 1's auth module with this week's discovery,
normalization, and push modules.

`discover()` and `ingest()` are both driven from a single raw Graph
pull (cached on the instance) so a full sync only round-trips the
Graph API once per object type, not twice.
"""
from __future__ import annotations

import time

from connectors.base.interface import Connector
from connectors.base.models import Asset, Finding, HealthStatus
from connectors.microsoft_entra_id.auth import EntraIDAuth, EntraIDAuthError
from connectors.microsoft_entra_id.discovery import discover_raw
from connectors.microsoft_entra_id.normalization import normalize_assets, normalize_findings
from connectors.microsoft_entra_id.push import push_to_platform


class EntraIDConnector(Connector):
    name = "microsoft_entra_id"

    def __init__(self, auth: EntraIDAuth | None = None):
        self.auth = auth or EntraIDAuth()
        self._raw_cache: list[dict] | None = None

    # ---- authenticate --------------------------------------------------

    def authenticate(self) -> None:
        self.auth.token(force_refresh=True)

    # ---- health_check ---------------------------------------------------

    def health_check(self) -> HealthStatus:
        start = time.time()
        try:
            self.auth.introspect()
            return HealthStatus(ok=True, message="Graph introspection succeeded",
                                 latency_ms=(time.time() - start) * 1000)
        except EntraIDAuthError as exc:
            return HealthStatus(ok=False, message=str(exc),
                                 latency_ms=(time.time() - start) * 1000)

    # ---- discover / ingest (share one raw pull) -------------------------

    def _raw(self) -> list[dict]:
        if self._raw_cache is None:
            self._raw_cache = discover_raw(self.auth)
        return self._raw_cache

    def discover(self) -> list[Asset]:
        return normalize_assets(self._raw())

    def ingest(self) -> list[Finding]:
        return normalize_findings(self._raw())

    # ---- normalize (single-record entry point) ---------------------

    def normalize(self, raw: dict) -> Asset | Finding:
        from connectors.microsoft_entra_id.normalization import normalize_asset
        return normalize_asset(raw)

    # ---- push -------------------------------------------------------

    def push(self, assets: list[Asset], findings: list[Finding]) -> dict:
        return push_to_platform(assets, findings)
