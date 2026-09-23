"""
Google Workspace authenticator: service account + domain-wide delegation.

Week 1 deliverable (Sep 4 - Sep 10), Pod Delta M4, Integration squad.
Owner: Bhawook. Built solo Thu-Fri after shadowing Bhavesh Kanekar on the
SentinelOne connector Mon-Wed.

Per the Pod Delta build guide:
  - FR-INT-012: Google Workspace auth = "Service account JWT; user
    inventory; audit log." The JWT here is what `service_account.Credentials
    .with_subject(...)` produces under the hood when you request a token for
    the impersonated (delegated) user — this is domain-wide delegation, not
    a per-user OAuth consent flow.
  - FR-INT-003: credentials come from Vault, as short-lived tokens with
    rotation — see credentials.py, which builds the config below.

Pattern mirrors SentinelOneAuthenticator: a small class that turns a
validated auth config into a usable, health-checkable session, exposing the
same shape (`validate()`) the rest of the connector pattern expects.
`AuthConfig` lives here (not in credentials.py) to match the SentinelOne
connector's layout, where credentials.py imports the config type from auth.py.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from google.auth.exceptions import GoogleAuthError, RefreshError
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

logger = logging.getLogger("google_workspace_connector.auth")

_DISCOVERY_SERVICE_NAME = "admin"
_DISCOVERY_SERVICE_VERSION = "directory_v1"


@dataclass(frozen=True)
class GoogleWorkspaceAuthConfig:
    """
    Everything the authenticator needs, sourced from Vault by credentials.py.

    service_account_info: the parsed service account JSON key (client_email,
        private_key, token_uri, etc.) — NEVER logged or serialized.
    delegated_admin_email: the Workspace super-admin (or a role account with
        the required Admin SDK privileges) the service account impersonates
        via domain-wide delegation.
    scopes: OAuth scopes requested for the impersonated session.
    org_id: internal org identifier, for logging/telemetry only.
    """

    service_account_info: Dict[str, Any]
    delegated_admin_email: str
    scopes: List[str]
    org_id: str

    def __repr__(self) -> str:  # never leak key material in logs/tracebacks
        return (
            f"GoogleWorkspaceAuthConfig(org_id={self.org_id!r}, "
            f"delegated_admin_email={self.delegated_admin_email!r}, "
            f"scopes={self.scopes!r}, service_account_info=<redacted>)"
        )

    __str__ = __repr__


class GoogleWorkspaceAuthError(RuntimeError):
    """Raised when authentication or token validation fails."""


class GoogleWorkspaceAuthenticator:
    """
    Builds delegated (impersonated) credentials from a service account key
    and validates them with a lightweight Admin SDK call.

    Usage mirrors SentinelOneAuthenticator:
        authenticator = GoogleWorkspaceAuthenticator(config)
        if authenticator.validate():
            service = authenticator.get_directory_service()
    """

    def __init__(self, config: GoogleWorkspaceAuthConfig):
        self._config = config
        self._credentials: Optional[service_account.Credentials] = None
        self._directory_service: Optional[Resource] = None

    def _build_credentials(self) -> service_account.Credentials:
        """
        Load the service account key and delegate (impersonate) the
        Workspace admin so the resulting credentials act as that user for
        Admin SDK calls. This is domain-wide delegation: the admin console
        must have already authorized this service account's client ID for
        the scopes in `self._config.scopes` — this code does not, and
        cannot, grant that itself.
        """
        base_credentials = service_account.Credentials.from_service_account_info(
            self._config.service_account_info,
            scopes=self._config.scopes,
        )
        return base_credentials.with_subject(self._config.delegated_admin_email)

    def authenticate(self) -> service_account.Credentials:
        """Build (or rebuild) delegated credentials and refresh the token."""
        credentials = self._build_credentials()
        try:
            credentials.refresh(Request())
        except RefreshError as exc:
            raise GoogleWorkspaceAuthError(
                f"Token refresh failed for org_id={self._config.org_id!r} "
                f"(delegated_admin_email={self._config.delegated_admin_email!r}): {exc}"
            ) from exc
        self._credentials = credentials
        return credentials

    def get_directory_service(self) -> Resource:
        """Return a cached Admin SDK Directory API client, authenticating if needed."""
        if self._credentials is None or not self._credentials.valid:
            self.authenticate()
        if self._directory_service is None:
            self._directory_service = build(
                _DISCOVERY_SERVICE_NAME,
                _DISCOVERY_SERVICE_VERSION,
                credentials=self._credentials,
                cache_discovery=False,
            )
        return self._directory_service

    def validate(self) -> bool:
        """
        Lightweight check that the delegated credentials actually work: one
        cheap Admin SDK call (fetch up to 1 user) rather than just checking
        that a token was issued. A token can be issued and still be useless
        if delegation wasn't authorized correctly in the admin console.
        """
        try:
            service = self.get_directory_service()
            service.users().list(customer="my_customer", maxResults=1).execute()
            logger.info(
                "google_workspace_connector.auth.validate.ok org_id=%s",
                self._config.org_id,
            )
            return True
        except (GoogleAuthError, HttpError, GoogleWorkspaceAuthError) as exc:
            logger.error(
                "google_workspace_connector.auth.validate.failed org_id=%s error=%s",
                self._config.org_id,
                exc,
            )
            return False
