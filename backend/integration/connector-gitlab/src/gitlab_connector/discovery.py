"""
Discovery / ingestion logic for GitLab.

GitLab objects we care about:
  - Projects        (GET /groups/{group}/projects, incl. subgroups) -> Assets
  - Vulnerabilities (GET /projects/{id}/vulnerabilities)            -> Findings

Vulnerability data requires GitLab Ultimate (and sufficient project role).
Projects where it is unavailable (HTTP 403/404) are skipped and summarised
in a single warning instead of failing the sync.

Pagination follows the `Link: rel="next"` header (`resp.links`). Rate limits
(HTTP 429) are retried with a capped wait.

SECURITY: vulnerability records can embed raw source-code extracts (which for
secret-detection findings may contain the secret). Those keys are stripped
recursively at ingestion.

Est: 1.5 days (per plan's per-connector standard pattern)
"""

import logging
import time
from typing import Any, Dict, List, Optional

import requests

from .auth import GitLabAuthenticator

logger = logging.getLogger("gitlab_connector")

PER_PAGE = 100
MAX_RETRIES = 3
MAX_WAIT_SECONDS = 60

NON_FATAL_VULN_STATUSES = (403, 404)
OPEN_VULN_STATES = ("detected", "confirmed")

SENSITIVE_KEYS = ("raw_source_code_extract",)


def _scrub(value: Any) -> Any:
    """Recursively drop sensitive keys from dicts/lists."""
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items() if k not in SENSITIVE_KEYS}
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    return value


class GitLabDiscoveryError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


def _wait_seconds(resp) -> int:
    if "Retry-After" in resp.headers:
        wait = int(resp.headers["Retry-After"])
    elif resp.headers.get("RateLimit-Reset"):
        wait = int(resp.headers["RateLimit-Reset"]) - int(time.time())
    else:
        wait = 5
    return max(0, min(wait, MAX_WAIT_SECONDS))


class GitLabDiscovery:
    def __init__(self, authenticator: GitLabAuthenticator, session: Optional[requests.Session] = None):
        self.authenticator = authenticator
        self._session = session or requests.Session()
        self._api_base = authenticator.config.api_base
        self._group_ref = authenticator.config.group_ref
        self.warnings: List[str] = []

    # -- internal ---------------------------------------------------------
    def _request(self, url: str, params: Optional[Dict[str, Any]]):
        for attempt in range(MAX_RETRIES + 1):
            resp = self._session.get(
                url, headers=self.authenticator.auth_headers(), params=params, timeout=30
            )
            if resp.status_code == 429 and attempt < MAX_RETRIES:
                wait = _wait_seconds(resp)
                logger.warning("gitlab_connector.rate_limited url=%s wait=%ss", url, wait)
                time.sleep(wait)
                continue
            if resp.status_code != 200:
                raise GitLabDiscoveryError(
                    f"GET {url} failed: {resp.status_code} {resp.text[:200]}",
                    status_code=resp.status_code,
                )
            return resp
        raise GitLabDiscoveryError(f"GET {url} failed after retries")  # pragma: no cover

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
        """Enumerate all projects in the group and its subgroups (raw)."""
        return self._paginate(
            f"/groups/{self._group_ref}/projects", {"include_subgroups": "true"}
        )

    def ingest(self, projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Pull open vulnerabilities per project and attach them under a
        "vulnerabilities" key. Only detected/confirmed vulnerabilities are kept
        (filtered client-side).
        """
        self.warnings = []
        skipped: Dict[int, int] = {}
        enriched: List[Dict[str, Any]] = []

        for project in projects:
            vulns: List[Dict[str, Any]] = []
            try:
                raw = self._paginate(f"/projects/{project.get('id')}/vulnerabilities")
                vulns = [
                    _scrub(v) for v in raw
                    if (v.get("state") or "detected") in OPEN_VULN_STATES
                ]
            except GitLabDiscoveryError as exc:
                if exc.status_code in NON_FATAL_VULN_STATUSES:
                    skipped[exc.status_code] = skipped.get(exc.status_code, 0) + 1
                else:
                    raise
            enriched.append({**project, "vulnerabilities": vulns})

        if skipped:
            n = sum(skipped.values())
            codes = ", ".join(str(c) for c in sorted(skipped))
            msg = (
                f"vulnerabilities skipped for {n} of {len(projects)} projects "
                f"(HTTP {codes}); requires GitLab Ultimate and a sufficient project role"
            )
            logger.warning("gitlab_connector.%s group=%s", msg, self.authenticator.config.group)
            self.warnings.append(msg)
        return enriched
