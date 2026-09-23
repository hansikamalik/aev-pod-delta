"""
Discovery / ingestion logic for SentinelOne.

SentinelOne objects we care about:
  - Agents  (GET /agents)  -> mapped to Assets (endpoints/servers)
  - Threats (GET /threats) -> mapped to Findings

Both endpoints use cursor pagination: pass `limit` (max 1000) and
`cursor`; the response carries `data` and `pagination.nextCursor`.

Est: 1.5 days (per plan's per-connector standard pattern)
"""

import logging
import time
from typing import Any, Dict, List, Optional

import requests

from .auth import SentinelOneAuthenticator

logger = logging.getLogger("sentinelone_connector")

PAGE_LIMIT = 1000
MAX_RETRIES = 3


class SentinelOneDiscoveryError(Exception):
    pass


class SentinelOneDiscovery:
    def __init__(self, authenticator: SentinelOneAuthenticator, session: Optional[requests.Session] = None):
        self.authenticator = authenticator
        self._session = session or requests.Session()
        self._api_base = authenticator.config.api_base

    # -- internal ---------------------------------------------------------
    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """GET with basic 429 backoff (SentinelOne throttles under load)."""
        url = f"{self._api_base}{path}"
        for attempt in range(MAX_RETRIES + 1):
            resp = self._session.get(
                url, headers=self.authenticator.auth_headers(), params=params, timeout=30
            )
            if resp.status_code == 429 and attempt < MAX_RETRIES:
                wait = int(resp.headers.get("Retry-After", 2 ** attempt))
                logger.warning("sentinelone_connector.rate_limited path=%s wait=%ss", path, wait)
                time.sleep(wait)
                continue
            if resp.status_code != 200:
                raise SentinelOneDiscoveryError(
                    f"GET {path} failed: {resp.status_code} {resp.text[:200]}"
                )
            return resp.json()
        raise SentinelOneDiscoveryError(f"GET {path} failed after retries")  # pragma: no cover

    def _paginate(self, path: str, extra_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        params: Dict[str, Any] = {"limit": PAGE_LIMIT, **(extra_params or {})}
        while True:
            payload = self._get(path, params)
            records.extend(payload.get("data", []))
            next_cursor = (payload.get("pagination") or {}).get("nextCursor")
            if not next_cursor:
                break
            params = {**params, "cursor": next_cursor}
        return records

    # -- public -----------------------------------------------------------
    def discover(self) -> List[Dict[str, Any]]:
        """Enumerate all agents (raw, pre-normalization)."""
        return self._paginate("/agents")

    def ingest(self, agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Pull threats and attach each to its agent under a "threats" key.
        Threats whose agent is not in `agents` are kept on a synthetic
        record so no finding is silently dropped.
        """
        threats = self._paginate("/threats")

        by_agent: Dict[str, List[Dict[str, Any]]] = {}
        for t in threats:
            agent_id = (t.get("agentRealtimeInfo") or {}).get("agentId", "")
            by_agent.setdefault(agent_id, []).append(t)

        enriched = [{**a, "threats": by_agent.pop(a.get("id", ""), [])} for a in agents]

        orphaned = [t for ts in by_agent.values() for t in ts]
        if orphaned:
            enriched.append({"_orphaned_threats": True, "threats": orphaned})
        return enriched
