from __future__ import annotations

from typing import Any

from googleapiclient.discovery import build


class GoogleWorkspaceClients:
    """Create Admin SDK clients using credentials from the auth module."""

    def __init__(self, credentials: Any):
        self._credentials = credentials
        self.directory = build(
            "admin",
            "directory_v1",
            credentials=credentials,
            cache_discovery=False,
        )
        self.reports = build(
            "admin",
            "reports_v1",
            credentials=credentials,
            cache_discovery=False,
        )
