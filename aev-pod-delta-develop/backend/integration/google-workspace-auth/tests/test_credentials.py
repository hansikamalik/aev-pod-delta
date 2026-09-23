import json

import pytest

from google_workspace_connector.credentials import (
    CredentialError,
    DEFAULT_SCOPES,
    MockVaultClient,
    load_google_workspace_credentials,
)

VALID_SA_JSON = {
    "type": "service_account",
    "client_email": "gws-connector@my-project.iam.gserviceaccount.com",
    "private_key": "-----BEGIN PRIVATE KEY-----\nFAKEKEY\n-----END PRIVATE KEY-----\n",
    "token_uri": "https://oauth2.googleapis.com/token",
}

PATH = "secret/connectors/google-workspace/org-123"


def test_loads_valid_credentials():
    vault = MockVaultClient(
        {
            PATH: {
                "service_account_json": json.dumps(VALID_SA_JSON),
                "delegated_admin_email": "admin@customer.com",
            }
        }
    )

    config = load_google_workspace_credentials(vault, org_id="org-123")

    assert config.org_id == "org-123"
    assert config.delegated_admin_email == "admin@customer.com"
    assert config.service_account_info["client_email"] == VALID_SA_JSON["client_email"]
    assert config.scopes == DEFAULT_SCOPES


def test_accepts_custom_scopes_as_json_list():
    vault = MockVaultClient(
        {
            PATH: {
                "service_account_json": json.dumps(VALID_SA_JSON),
                "delegated_admin_email": "admin@customer.com",
                "scopes": json.dumps(
                    ["https://www.googleapis.com/auth/admin.directory.user.readonly"]
                ),
            }
        }
    )

    config = load_google_workspace_credentials(vault, org_id="org-123")

    assert config.scopes == ["https://www.googleapis.com/auth/admin.directory.user.readonly"]


def test_accepts_custom_scopes_as_single_string():
    # Vault secrets are string key/value — a hand-written secret might not
    # JSON-encode a single scope.
    vault = MockVaultClient(
        {
            PATH: {
                "service_account_json": json.dumps(VALID_SA_JSON),
                "delegated_admin_email": "admin@customer.com",
                "scopes": "https://www.googleapis.com/auth/admin.directory.user.readonly",
            }
        }
    )

    config = load_google_workspace_credentials(vault, org_id="org-123")

    assert config.scopes == ["https://www.googleapis.com/auth/admin.directory.user.readonly"]


def test_missing_secret_raises_key_error():
    # MockVaultClient raises KeyError for an unknown path — same as the
    # SentinelOne connector's mock; the real Vault client's own not-found
    # behavior will differ and should be handled at the call site once swapped in.
    vault = MockVaultClient({})

    with pytest.raises(KeyError, match="No secret at Vault path"):
        load_google_workspace_credentials(vault, org_id="org-404")


def test_missing_service_account_json_raises():
    vault = MockVaultClient(
        {PATH: {"delegated_admin_email": "admin@customer.com"}}
    )

    with pytest.raises(CredentialError, match="missing required fields"):
        load_google_workspace_credentials(vault, org_id="org-123")


def test_missing_delegated_admin_email_raises():
    vault = MockVaultClient(
        {PATH: {"service_account_json": json.dumps(VALID_SA_JSON)}}
    )

    with pytest.raises(CredentialError, match="missing required fields"):
        load_google_workspace_credentials(vault, org_id="org-123")


def test_malformed_json_raises():
    vault = MockVaultClient(
        {
            PATH: {
                "service_account_json": "{not valid json",
                "delegated_admin_email": "admin@customer.com",
            }
        }
    )

    with pytest.raises(CredentialError, match="not valid JSON"):
        load_google_workspace_credentials(vault, org_id="org-123")


def test_missing_required_sa_fields_raises():
    incomplete_sa = {"type": "service_account", "client_email": "x@y.com"}  # no private_key/token_uri
    vault = MockVaultClient(
        {
            PATH: {
                "service_account_json": json.dumps(incomplete_sa),
                "delegated_admin_email": "admin@customer.com",
            }
        }
    )

    with pytest.raises(CredentialError, match="missing required field"):
        load_google_workspace_credentials(vault, org_id="org-123")


def test_repr_never_leaks_key_material():
    vault = MockVaultClient(
        {
            PATH: {
                "service_account_json": json.dumps(VALID_SA_JSON),
                "delegated_admin_email": "admin@customer.com",
            }
        }
    )

    config = load_google_workspace_credentials(vault, org_id="org-123")

    assert "FAKEKEY" not in repr(config)
    assert "redacted" in repr(config)
