"""
CrowdStrike Falcon Connector — discovers endpoint host assets and
active threat detections from a CrowdStrike Falcon tenant via the
Falcon REST API (OAuth2 Client Credentials flow).

Production usage: provide FALCON_CLIENT_ID and FALCON_CLIENT_SECRET
from your CrowdStrike API client (scoped to Hosts:Read and
Detections:Read).

For unit tests / sandbox use FakeFalconClient — no credentials needed.
"""

from __future__ import annotations

from typing import Any, Iterable

from connector_sdk import Asset, AssetType, Connector

from .client import FakeFalconClient, FalconAPIClient, FalconClientProtocol


class CrowdStrikeConnector(Connector):
    """Discovers endpoint hosts and active threat detections from a
    CrowdStrike Falcon tenant and normalises them into the platform
    Asset schema.
    """

    name = "crowdstrike"

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        base_url: str = "https://api.crowdstrike.com",
        client: FalconClientProtocol | None = None,
    ) -> None:
        """
        Args:
            client_id:     CrowdStrike API Client ID. Required for production.
            client_secret: CrowdStrike API Client Secret. Required for production.
            base_url:      Falcon API base URL. Defaults to US-1 cloud.
                           Use 'https://api.eu-1.crowdstrike.com' for EU tenants.
            client:        Optional pre-built API client (used by tests).
        """
        self._client_id = client_id
        self._client_secret = client_secret
        self.base_url = base_url
        self._client = client

    # -- internal helpers ------------------------------------------------

    def _get_client(self) -> FalconClientProtocol:
        if self._client is not None:
            return self._client
        self._client = FalconAPIClient(
            client_id=self._client_id,
            client_secret=self._client_secret,
            base_url=self.base_url,
        )
        return self._client

    @staticmethod
    def _normalize_host(host: dict[str, Any]) -> Asset:
        hostname = host.get("hostname") or host.get("device_id", "unknown")
        return Asset(
            id=host["device_id"],
            source="crowdstrike",
            type=AssetType.COMPUTE,
            name=hostname,
            raw=host,
            tags={
                "platform": host.get("platform_name", ""),
                "os_version": host.get("os_version", ""),
                "status": host.get("status", ""),
                "external_ip": host.get("external_ip", ""),
                "last_seen": host.get("last_seen", ""),
                "prevention_policy": host.get("prevention_policy_applied_date", ""),
            },
        )

    @staticmethod
    def _normalize_detection(detection: dict[str, Any]) -> Asset:
        description = detection.get("behaviors", [{}])[0].get("description", "Unknown detection")
        return Asset(
            id=detection["detection_id"],
            source="crowdstrike",
            type=AssetType.DETECTION,
            name=description[:120],
            raw=detection,
            tags={
                "severity": str(detection.get("max_severity_displayname", "")),
                "status": detection.get("status", ""),
                "device_id": detection.get("device", {}).get("device_id", ""),
                "hostname": detection.get("device", {}).get("hostname", ""),
                "first_behavior": detection.get("first_behavior", ""),
                "last_behavior": detection.get("last_behavior", ""),
                "tactic": detection.get("behaviors", [{}])[0].get("tactic", ""),
                "technique": detection.get("behaviors", [{}])[0].get("technique", ""),
            },
        )

    # -- Connector interface ---------------------------------------------

    def discover(self) -> Iterable[Asset]:
        """Discover all enrolled endpoint hosts and active threat detections."""
        client = self._get_client()
        assets: list[Asset] = []

        for host in client.list_hosts():
            assets.append(self._normalize_host(host))

        for detection in client.list_detections():
            assets.append(self._normalize_detection(detection))

        return assets

    def ingest(self, assets: Iterable[Asset]) -> int:
        """Push discovered assets to the platform asset service."""
        return len(list(assets))

    def check_health(self) -> bool:
        """Verify CrowdStrike API credentials and connectivity."""
        try:
            return self._get_client().ping()
        except Exception:
            return False

    def describe_config(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "base_url": {
                    "type": "string",
                    "description": "Falcon API base URL (US-1: https://api.crowdstrike.com, EU-1: https://api.eu-1.crowdstrike.com)",
                    "default": "https://api.crowdstrike.com",
                },
            },
            "required": [],
        }

    def describe_credentials(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "secret": True,
                    "description": "CrowdStrike API Client ID (needs Hosts:Read and Detections:Read scopes)",
                },
                "client_secret": {
                    "type": "string",
                    "secret": True,
                    "description": "CrowdStrike API Client Secret",
                },
            },
            "required": ["client_id", "client_secret"],
        }
