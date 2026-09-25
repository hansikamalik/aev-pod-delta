"""
GitLab Connector - full implementation.

Owner: Bhavesh Kanekar (Integration squad)
Week 3 deliverable (Sep 18 - Sep 24), Pod Delta M4.

auth -> credentials (Vault) -> discovery/ingestion -> normalization -> push
"""

import logging
from typing import Any, Dict, List

from .auth import GitLabAuthenticator
from .base import Asset, Connector, Finding, SyncResult
from .credentials import VaultClientProtocol, load_gitlab_credentials
from .discovery import GitLabDiscovery
from .normalization import normalize, normalize_findings
from .push import BetaPlatformPusher

logger = logging.getLogger("gitlab_connector")


class GitLabConnector(Connector):
    name = "gitlab"

    def __init__(self, vault: VaultClientProtocol, org_id: str, beta_api_token: str):
        self.org_id = org_id
        self.findings: List[Finding] = []
        self._auth_config = load_gitlab_credentials(vault, org_id)
        self._authenticator = GitLabAuthenticator(self._auth_config)
        self._discovery = GitLabDiscovery(self._authenticator)
        self._pusher = BetaPlatformPusher(api_token=beta_api_token)

    @property
    def warnings(self) -> List[str]:
        """Non-fatal issues from the last ingest (e.g. vulnerabilities unavailable)."""
        return self._discovery.warnings

    def authenticate(self) -> bool:
        ok = self._authenticator.validate()
        if ok:
            logger.info("gitlab_connector.auth.ok org_id=%s", self.org_id)
        else:
            logger.error("gitlab_connector.auth.failed org_id=%s", self.org_id)
        return ok

    def discover(self) -> List[Dict[str, Any]]:
        projects = self._discovery.discover()
        logger.info("gitlab_connector.discover.count=%d org_id=%s", len(projects), self.org_id)
        return projects

    def ingest(self) -> List[Dict[str, Any]]:
        enriched = self._discovery.ingest(self.discover())
        logger.info("gitlab_connector.ingest.count=%d org_id=%s", len(enriched), self.org_id)
        return enriched

    def normalize(self, raw_records: List[Dict[str, Any]]) -> List[Asset]:
        assets = normalize(raw_records)
        self.findings = normalize_findings(raw_records)
        logger.info(
            "gitlab_connector.normalize assets=%d findings=%d org_id=%s",
            len(assets), len(self.findings), self.org_id,
        )
        return assets

    def push(self, assets: List[Asset]) -> SyncResult:
        result = self._pusher.push(self.name, assets)
        if result.success:
            logger.info("gitlab_connector.push.ok assets=%d org_id=%s", result.assets_count, self.org_id)
        else:
            logger.error("gitlab_connector.push.errors=%s org_id=%s", result.errors, self.org_id)
        return result

    def health_check(self) -> bool:
        return self.authenticate()

    def run_full_sync(self) -> SyncResult:
        """auth -> ingest -> normalize -> push (what a scheduler would call)."""
        if not self.authenticate():
            return SyncResult(
                connector=self.name, started_at="", finished_at="",
                assets_count=0, findings_count=0, errors=["Authentication failed"],
            )
        assets = self.normalize(self.ingest())
        result = self.push(assets)
        result.findings_count = len(self.findings)
        return result
