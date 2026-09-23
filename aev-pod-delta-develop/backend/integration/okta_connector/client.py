"""
Thin HTTP client over the Okta Users and Groups APIs.

Kept deliberately small: just enough to list users, list groups, and list a
group's members, with the token-based auth header and simple pagination
handling. Network calls go through `requests` so they're easy to mock in
tests (see tests/test_okta_connector.py).
"""

from __future__ import annotations

from typing import Any, Dict, List

import requests

from .credentials import OktaCredentials

DEFAULT_TIMEOUT = 10  # seconds
DEFAULT_PAGE_LIMIT = 200


class OktaAPIError(RuntimeError):
    """Raised when the Okta API returns a non-2xx response."""


class OktaClient:
    def __init__(self, credentials: OktaCredentials, session: requests.Session | None = None):
        self._creds = credentials
        self._session = session or requests.Session()

    def _get(self, path: str, params: Dict[str, Any] | None = None) -> requests.Response:
        url = f"{self._creds.org_url}{path}"
        resp = self._session.get(
            url, headers=self._creds.auth_header(), params=params, timeout=DEFAULT_TIMEOUT
        )
        if resp.status_code != 200:
            raise OktaAPIError(f"GET {path} failed: {resp.status_code} {resp.text}")
        return resp

    def _paginate(self, path: str, params: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """Follow Okta's Link-header pagination and return every record."""
        records: List[Dict[str, Any]] = []
        params = dict(params or {})
        params.setdefault("limit", DEFAULT_PAGE_LIMIT)

        next_url = f"{self._creds.org_url}{path}"
        next_params: Dict[str, Any] | None = params

        while next_url:
            resp = self._session.get(
                next_url, headers=self._creds.auth_header(), params=next_params, timeout=DEFAULT_TIMEOUT
            )
            if resp.status_code != 200:
                raise OktaAPIError(f"GET {path} failed: {resp.status_code} {resp.text}")
            records.extend(resp.json())

            next_url = None
            next_params = None
            link_header = resp.headers.get("Link", "")
            for link in link_header.split(","):
                if 'rel="next"' in link:
                    next_url = link.split(";")[0].strip().strip("<>")

        return records

    def list_users(self) -> List[Dict[str, Any]]:
        """GET /api/v1/users -- all users in the org, paginated."""
        return self._paginate("/api/v1/users")

    def list_groups(self) -> List[Dict[str, Any]]:
        """GET /api/v1/groups -- all groups in the org, paginated."""
        return self._paginate("/api/v1/groups")

    def list_group_members(self, group_id: str) -> List[Dict[str, Any]]:
        """GET /api/v1/groups/{id}/users -- members of a single group."""
        return self._paginate(f"/api/v1/groups/{group_id}/users")

    def health_check(self) -> bool:
        """Lightweight call to confirm the token and org URL are valid."""
        try:
            resp = self._get("/api/v1/users", params={"limit": 1})
            return resp.status_code == 200
        except OktaAPIError:
            return False
