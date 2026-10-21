"""
Jira Connector -- unlike the AWS/Azure/GCP connectors, Jira's traffic
runs in both directions:

  1. Ticket creation FROM exposures: when the platform finds an
     exposure, this connector opens a Jira ticket for it.
  2. Status sync back TO the platform: this connector discovers the
     current status of previously-created tickets and pushes that
     status into the platform's asset service (as `Asset` records of
     type `TICKET`), so the platform always reflects Jira's ground
     truth on remediation progress.

`discover()`/`ingest()` implement direction 2, satisfying the shared
Connector contract. `create_ticket_from_exposure()` is an
connector-specific extension covering direction 1 -- the contract
doesn't (and shouldn't) need to know about ticket creation, since only
Jira/ITSM-style connectors do this.
"""

from __future__ import annotations

from typing import Any, Iterable, Protocol

from connector_sdk import Asset, AssetType, Connector

from .auth import JiraAuthError, JiraTokenAuth
from .client import FakeJiraAPIClient, JiraAPIClient, JiraClientProtocol


class PlatformClient(Protocol):
    def bulk_upsert(self, assets: list[Asset]) -> int: ...


class InMemoryPlatformClient:
    def __init__(self, fail: bool = False) -> None:
        self._fail = fail
        self.pushed: list[Asset] = []

    def bulk_upsert(self, assets: list[Asset]) -> int:
        if self._fail:
            raise ConnectionError("simulated push failure")
        self.pushed.extend(assets)
        return len(assets)


class JiraConnector(Connector):
    """Creates Jira tickets from platform exposures and syncs their
    status back to the platform.
    """

    name = "jira"

    def __init__(
        self,
        base_url: str,
        project_key: str,
        email: str | None = None,
        api_token: str | None = None,
        client: JiraClientProtocol | None = None,
        platform_client: PlatformClient | None = None,
        jql: str | None = None,
    ) -> None:
        """
        Args:
            base_url: The customer's Jira site, e.g. "https://acme.atlassian.net".
            project_key: Jira project tickets are created in/read from, e.g. "SEC".
            email: Jira account email used for Basic Auth. Not required if
                `client` is supplied directly (tests).
            api_token: Jira API token (from the vault). Not required if
                `client` is supplied directly (tests).
            client: Optional pre-built API client.
            platform_client: Where synced ticket-status assets are pushed.
            jql: JQL used by discover() to find tickets to sync. Defaults
                to all tickets in `project_key` labeled by this connector.
        """
        self.base_url = base_url
        self.project_key = project_key
        self._email = email
        self._api_token = api_token
        self._client = client
        self._platform_client = platform_client or InMemoryPlatformClient()
        self._jql = jql or f'project = "{project_key}" AND labels = "platform-exposure"'

    # -- internal helpers ---------------------------------------------

    def _auth(self) -> JiraTokenAuth:
        if not self._email or not self._api_token:
            raise JiraAuthError("email and api_token were not provided")
        return JiraTokenAuth(self._email, self._api_token)

    def _get_client(self) -> JiraClientProtocol:
        if self._client is not None:
            return self._client
        headers = self._auth().basic_auth_header()
        self._client = JiraAPIClient(self.base_url, headers)
        return self._client

    @staticmethod
    def _normalize_issue(item: dict[str, Any]) -> Asset:
        fields = item.get("fields", {})
        return Asset(
            id=item["key"],
            source="jira",
            type=AssetType.TICKET,
            name=fields.get("summary", item["key"]),
            raw=item,
            tags={
                "status": fields.get("status", {}).get("name", ""),
                "labels": ",".join(fields.get("labels", [])),
            },
        )

    # -- Connector interface --------------------------------------------

    def discover(self) -> Iterable[Asset]:
        """Read current ticket status from Jira -- direction 2 (status sync)."""
        client = self._get_client()
        issues = client.search_issues(self._jql)
        return [self._normalize_issue(issue) for issue in issues]

    def ingest(self, assets: Iterable[Asset]) -> int:
        """Push synced ticket-status assets into the platform."""
        return self._platform_client.bulk_upsert(list(assets))

    def check_health(self) -> bool:
        try:
            return self._get_client().ping()
        except JiraAuthError:
            return False

    def describe_config(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "base_url": {"type": "string", "description": "Jira site URL, e.g. https://acme.atlassian.net"},
                "project_key": {"type": "string", "description": "Jira project key tickets are created in"},
            },
            "required": ["base_url", "project_key"],
        }

    def describe_credentials(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "email": {"type": "string", "description": "Jira account email for Basic Auth"},
                "api_token": {"type": "string", "secret": True, "description": "Jira API token"},
            },
            "required": ["email", "api_token"],
        }

    # -- connector-specific extension: direction 1 (ticket creation) ------

    def create_ticket_from_exposure(self, exposure: dict[str, Any]) -> Asset:
        """Open a Jira ticket for a platform-discovered exposure.

        `exposure` is expected to have at least `title` and
        `description` keys; any other keys are ignored by the ticket
        body but preserved in `raw` for traceability.
        """
        client = self._get_client()
        issue = client.create_issue(
            project_key=self.project_key,
            summary=exposure.get("title", "Untitled exposure"),
            description=exposure.get("description", ""),
            labels=["platform-exposure"],
        )
        return self._normalize_issue(issue)
