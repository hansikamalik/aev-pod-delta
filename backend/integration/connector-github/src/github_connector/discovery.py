"""
Discovery / ingestion logic for GitHub.

GitHub objects we care about:
  - Repositories                 (GET /orgs/{org}/repos)               -> Assets
  - Dependabot alerts            (GET /orgs/{org}/dependabot/alerts)   -> Findings
  - Code scanning alerts         (GET /orgs/{org}/code-scanning/alerts)-> Findings
  - Secret scanning alerts       (GET /orgs/{org}/secret-scanning/alerts) -> Findings

Pagination is via the `Link: rel="next"` header (requests exposes it as
`resp.links`). Rate limits (429, or 403 with X-RateLimit-Remaining: 0)
are retried with a capped wait.

SECURITY: secret-scanning alerts include the leaked secret value in a
`secret` field. It is stripped here so it never enters raw records,
logs, or the push payload.

Est: 1.5 days (per plan's per-connector standard pattern)
"""

import logging
import time
from typing import Any, Dict, List, Optional

import requests

from .auth import GitHubAuthenticator

logger = logging.getLogger("github_connector")

PER_PAGE = 100
MAX_RETRIES = 3
MAX_WAIT_SECONDS = 60

# Alert features may be disabled / not licensed / not permitted for a token.
# These statuses skip that alert type with a warning instead of failing the sync.
NON_FATAL_ALERT_STATUSES = (403, 404, 410, 451)

ALERT_ENDPOINTS = {
    "dependabot": "/orgs/{org}/dependabot/alerts",
    "code_scanning": "/orgs/{org}/code-scanning/alerts",
    "secret_scanning": "/orgs/{org}/secret-scanning/alerts",
}

SENSITIVE_ALERT_KEYS = ("secret",)


class GitHubDiscoveryError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


def _is_rate_limited(resp) -> bool:
    if resp.status_code == 429:
        return True
    return resp.status_code == 403 and (
        resp.headers.get("X-RateLimit-Remaining") == "0" or "Retry-After" in resp.headers
    )


def _wait_seconds(resp) -> int:
    if "Retry-After" in resp.headers:
        wait = int(resp.headers["Retry-After"])
    elif resp.headers.get("X-RateLimit-Reset"):
        wait = int(resp.headers["X-RateLimit-Reset"]) - int(time.time())
    else:
        wait = 5
    return max(0, min(wait, MAX_WAIT_SECONDS))


class GitHubDiscovery:
    def __init__(self, authenticator: GitHubAuthenticator, session: Optional[requests.Session] = None):
        self.authenticator = authenticator
        self._session = session or requests.Session()
        self._api_base = authenticator.config.api_base
        self._org = authenticator.config.org
        self.warnings: List[str] = []

    # -- internal ---------------------------------------------------------
    def _request(self, url: str, params: Optional[Dict[str, Any]]):
        for attempt in range(MAX_RETRIES + 1):
            resp = self._session.get(
                url, headers=self.authenticator.auth_headers(), params=params, timeout=30
            )
            if _is_rate_limited(resp) and attempt < MAX_RETRIES:
                wait = _wait_seconds(resp)
                logger.warning("github_connector.rate_limited url=%s wait=%ss", url, wait)
                time.sleep(wait)
                continue
            if resp.status_code != 200:
                raise GitHubDiscoveryError(
                    f"GET {url} failed: {resp.status_code} {resp.text[:200]}",
                    status_code=resp.status_code,
                )
            return resp
        raise GitHubDiscoveryError(f"GET {url} failed after retries")  # pragma: no cover

    def _paginate(self, path: str, extra_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        url: Optional[str] = f"{self._api_base}{path}"
        params: Optional[Dict[str, Any]] = {"per_page": PER_PAGE, **(extra_params or {})}
        while url:
            resp = self._request(url, params)
            data = resp.json()
            records.extend(data if isinstance(data, list) else [])
            url = (resp.links.get("next") or {}).get("url")
            params = None  # the next URL already carries the query string
        return records

    # -- public -----------------------------------------------------------
    def discover(self) -> List[Dict[str, Any]]:
        """Enumerate all repositories in the org (raw, pre-normalization)."""
        return self._paginate(f"/orgs/{self._org}/repos", {"type": "all"})

    def ingest(self, repos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Pull open security alerts and attach each to its repository under an
        "alerts" key (each alert tagged with "_alert_type"). Alerts whose repo
        is not in `repos` are kept on a synthetic record, never dropped.
        """
        self.warnings = []
        by_repo: Dict[str, List[Dict[str, Any]]] = {}

        for kind, path in ALERT_ENDPOINTS.items():
            try:
                alerts = self._paginate(path.format(org=self._org), {"state": "open"})
            except GitHubDiscoveryError as exc:
                if exc.status_code in NON_FATAL_ALERT_STATUSES:
                    msg = f"{kind} alerts skipped (HTTP {exc.status_code})"
                    logger.warning("github_connector.%s org=%s", msg, self._org)
                    self.warnings.append(msg)
                    continue
                raise
            for alert in alerts:
                clean = {k: v for k, v in alert.items() if k not in SENSITIVE_ALERT_KEYS}
                clean["_alert_type"] = kind
                repo_id = str((alert.get("repository") or {}).get("id", ""))
                by_repo.setdefault(repo_id, []).append(clean)

        enriched = [{**r, "alerts": by_repo.pop(str(r.get("id", "")), [])} for r in repos]

        orphaned = [a for alerts in by_repo.values() for a in alerts]
        if orphaned:
            enriched.append({"_orphaned_alerts": True, "alerts": orphaned})
        return enriched
