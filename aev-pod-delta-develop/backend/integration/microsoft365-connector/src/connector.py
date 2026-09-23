"""
Microsoft365Connector — ties authentication, discovery, normalization, and
push together behind the shared Connector interface.
"""

import logging
from typing import Any, Dict, List, Optional

from .auth import GraphAuthenticator
from .base import Connector
from .config import ConnectorConfig
from .credentials import VaultClient
from .discovery import GraphDiscovery
from .exceptions import ConnectorError
from .normalization import normalize as normalize_assets
from .normalization import normalize_findings
from .push import PlatformClient

logger = logging.getLogger("microsoft365_connector")


class Microsoft365Connector(Connector):
    def __init__(self, config: ConnectorConfig, vault_client: Optional[VaultClient] = None):
        self.config = config
        self.vault = vault_client or VaultClient(addr=config.vault_addr)
        self._authenticator: Optional[GraphAuthenticator] = None
        self._discovery: Optional[GraphDiscovery] = None
        self._platform: Optional[PlatformClient] = None
        self._platform_token: Optional[str] = None

    # -- Connector interface -------------------------------------------------

    def authenticate(self) -> None:
        secret = self.vault.get_secret(self.config.client_secret_vault_path)
        self._authenticator = GraphAuthenticator(
            tenant_id=self.config.tenant_id,
            client_id=self.config.client_id,
            client_secret=secret["client_secret"],
            scope=self.config.scope,
            token_url_template=self.config.token_url_template,
        )
        # Fail fast on bad credentials rather than during the first discover().
        self._authenticator.get_token()

        platform_secret = self.vault.get_secret(self.config.platform_api_token_vault_path)
        self._platform_token = platform_secret["api_token"]

        self._discovery = GraphDiscovery(
            base_url=self.config.graph_api_base_url,
            get_access_token=lambda: self._authenticator.get_token().access_token,
            page_size=self.config.page_size,
            audit_log_lookback_hours=self.config.audit_log_lookback_hours,
        )
        self._platform = PlatformClient(
            base_url=self.config.platform_api_base_url,
            get_api_token=lambda: self._platform_token,
            ingest_endpoint=self.config.ingest_endpoint,
            findings_endpoint=self.config.findings_ingest_endpoint,
            batch_size=self.config.batch_size,
        )
        logger.info("Authenticated against Graph API and platform API.")

    def discover(self) -> Dict[str, List[Dict[str, Any]]]:
        resources = [r for r, enabled in self.config.discover_resources.items() if enabled]
        logger.info("Discovering resources: %s", resources)
        return self._discovery.discover(resources)

    def ingest(
        self, raw_objects: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        return self._discovery.ingest(raw_objects)

    def normalize(self, ingested_objects: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Any]]:
        assets = normalize_assets(ingested_objects)
        findings = normalize_findings(ingested_objects)
        logger.info("Normalized %d assets, %d findings.", len(assets), len(findings))
        return {"assets": assets, "findings": findings}

    def push(self, normalized: Dict[str, List[Any]]) -> Dict[str, Any]:
        asset_result = self._platform.push(normalized["assets"])
        findings = normalized.get("findings") or []
        finding_result = (
            self._platform.push_findings(findings)
            if findings
            else {"pushed": 0, "total": 0}
        )
        logger.info(
            "Pushed %d/%d assets, %d/%d findings.",
            asset_result["pushed"],
            asset_result["total"],
            finding_result["pushed"],
            finding_result["total"],
        )
        return {"assets": asset_result, "findings": finding_result}

    def health_check(self) -> Dict[str, Any]:
        try:
            token = self._authenticator.get_token() if self._authenticator else None
            graph_ok = token is not None and token.is_valid()
        except ConnectorError:
            graph_ok = False

        return {
            "graph_api": "ok" if graph_ok else "unreachable",
            "platform_api": "ok" if self._platform_token else "unauthenticated",
        }

    # -- Orchestration ---------------------------------------------------------

    def sync(self) -> Dict[str, Any]:
        raw = self.discover()
        ingested = self.ingest(raw)
        normalized = self.normalize(ingested)
        result = self.push(normalized)
        return {"health": self.health_check(), "push_result": result}

    def run_sync(self) -> Dict[str, Any]:
        self.authenticate()
        return self.sync()
