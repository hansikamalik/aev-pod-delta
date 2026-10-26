"""
Thin wrapper around the Jira Cloud REST API v3 endpoints this connector
needs:

  - GET  /rest/api/3/search              (list existing tickets by JQL)
  - POST /rest/api/3/issue                (create a ticket from an exposure)
  - GET  /rest/api/3/myself               (health check)

`JiraAPIClient` is the production implementation, built on `requests`.
`FakeJiraAPIClient` returns canned data with the same shape and is what
the connector is exercised against in this sandbox (no network access)
and in unit tests -- same pattern as the AWS/Azure/GCP connectors'
sandbox-account testing approach.
"""

from __future__ import annotations

from typing import Any, Protocol


class JiraClientProtocol(Protocol):
    def search_issues(self, jql: str) -> list[dict[str, Any]]: ...

    def create_issue(self, project_key: str, summary: str, description: str, labels: list[str]) -> dict[str, Any]: ...

    def ping(self) -> bool: ...


class JiraAPIClient:
    """Production client, backed by `requests`.

    `requests` is imported lazily so this module stays importable
    without the dependency installed (e.g. for schema inspection or
    unit tests using the fake client).
    """

    def __init__(self, base_url: str, auth_headers: dict[str, str]) -> None:
        self.base_url = base_url.rstrip("/")
        self._auth_headers = auth_headers

    def _session(self):
        import requests  # type: ignore

        session = requests.Session()
        session.headers.update(self._auth_headers)
        session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        return session

    def search_issues(self, jql: str) -> list[dict[str, Any]]:
        session = self._session()
        issues: list[dict[str, Any]] = []
        start_at = 0
        while True:
            resp = session.get(
                f"{self.base_url}/rest/api/3/search",
                params={"jql": jql, "startAt": start_at, "maxResults": 50},
                timeout=30,
            )
            resp.raise_for_status()
            page = resp.json()
            issues.extend(page.get("issues", []))
            start_at += len(page.get("issues", []))
            if start_at >= page.get("total", 0) or not page.get("issues"):
                break
        return issues

    def create_issue(self, project_key: str, summary: str, description: str, labels: list[str]) -> dict[str, Any]:
        session = self._session()
        body = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "issuetype": {"name": "Task"},
                "labels": labels,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": description}]},
                    ],
                },
            }
        }
        resp = session.post(f"{self.base_url}/rest/api/3/issue", json=body, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def ping(self) -> bool:
        try:
            resp = self._session().get(f"{self.base_url}/rest/api/3/myself", timeout=10)
            return resp.status_code == 200
        except Exception:
            return False


class FakeJiraAPIClient:
    """Canned data standing in for a real Jira site. Used for unit tests
    and for integration testing in this sandbox, which has no network
    access -- mirrors the AWS/Azure/GCP connectors' sandbox-account
    testing approach.
    """

    def __init__(self, fail_ping: bool = False) -> None:
        self._fail_ping = fail_ping
        self._next_id = 1001
        self.created_issues: list[dict[str, Any]] = []

    def search_issues(self, jql: str) -> list[dict[str, Any]]:
        return [
            {
                "id": "10001",
                "key": "SEC-101",
                "fields": {
                    "summary": "Publicly exposed S3 bucket: demo-app-uploads",
                    "status": {"name": "In Progress"},
                    "labels": ["platform-exposure"],
                },
            },
            {
                "id": "10002",
                "key": "SEC-102",
                "fields": {
                    "summary": "Overly permissive IAM role: legacy-admin",
                    "status": {"name": "Done"},
                    "labels": ["platform-exposure"],
                },
            },
        ]

    def create_issue(self, project_key: str, summary: str, description: str, labels: list[str]) -> dict[str, Any]:
        key = f"{project_key}-{self._next_id}"
        self._next_id += 1
        issue = {
            "id": str(10000 + self._next_id),
            "key": key,
            "fields": {"summary": summary, "status": {"name": "Open"}, "labels": labels},
        }
        self.created_issues.append(issue)
        return issue

    def ping(self) -> bool:
        return not self._fail_ping
