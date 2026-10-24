"""
Connector Registry for the Integration Service.

Maintains the catalog of supported connector types, resolves configuration
schemas, and instantiates connectors for health checks and sync jobs.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from app.models import CatalogItem

logger = logging.getLogger(__name__)

# Ensure canonical connector SDK is always resolved first
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_CURRENT_DIR, "..", "..", ".."))
_CANONICAL_SDK = os.path.join(_PROJECT_ROOT, "backend", "connector-sdk")
if _CANONICAL_SDK not in sys.path:
    sys.path.insert(0, _CANONICAL_SDK)

# Supported connector types and metadata
_CATALOG_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "sample": {
        "name": "Sample Reference Connector",
        "category": "reference",
    },
    "aws": {
        "name": "Amazon Web Services (AWS)",
        "category": "cloud",
    },
    "gcp": {
        "name": "Google Cloud Platform (GCP)",
        "category": "cloud",
    },
    "crowdstrike": {
        "name": "CrowdStrike Falcon EDR",
        "category": "edr",
    },
    "jira": {
        "name": "Atlassian Jira Software",
        "category": "itsm",
    },
}


class ConnectorRegistry:
    """Manages connector classes and execution lifecycle."""

    @classmethod
    def get_supported_types(cls) -> List[str]:
        return list(_CATALOG_DEFINITIONS.keys())

    @classmethod
    def get_catalog(cls) -> List[CatalogItem]:
        items: List[CatalogItem] = []
        for c_type, meta in _CATALOG_DEFINITIONS.items():
            connector = cls._instantiate_sandbox(c_type)
            config_schema = connector.describe_config() if hasattr(connector, "describe_config") else {}
            cred_schema = connector.describe_credentials() if hasattr(connector, "describe_credentials") else {}
            items.append(
                CatalogItem(
                    connector_type=c_type,
                    name=meta["name"],
                    category=meta["category"],
                    config_schema=config_schema,
                    credential_schema=cred_schema,
                )
            )
        return items

    @classmethod
    def _instantiate_sandbox(cls, connector_type: str) -> Any:
        """Instantiate a connector with sandbox/mock client for schema inspection or testing."""
        if connector_type == "sample":
            from connector_sdk import SampleConnector
            return SampleConnector()

        elif connector_type == "aws":
            from aws_connector import AWSConnector, FakeAWSClient
            return AWSConnector(client=FakeAWSClient())

        elif connector_type == "gcp":
            from gcp_connector import GCPConnector, FakeGCPClient
            return GCPConnector(project_id="sandbox-project", client=FakeGCPClient())

        elif connector_type == "crowdstrike":
            from crowdstrike_connector import CrowdStrikeConnector, FakeFalconClient
            return CrowdStrikeConnector(client=FakeFalconClient())

        elif connector_type == "jira":
            from jira_connector import JiraConnector, FakeJiraAPIClient
            return JiraConnector(
                base_url="https://sandbox.atlassian.net",
                project_key="SEC",
                client=FakeJiraAPIClient(),
            )

        raise ValueError(f"Unknown connector type: {connector_type}")

    @classmethod
    def instantiate(
        cls,
        connector_type: str,
        config: Dict[str, Any],
        credentials: Dict[str, Any],
    ) -> Any:
        """Instantiate a connector with provided config/credentials.

        If real credentials are provided, attempts live client initialization;
        otherwise defaults gracefully to sandbox test client.
        """
        if connector_type == "sample":
            from connector_sdk import SampleConnector
            simulate_failure = config.get("simulate_failure", False)
            return SampleConnector(simulate_failure=simulate_failure)

        elif connector_type == "aws":
            from aws_connector import AWSConnector, FakeAWSClient
            region = config.get("region", "us-east-1")
            ak = credentials.get("access_key_id")
            sk = credentials.get("secret_access_key")
            if ak and sk:
                return AWSConnector(region=region, access_key_id=ak, secret_access_key=sk)
            return AWSConnector(region=region, client=FakeAWSClient())

        elif connector_type == "gcp":
            from gcp_connector import GCPConnector, FakeGCPClient
            project_id = config.get("project_id", "default-gcp-project")
            creds_json = credentials.get("credentials_json")
            if creds_json:
                return GCPConnector(project_id=project_id, credentials_json=creds_json)
            return GCPConnector(project_id=project_id, client=FakeGCPClient())

        elif connector_type == "crowdstrike":
            from crowdstrike_connector import CrowdStrikeConnector, FakeFalconClient
            cid = credentials.get("client_id")
            csec = credentials.get("client_secret")
            base_url = config.get("base_url", "https://api.crowdstrike.com")
            if cid and csec:
                return CrowdStrikeConnector(client_id=cid, client_secret=csec, base_url=base_url)
            return CrowdStrikeConnector(base_url=base_url, client=FakeFalconClient())

        elif connector_type == "jira":
            from jira_connector import JiraConnector, FakeJiraAPIClient
            base_url = config.get("base_url", "https://enterprise.atlassian.net")
            project_key = config.get("project_key", "SEC")
            email = credentials.get("email")
            token = credentials.get("api_token")
            if email and token:
                return JiraConnector(base_url=base_url, project_key=project_key, email=email, api_token=token)
            return JiraConnector(base_url=base_url, project_key=project_key, client=FakeJiraAPIClient())

        raise ValueError(f"Unsupported connector type: {connector_type}")

    @classmethod
    def test_health(cls, connector_instance: Any) -> bool:
        """Run health check against connector instance."""
        try:
            if hasattr(connector_instance, "check_health"):
                return bool(connector_instance.check_health())
            elif hasattr(connector_instance, "health_check"):
                return bool(connector_instance.health_check())
            return True
        except Exception as exc:
            logger.warning(f"Connector health check failed: {exc}")
            return False

    @classmethod
    def execute_sync(cls, connector_instance: Any) -> Tuple[str, int, int, List[str]]:
        """Run sync cycle and return (status, discovered, pushed, errors)."""
        import asyncio
        import inspect

        raw_result = connector_instance.sync()
        result = asyncio.run(raw_result) if inspect.isawaitable(raw_result) else raw_result

        # Extract values across connector SDK SyncResult model and legacy dicts
        status = getattr(result, "status", "success")
        if hasattr(status, "value"):
            status = status.value
        status = str(status).lower()

        discovered = getattr(result, "assets_discovered", 0)
        pushed = getattr(result, "assets_pushed", 0)
        errors = getattr(result, "errors", [])

        # Fallback if result is a custom object or dict
        if isinstance(result, dict):
            status = result.get("status", "success")
            discovered = result.get("records_synced", result.get("assets_discovered", 0))
            pushed = result.get("assets_pushed", discovered)
            errors = result.get("errors", [])

        return status, discovered, pushed, errors
