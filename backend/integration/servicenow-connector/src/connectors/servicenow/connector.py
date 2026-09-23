"""ServiceNowConnector — implements the 6-method connector interface.

    authenticate()   -> resolve credentials (env / Vault) and build auth handler
    discover()       -> enumerate owned tables + probe reachability
    ingest()         -> stream raw ServiceNow records
    normalize()      -> map raw records to shared Asset / Finding shapes
    push()           -> upsert normalized records to the Beta platform
    health_check()   -> end-to-end liveness probe (auth + one table read + push noop)
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests
import yaml

from .auth import ServiceNowAuth
from .client import ServiceNowClient
from .discovery import DiscoveryResult, discover
from .ingestion import ingest
from .normalize import normalize_ci, normalize_incident
from .push import PlatformPusher
from .vault import VaultClient

DEFAULT_CONFIG = "config/servicenow.yaml"


def load_config(path: str = DEFAULT_CONFIG) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


class ServiceNowConnector:
    """Six-method connector for ServiceNow CMDB + security incidents."""

    SOURCE = "servicenow"

    def __init__(self, config: Optional[Dict[str, Any]] = None,
                 config_path: str = DEFAULT_CONFIG,
                 session: Optional[requests.Session] = None) -> None:
        self.config = config if config is not None else load_config(config_path)
        self._session = session or requests.Session()
        self._auth: Optional[ServiceNowAuth] = None
        self._client: Optional[ServiceNowClient] = None
        self._pusher: Optional[PlatformPusher] = None

    # 1 --------------------------------------------------------------- #
    def authenticate(self) -> ServiceNowAuth:
        """Resolve credentials (explicit config -> env -> Vault) and build auth."""
        cfg = self.config
        auth_cfg = cfg.get("auth", {})
        username = auth_cfg.get("username") or os.environ.get("SN_USERNAME")
        password = auth_cfg.get("password") or os.environ.get("SN_PASSWORD")
        client_id = auth_cfg.get("oauth_client_id") or os.environ.get("SN_OAUTH_CLIENT_ID")
        client_secret = (
            auth_cfg.get("oauth_client_secret") or os.environ.get("SN_OAUTH_CLIENT_SECRET")
        )

        vault_cfg = cfg.get("vault", {})
        if vault_cfg.get("enabled") and not (username and password):
            creds = VaultClient(session=self._session).read_connector_credentials(vault_cfg)
            username = username or creds.username
            password = password or creds.password
            client_id = client_id or creds.oauth_client_id
            client_secret = client_secret or creds.oauth_client_secret

        self._auth = ServiceNowAuth(
            instance_url=os.environ.get("SN_INSTANCE_URL", cfg["instance_url"]),
            method=os.environ.get("SN_AUTH_METHOD", auth_cfg.get("method", "basic")),
            username=username,
            password=password,
            oauth_client_id=client_id,
            oauth_client_secret=client_secret,
            timeout=cfg.get("timeout_seconds", 30),
            session=self._session,
        )
        return self._auth

    # 2 --------------------------------------------------------------- #
    def discover(self) -> DiscoveryResult:
        return discover(self._require_client(), self.config.get("tables", {}))

    # 3 --------------------------------------------------------------- #
    def ingest(self):
        return ingest(
            self._require_client(),
            self.config.get("tables", {}),
            batch_size=self.config.get("batch_size", 200),
        )

    # 4 --------------------------------------------------------------- #
    def normalize(self, raw_records):
        """Accept the (assets, findings) tuple from ingest(); yield normalized dicts."""
        assets_raw, findings_raw = raw_records
        for rec in assets_raw:
            yield normalize_ci(rec, source=self.SOURCE)
        for rec in findings_raw:
            yield normalize_incident(rec, source=self.SOURCE)

    # 5 --------------------------------------------------------------- #
    def push(self, normalized_records) -> Dict[str, int]:
        """Split the stream by shape and push to asset vs exposure services."""
        pusher = self._require_pusher()
        assets, findings = [], []
        for rec in normalized_records:
            (assets if "asset_id" in rec and "title" not in rec else findings).append(rec)

        stats = {"assets": {"sent": 0, "accepted": 0, "failed": 0},
                 "findings": {"sent": 0, "accepted": 0, "failed": 0}}
        if assets:
            stats["assets"] = pusher.push_assets(iter(assets))
        if findings:
            stats["findings"] = pusher.push_findings(iter(findings))
        return stats

    # 6 --------------------------------------------------------------- #
    def health_check(self) -> Dict[str, Any]:
        """Verify instance reachability, auth validity, and push endpoint shape."""
        ok, detail = self.authenticate().verify()
        result: Dict[str, Any] = {"auth_ok": ok, "auth_detail": detail, "tables_ok": {}}
        if ok:
            client = self._require_client()
            for key, table in self.config.get("tables", {}).items():
                try:
                    next(client.get_table(table, params={"sysparm_limit": 1}, batch_size=1), None)
                    result["tables_ok"][table] = True
                except Exception as exc:  # noqa: BLE001
                    result["tables_ok"][table] = f"error: {exc}"
        result["overall_ok"] = ok and all(v is True for v in result["tables_ok"].values())
        return result

    # ------------------------------------------------------------------ #
    def _require_client(self) -> ServiceNowClient:
        if self._client is None:
            self._client = ServiceNowClient(
                self.authenticate(),
                timeout=self.config.get("timeout_seconds", 30),
                max_retries=self.config.get("max_retries", 3),
                session=self._session,
            )
        return self._client

    def _require_pusher(self) -> PlatformPusher:
        if self._pusher is None:
            push_cfg = self.config.get("push", {})
            self._pusher = PlatformPusher(
                asset_url=os.environ.get("AEV_ASSET_URL", push_cfg["asset_url"]),
                exposure_url=os.environ.get("AEV_EXPOSURE_URL", push_cfg["exposure_url"]),
                session=self._session,
            )
        return self._pusher

    # ------------------------------------------------------------------ #
    def run_sync(self) -> Dict[str, Any]:
        """Convenience: full pipeline discover -> ingest -> normalize -> push."""
        discovery = self.discover()
        raw = self.ingest()
        normalized = list(self.normalize(raw))
        stats = self.push(iter(normalized))
        return {"discovery": discovery, "stats": stats, "records": len(normalized)}
