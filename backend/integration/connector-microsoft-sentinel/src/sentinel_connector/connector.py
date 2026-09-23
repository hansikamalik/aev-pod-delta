"""
Microsoft Sentinel Connector — full implementation.

Owner: Harshal Sahare (Integration squad lead)
Week 1 deliverable (Sep 4 - Sep 10), Pod Delta M4.

Ties together auth -> credentials(Vault) -> discovery/ingestion ->
normalization -> push, matching the standard per-connector pattern
used across the Integration squad.
"""

import logging
from typing import Any, Dict, List, Optional

from .auth import SentinelAuthenticator
from .base import Asset, Connector, SyncResult
from .credentials import VaultClientProtocol, load_sentinel_credentials
from .discovery import SentinelDiscovery
from .normalization import normalize
from .push import BetaPlatformPusher

logger = logging.getLogger("sentinel_connector")


class SentinelConnector(Connector):
    name = "microsoft_sentinel"

    def __init__(self, vault: VaultClientProtocol, org_id: str, beta_api_token: str):
        self.org_id = org_id
        self._auth_config = load_sentinel_credentials(vault, org_id)
        self._authenticator = SentinelAuthenticator(self._auth_config)
        self._discovery = SentinelDiscovery(self._authenticator)
        self._pusher = BetaPlatformPusher(api_token=beta_api_token)

    def authenticate(self) -> bool:
        ok = self._authenticator.validate()
        if ok:
            logger.info("sentinel_connector.auth.ok org_id=%s", self.org_id)
        else:
            logger.error("sentinel_connector.auth.failed org_id=%s", self.org_id)
        return ok

    def discover(self) -> List[Dict[str, Any]]:
        incidents = self._discovery.discover()
        logger.info("sentinel_connector.discover.count=%d org_id=%s", len(incidents), self.org_id)
        return incidents

    def ingest(self) -> List[Dict[str, Any]]:
        incidents = self.discover()
        enriched = self._discovery.ingest(incidents)
        logger.info("sentinel_connector.ingest.count=%d org_id=%s", len(enriched), self.org_id)
        return enriched

    def normalize(self, raw_records: List[Dict[str, Any]]) -> List[Asset]:
        assets = normalize(raw_records)
        logger.info("sentinel_connector.normalize.count=%d org_id=%s", len(assets), self.org_id)
        return assets

    def push(self, assets: List[Asset]) -> SyncResult:
        result = self._pusher.push(self.name, assets)
        if result.success:
            logger.info(
                "sentinel_connector.push.ok assets=%d org_id=%s", result.assets_count, self.org_id
            )
        else:
            logger.error(
                "sentinel_connector.push.errors=%s org_id=%s", result.errors, self.org_id
            )
        return result

    def health_check(self) -> bool:
        return self.authenticate()

    def run_full_sync(self) -> SyncResult:
        """
        Convenience method chaining the full pipeline:
        auth -> ingest -> normalize -> push.
        Not part of the Connector ABC itself, but this is what a
        scheduler/orchestrator would call end-to-end.
        """
        if not self.authenticate():
            return SyncResult(
                connector=self.name,
                started_at="",
                finished_at="",
                assets_count=0,
                findings_count=0,
                errors=["Authentication failed"],
            )

        raw_records = self.ingest()
        assets = self.normalize(raw_records)
        return self.push(assets)
