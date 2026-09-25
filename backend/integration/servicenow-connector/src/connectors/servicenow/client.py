"""Thin ServiceNow REST client with pagination + bounded retry."""

from __future__ import annotations

import time
from typing import Any, Dict, Iterator, Optional

import requests

from .auth import ServiceNowAuth


class ServiceNowAPIError(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(f"ServiceNow API error {status}: {body[:300]}")
        self.status = status
        self.body = body


class ServiceNowClient:
    """Wraps Table API GET calls. Auth headers come from ServiceNowAuth."""

    RETRYABLE_STATUS = {429, 500, 502, 503, 504}
    BACKOFF_SECONDS = (1, 2, 4)

    def __init__(
        self,
        auth: ServiceNowAuth,
        timeout: int = 30,
        max_retries: int = 3,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.auth = auth
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = session or requests.Session()

    # ------------------------------------------------------------------ #
    def get_table(
        self,
        table: str,
        params: Optional[Dict[str, Any]] = None,
        batch_size: int = 200,
    ) -> Iterator[Dict[str, Any]]:
        """Yield every record of a table via offset pagination."""
        params = dict(params or {})
        params.setdefault("sysparm_limit", batch_size)
        params.setdefault("sysparm_offset", 0)
        params.setdefault("sysparm_exclude_reference_link", "true")

        while True:
            page = self._request("GET", f"/api/now/table/{table}", params=params)
            records = page.get("result") or []
            if not records:
                return
            yield from records
            if len(records) < params["sysparm_limit"]:
                return
            params["sysparm_offset"] += params["sysparm_limit"]

    # ------------------------------------------------------------------ #
    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        url = self.auth.instance_url + path
        headers = self.auth.auth_headers()
        headers.setdefault("Accept", "application/json")
        last_exc: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                resp = self.session.request(
                    method, url, headers=headers, timeout=self.timeout, **kwargs
                )
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(self.BACKOFF_SECONDS[min(attempt, 2)])
                    continue
                raise

            if resp.status_code in self.RETRYABLE_STATUS and attempt < self.max_retries:
                time.sleep(self.BACKOFF_SECONDS[min(attempt, 2)])
                continue
            if resp.status_code >= 400:
                raise ServiceNowAPIError(resp.status_code, resp.text)
            if not resp.content:
                return {}
            return resp.json()

        if last_exc:
            raise last_exc
        raise ServiceNowAPIError(-1, "exhausted retries")
