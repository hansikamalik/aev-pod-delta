"""
Service-account authentication for the GCP connector.

The platform never stores a user's personal GCP login -- every GCP
connector instance authenticates as a dedicated, read-only service
account whose JSON key is supplied through the credentials schema
declared in `GCPConnector.describe_credentials()`.

This mirrors the AWS connector's IAM-role auth module and the Azure
connector's service-principal auth module: same shape, GCP-specific
mechanics.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

# Read-only scope: discovery/inventory only, never write access to the
# customer's GCP project.
READONLY_SCOPES = ["https://www.googleapis.com/auth/cloud-platform.read-only"]


class GCPAuthError(Exception):
    """Raised when a service-account key is missing, malformed, or rejected."""


@dataclass
class GCPServiceAccountAuth:
    """Loads a GCP service-account key and produces credentials for the
    API client.

    In production this wraps `google.oauth2.service_account.Credentials`.
    The `google-auth` import is deferred into `get_credentials()` so this
    module (and the rest of the connector) stays importable in
    environments -- like CI or this sandbox -- that don't have network
    access or the Google client libraries installed.
    """

    project_id: str
    service_account_key_json: str  # raw JSON string, as stored in the vault

    def _parsed_key(self) -> dict[str, Any]:
        try:
            key = json.loads(self.service_account_key_json)
        except json.JSONDecodeError as exc:
            raise GCPAuthError("service_account_key is not valid JSON") from exc

        required_fields = {"type", "project_id", "private_key", "client_email"}
        missing = required_fields - key.keys()
        if missing:
            raise GCPAuthError(f"service account key missing fields: {sorted(missing)}")
        if key["type"] != "service_account":
            raise GCPAuthError("credential JSON is not a service_account key")
        return key

    def get_credentials(self):
        """Return a `google.auth.credentials.Credentials` instance.

        Deferred import so the connector can be constructed, tested, and
        have its config/credential schemas inspected without the
        `google-auth` package being present (e.g. in the SDK squad's
        schema-generation helper, which only needs the class shape).
        """
        key = self._parsed_key()

        from google.oauth2 import service_account  # type: ignore

        return service_account.Credentials.from_service_account_info(
            key, scopes=READONLY_SCOPES
        )

    def validate(self) -> bool:
        """Cheap validation used by check_health(): confirms the key
        parses and belongs to the configured project, without making a
        network call.
        """
        key = self._parsed_key()
        return key.get("project_id") == self.project_id
