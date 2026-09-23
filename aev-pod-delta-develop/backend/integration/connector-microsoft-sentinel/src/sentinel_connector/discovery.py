"""
Discovery / ingestion logic for Microsoft Sentinel.

Sentinel's core objects for our purposes are:
  - Incidents (mapped to Findings)
  - Security Alerts underlying each incident
  - Entities referenced by alerts (hosts, accounts, IPs) -> mapped to Assets

Est: 1.5 days (per plan's per-connector standard pattern)

API reference (for whoever picks this up): Microsoft Sentinel incidents
sit under the Azure Resource Manager path:
  /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.OperationalInsights/
  workspaces/{workspace}/providers/Microsoft.SecurityInsights/incidents

TODO(Harshal): confirm API version pin (using 2023-11-01 as a
placeholder below) against whatever the org's current ARM API version
policy is.
"""

from typing import Any, Dict, List, Optional

import requests

from .auth import SentinelAuthenticator

ARM_BASE = "https://management.azure.com"
API_VERSION = "2023-11-01"


class SentinelDiscoveryError(Exception):
    pass


class SentinelDiscovery:
    def __init__(self, authenticator: SentinelAuthenticator, session: Optional[requests.Session] = None):
        self.authenticator = authenticator
        self._session = session or requests.Session()
        cfg = authenticator.config
        self._incidents_url = (
            f"{ARM_BASE}/subscriptions/{cfg.subscription_id}/resourceGroups/"
            f"{cfg.resource_group}/providers/Microsoft.OperationalInsights/"
            f"workspaces/{cfg.workspace_name}/providers/Microsoft.SecurityInsights/"
            f"incidents"
        )

    def discover(self, top: int = 100) -> List[Dict[str, Any]]:
        """
        Page through Sentinel incidents. Returns the raw list of
        incident dicts as returned by the API (pre-normalization).
        """
        incidents: List[Dict[str, Any]] = []
        url = self._incidents_url
        params = {"api-version": API_VERSION, "$top": top}

        while url:
            resp = self._session.get(url, headers=self.authenticator.auth_headers(), params=params, timeout=30)
            if resp.status_code != 200:
                raise SentinelDiscoveryError(
                    f"Incident list failed: {resp.status_code} {resp.text[:200]}"
                )
            payload = resp.json()
            incidents.extend(payload.get("value", []))
            url = payload.get("nextLink")
            params = None  # nextLink already carries query params

        return incidents

    def ingest(self, incidents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        For each discovered incident, pull the related entities
        (accounts, hosts, IPs) that back the Asset normalization step.
        Returns incidents enriched with an "entities" key.
        """
        enriched = []
        for incident in incidents:
            incident_id = incident.get("name")
            entities_url = f"{self._incidents_url}/{incident_id}/entities"
            resp = self._session.post(
                entities_url,
                headers=self.authenticator.auth_headers(),
                params={"api-version": API_VERSION},
                timeout=30,
            )
            entities: List[Dict[str, Any]] = []
            if resp.status_code == 200:
                entities = resp.json().get("entities", [])
            else:
                # Non-fatal: keep the incident, just without entities.
                # Logged upstream by the connector's sync loop.
                pass

            enriched.append({**incident, "entities": entities})

        return enriched
