"""
Load and validate connector configuration from a YAML file.
"""

from dataclasses import dataclass
from typing import Any, Dict

import yaml


@dataclass
class ConnectorConfig:
    tenant_id: str
    client_id: str
    client_secret_vault_path: str
    graph_api_base_url: str
    token_url_template: str
    scope: str
    platform_api_base_url: str
    platform_api_token_vault_path: str
    ingest_endpoint: str
    findings_ingest_endpoint: str
    batch_size: int
    vault_addr: str
    page_size: int
    discover_resources: Dict[str, bool]
    audit_log_lookback_hours: int
    log_level: str

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "ConnectorConfig":
        azure = raw["azure_ad"]
        platform = raw["platform"]
        vault = raw["vault"]
        sync = raw.get("sync", {})
        logging_cfg = raw.get("logging", {})

        return cls(
            tenant_id=azure["tenant_id"],
            client_id=azure["client_id"],
            client_secret_vault_path=azure["client_secret_vault_path"],
            graph_api_base_url=azure["graph_api_base_url"],
            token_url_template=azure["token_url"],
            scope=azure["scope"],
            platform_api_base_url=platform["api_base_url"],
            platform_api_token_vault_path=platform["api_token_vault_path"],
            ingest_endpoint=platform["ingest_endpoint"],
            findings_ingest_endpoint=platform.get(
                "findings_ingest_endpoint", "/api/v1/findings/ingest"
            ),
            batch_size=platform.get("batch_size", 100),
            vault_addr=vault["addr"],
            page_size=sync.get("page_size", 100),
            discover_resources={
                "user": sync.get("discover_users", True),
                "group": sync.get("discover_groups", True),
                "device": sync.get("discover_devices", True),
                "domain": sync.get("discover_domains", True),
                "license": sync.get("discover_licenses", True),
                "audit_log": sync.get("discover_audit_logs", True),
            },
            audit_log_lookback_hours=sync.get("audit_log_lookback_hours", 24),
            log_level=logging_cfg.get("level", "INFO"),
        )


def load_config(path: str) -> ConnectorConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return ConnectorConfig.from_dict(raw)
