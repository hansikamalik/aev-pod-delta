"""
Google Workspace discovery: user inventory (Directory API) and admin audit
log activities (Reports API), both paginated.
"""

import logging
from typing import Any, Dict, List, Optional

from .auth import GoogleWorkspaceAuthenticator

logger = logging.getLogger("google_workspace_connector.discovery")

_DIRECTORY_USERS_PAGE_SIZE = 500
_REPORTS_ACTIVITIES_PAGE_SIZE = 1000
_REPORTS_APPLICATION_NAME = "admin"


class GoogleWorkspaceDiscovery:
    """Pulls raw records from the Admin SDK — no normalization happens here."""

    def __init__(self, authenticator: GoogleWorkspaceAuthenticator):
        self._authenticator = authenticator

    def discover(self) -> List[Dict[str, Any]]:
        """Enumerate the full Workspace user inventory via the Directory API."""
        service = self._authenticator.get_directory_service()
        users: List[Dict[str, Any]] = []
        page_token: Optional[str] = None

        while True:
            response = (
                service.users()
                .list(
                    customer="my_customer",
                    maxResults=_DIRECTORY_USERS_PAGE_SIZE,
                    pageToken=page_token,
                    orderBy="email",
                )
                .execute()
            )
            users.extend(response.get("users", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        logger.info("google_workspace_connector.discovery.users.count=%d", len(users))
        return users

    def ingest(self) -> List[Dict[str, Any]]:
        """Pull admin audit log activities via the Reports API."""
        service = self._authenticator.get_reports_service()
        activities: List[Dict[str, Any]] = []
        page_token: Optional[str] = None

        while True:
            response = (
                service.activities()
                .list(
                    userKey="all",
                    applicationName=_REPORTS_APPLICATION_NAME,
                    maxResults=_REPORTS_ACTIVITIES_PAGE_SIZE,
                    pageToken=page_token,
                )
                .execute()
            )
            activities.extend(response.get("items", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        logger.info(
            "google_workspace_connector.discovery.activities.count=%d", len(activities)
        )
        return activities
