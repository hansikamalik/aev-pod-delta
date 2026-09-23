"""
Discovery/ingestion against Microsoft Graph.

discover() enumerates raw objects (paginating through @odata.nextLink);
ingest() is a thin pass-through here since list responses already carry the
full object — kept as a separate step to match the connector interface and
give a seam for a future per-object detail fetch (e.g. sign-in activity).

"audit_log" is discovered the same paginated way as everything else, but
through directoryAudits with a time-window $filter rather than a plain list.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional

import requests

from .exceptions import DiscoveryError

RESOURCE_ENDPOINTS = {
    "user": "/users",
    "group": "/groups",
    "device": "/devices",
    "domain": "/domains",
    "license": "/subscribedSkus",
    "audit_log": "/auditLogs/directoryAudits",
}


class GraphDiscovery:
    def __init__(
        self,
        base_url: str,
        get_access_token: Callable[[], str],
        page_size: int = 100,
        audit_log_lookback_hours: int = 24,
        timeout: float = 15.0,
        session: Optional[requests.Session] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.get_access_token = get_access_token
        self.page_size = page_size
        self.audit_log_lookback_hours = audit_log_lookback_hours
        self.timeout = timeout
        self.session = session or requests.Session()

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.get_access_token()}"}

    def _paged_get(
        self, url: str, params: Optional[Dict[str, Any]] = None
    ) -> Iterable[Dict[str, Any]]:
        next_url, next_params = url, params
        while next_url:
            try:
                resp = self.session.get(
                    next_url,
                    headers=self._headers(),
                    params=next_params,
                    timeout=self.timeout,
                )
                resp.raise_for_status()
            except requests.RequestException as exc:
                raise DiscoveryError(
                    f"Graph API request to {next_url} failed: {exc}"
                ) from exc

            body = resp.json()
            for item in body.get("value", []):
                yield item

            next_url = body.get("@odata.nextLink")
            next_params = None  # nextLink already carries its own query params

    def discover_resource(self, resource: str) -> List[Dict[str, Any]]:
        if resource not in RESOURCE_ENDPOINTS:
            raise DiscoveryError(f"Unknown resource type: {resource}")
        url = f"{self.base_url}{RESOURCE_ENDPOINTS[resource]}"
        params = {"$top": self.page_size}
        return list(self._paged_get(url, params))

    def discover_audit_logs(self) -> List[Dict[str, Any]]:
        since = (
            datetime.now(timezone.utc) - timedelta(hours=self.audit_log_lookback_hours)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        url = f"{self.base_url}{RESOURCE_ENDPOINTS['audit_log']}"
        params = {"$top": self.page_size, "$filter": f"activityDateTime ge {since}"}
        return list(self._paged_get(url, params))

    def discover(
        self, resources: Optional[Iterable[str]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        resources = list(resources or RESOURCE_ENDPOINTS.keys())
        result: Dict[str, List[Dict[str, Any]]] = {}
        for resource in resources:
            if resource == "audit_log":
                result[resource] = self.discover_audit_logs()
            else:
                result[resource] = self.discover_resource(resource)
        return result

    def ingest(
        self, raw_by_resource: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        # Pass-through for now — list responses already carry full objects.
        return raw_by_resource
