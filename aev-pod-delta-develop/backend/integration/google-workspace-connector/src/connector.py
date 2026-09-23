"""
Google Workspace Connector — full implementation.

auth -> discover (users) + ingest (audit log) -> normalize -> push

Note on shape: unlike a connector where ingest() pulls enriched detail for
entities discover() already found, Google Workspace's discover() (user
inventory) and ingest() (admin audit log) are two independent data sources
from different Admin SDK sub-APIs. normalize() is called with discover()'s
output to build Assets, and internally calls ingest() once to populate
self.findings — keeping the same external shape (normalize() sets
self.findings as a side effect) as the rest of the codebase, while
reflecting that these are genuinely separate feeds.
"""

import logging
from typing import Any, Dict, List

from .auth import GoogleWorkspaceAuthenticator
from .base import Asset, Connector, Finding, SyncResult
from .credentials import VaultClientProtocol, load_google_workspace_credentials
from .discovery import GoogleWorkspaceDiscovery
from .normalization import normalize, normalize_findings
from .push import BetaPlatformPusher

logger = logging.getLogger("google_workspace_connector")


class GoogleWorkspaceConnector(Connector):
    name = "google_workspace"

    def __init__(self, vault: VaultClientProtocol, org_id: str, beta_api_token: str):
        self.org_id = org_id
        self.findings: List[Finding] = []
        self._auth_config = load_google_workspace_credentials(vault, org_id)
        self._authenticator = GoogleWorkspaceAuthenticator(self._auth_config)
        self._discovery = GoogleWorkspaceDiscovery(self._authenticator)
        self._pusher = BetaPlatformPusher(api_token=beta_api_token)

    def authenticate(self) -> bool:
        ok = self._authenticator.validate()
        if ok:
            logger.info("google_workspace_connector.auth.ok org_id=%s", self.org_id)
        else:
            logger.error("google_workspace_connector.auth.failed org_id=%s", self.org_id)
        return ok

    def discover(self) -> List[Dict[str, Any]]:
        users = self._discovery.discover()
        logger.info(
            "google_workspace_connector.discover.count=%d org_id=%s", len(users), self.org_id
        )
        return users

    def ingest(self) -> List[Dict[str, Any]]:
        activities = self._discovery.ingest()
        logger.info(
            "google_workspace_connector.ingest.count=%d org_id=%s",
            len(activities), self.org_id,
        )
        return activities

    def normalize(self, raw_records: List[Dict[str, Any]]) -> List[Asset]:
        assets = normalize(raw_records)
        self.findings = normalize_findings(self.ingest())
        logger.info(
            "google_workspace_connector.normalize assets=%d findings=%d org_id=%s",
            len(assets), len(self.findings), self.org_id,
        )
        return assets

    def push(self, assets: List[Asset]) -> SyncResult:
        result = self._pusher.push(self.name, assets)
        result.findings_count = len(self.findings)
        if result.success:
            logger.info(
                "google_workspace_connector.push.ok assets=%d org_id=%s",
                result.assets_count, self.org_id,
            )
        else:
            logger.error(
                "google_workspace_connector.push.errors=%s org_id=%s",
                result.errors, self.org_id,
            )
        return result

    def health_check(self) -> bool:
        return self.authenticate()

    def run_full_sync(self) -> SyncResult:
        """auth -> discover -> normalize (which also ingests) -> push."""
        if not self.authenticate():
            return SyncResult(
                connector=self.name, started_at="", finished_at="",
                assets_count=0, findings_count=0, errors=["Authentication failed"],
            )
        assets = self.normalize(self.discover())
        result = self.push(assets)
        result.findings_count = len(self.findings)
        return result
