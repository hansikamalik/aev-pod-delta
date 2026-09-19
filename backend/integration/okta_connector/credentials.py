"""
Credential configuration for the Okta connector.

Okta connectors authenticate with a single SSWS API token scoped to a
read-only admin role. In production the token and org URL are pulled from
the shared secrets vault (wired in Week 3) rather than from environment
variables directly -- `load_from_vault` is the seam where that happens.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class OktaCredentials(BaseModel):
    """Everything the connector needs to authenticate against an Okta org."""

    org_url: str = Field(..., description="e.g. https://your-org.okta.com")
    api_token: str = Field(..., description="SSWS API token, read-only admin scope")

    @field_validator("org_url")
    @classmethod
    def _normalize_org_url(cls, v: str) -> str:
        v = v.rstrip("/")
        if not v.startswith("https://"):
            raise ValueError("org_url must be an https:// URL")
        return v

    def auth_header(self) -> Dict[str, str]:
        return {
            "Authorization": f"SSWS {self.api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    @classmethod
    def load_from_vault(cls, vault_client: Any, secret_path: str = "connectors/okta") -> "OktaCredentials":
        """Fetch credentials from the shared secrets vault.

        `vault_client` is expected to expose `.get_secret(path) -> dict`,
        matching the interface the Integration squad's vault wiring exposes
        to all four Week 3 connectors.
        """
        secret = vault_client.get_secret(secret_path)
        return cls(org_url=secret["org_url"], api_token=secret["api_token"])

    @classmethod
    def load_from_env(cls) -> "OktaCredentials":
        """Fallback for local dev/testing without the vault wired up."""
        org_url = os.environ.get("OKTA_ORG_URL")
        api_token = os.environ.get("OKTA_API_TOKEN")
        if not org_url or not api_token:
            raise RuntimeError(
                "OKTA_ORG_URL and OKTA_API_TOKEN must be set when not loading from vault"
            )
        return cls(org_url=org_url, api_token=api_token)


def describe_credential_schema() -> Dict[str, Any]:
    """Machine-readable description used by describe_credentials()."""
    return {
        "type": "object",
        "required": ["org_url", "api_token"],
        "properties": {
            "org_url": {
                "type": "string",
                "format": "uri",
                "description": "Okta org base URL, e.g. https://your-org.okta.com",
            },
            "api_token": {
                "type": "string",
                "description": "SSWS API token with read-only admin scope",
                "secret": True,
            },
        },
    }
