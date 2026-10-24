"""
Thin wrapper around the CrowdStrike Falcon REST API.

FalconAPIClient  — production implementation using OAuth2 + requests (lazy import).
FakeFalconClient — canned data for unit tests and sandbox — no credentials needed.
"""

from __future__ import annotations

from typing import Any, Protocol


class FalconClientProtocol(Protocol):
    def list_hosts(self) -> list[dict[str, Any]]: ...
    def list_detections(self) -> list[dict[str, Any]]: ...
    def ping(self) -> bool: ...


class FalconAPIClient:
    """Production client using OAuth2 Client Credentials + requests.

    requests is imported lazily so this module stays importable in unit
    tests without network dependencies installed.
    """

    def __init__(
        self,
        client_id: str | None,
        client_secret: str | None,
        base_url: str = "https://api.crowdstrike.com",
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self.base_url = base_url.rstrip("/")
        self._token: str | None = None

    def _get_token(self) -> str:
        """Obtain a short-lived OAuth2 bearer token."""
        import requests  # type: ignore

        resp = requests.post(
            f"{self.base_url}/oauth2/token",
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
            timeout=15,
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    def _headers(self) -> dict[str, str]:
        token = self._token or self._get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        import requests  # type: ignore

        resp = requests.get(
            f"{self.base_url}{path}",
            headers=self._headers(),
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def list_hosts(self) -> list[dict[str, Any]]:
        """Page through all host device IDs then fetch full device details."""
        ids: list[str] = []
        offset = 0
        limit = 100
        while True:
            data = self._get("/devices/queries/devices/v1", params={"limit": limit, "offset": offset})
            batch = data.get("resources", [])
            ids.extend(batch)
            meta = data.get("meta", {}).get("pagination", {})
            total = meta.get("total", 0)
            offset += len(batch)
            if offset >= total or not batch:
                break

        if not ids:
            return []

        # Fetch full device details in batches of 100
        hosts: list[dict[str, Any]] = []
        for i in range(0, len(ids), 100):
            batch_ids = ids[i : i + 100]
            detail = self._get(
                "/devices/entities/devices/v2",
                params={"ids": batch_ids},
            )
            hosts.extend(detail.get("resources", []))
        return hosts

    def list_detections(self) -> list[dict[str, Any]]:
        """Page through active detection IDs then fetch full detection details."""
        ids: list[str] = []
        offset = 0
        limit = 100
        while True:
            data = self._get(
                "/detects/queries/detects/v1",
                params={"limit": limit, "offset": offset, "filter": "status:'new'+status:'in_progress'"},
            )
            batch = data.get("resources", [])
            ids.extend(batch)
            meta = data.get("meta", {}).get("pagination", {})
            total = meta.get("total", 0)
            offset += len(batch)
            if offset >= total or not batch:
                break

        if not ids:
            return []

        import requests  # type: ignore

        resp = requests.post(
            f"{self.base_url}/detects/entities/summaries/GET/v1",
            headers=self._headers(),
            json={"ids": ids},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("resources", [])

    def ping(self) -> bool:
        try:
            self._get_token()
            return True
        except Exception:
            return False


class FakeFalconClient:
    """Canned data for unit tests and sandbox — no CrowdStrike credentials needed."""

    def __init__(self, fail_ping: bool = False) -> None:
        self._fail_ping = fail_ping

    def list_hosts(self) -> list[dict[str, Any]]:
        return [
            {
                "device_id": "abc123def456789",
                "hostname": "LAPTOP-FINTECH-001",
                "platform_name": "Windows",
                "os_version": "Windows 11",
                "status": "normal",
                "external_ip": "203.0.113.10",
                "last_seen": "2026-10-24T18:30:00Z",
                "prevention_policy_applied_date": "2026-09-01T00:00:00Z",
            },
            {
                "device_id": "xyz987uvw654321",
                "hostname": "WORKSTATION-TRADER-05",
                "platform_name": "Windows",
                "os_version": "Windows 10",
                "status": "contained",
                "external_ip": "203.0.113.55",
                "last_seen": "2026-10-24T17:00:00Z",
                "prevention_policy_applied_date": "2026-09-01T00:00:00Z",
            },
            {
                "device_id": "linux001ubuntu22",
                "hostname": "api-server-prod",
                "platform_name": "Linux",
                "os_version": "Ubuntu 22.04",
                "status": "normal",
                "external_ip": "203.0.113.100",
                "last_seen": "2026-10-24T20:00:00Z",
                "prevention_policy_applied_date": "2026-09-15T00:00:00Z",
            },
        ]

    def list_detections(self) -> list[dict[str, Any]]:
        return [
            {
                "detection_id": "ldt:abc123def456789:11223344556677",
                "status": "new",
                "max_severity_displayname": "High",
                "first_behavior": "2026-10-24T16:45:00Z",
                "last_behavior": "2026-10-24T16:47:00Z",
                "device": {
                    "device_id": "abc123def456789",
                    "hostname": "LAPTOP-FINTECH-001",
                },
                "behaviors": [
                    {
                        "description": "Suspicious PowerShell execution attempting to disable Windows Defender",
                        "tactic": "Defense Evasion",
                        "technique": "Impair Defenses",
                    }
                ],
            },
            {
                "detection_id": "ldt:xyz987uvw654321:99887766554433",
                "status": "in_progress",
                "max_severity_displayname": "Critical",
                "first_behavior": "2026-10-24T14:00:00Z",
                "last_behavior": "2026-10-24T14:30:00Z",
                "device": {
                    "device_id": "xyz987uvw654321",
                    "hostname": "WORKSTATION-TRADER-05",
                },
                "behaviors": [
                    {
                        "description": "Ransomware-like file encryption activity detected across multiple directories",
                        "tactic": "Impact",
                        "technique": "Data Encrypted for Impact",
                    }
                ],
            },
        ]

    def ping(self) -> bool:
        return not self._fail_ping
