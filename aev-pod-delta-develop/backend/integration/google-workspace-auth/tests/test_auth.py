from unittest.mock import MagicMock, patch

import pytest
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from google_workspace_connector.auth import (
    GoogleWorkspaceAuthConfig,
    GoogleWorkspaceAuthenticator,
    GoogleWorkspaceAuthError,
)

CONFIG = GoogleWorkspaceAuthConfig(
    service_account_info={
        "type": "service_account",
        "client_email": "gws-connector@my-project.iam.gserviceaccount.com",
        "private_key": "fake",
        "token_uri": "https://oauth2.googleapis.com/token",
    },
    delegated_admin_email="admin@customer.com",
    scopes=["https://www.googleapis.com/auth/admin.directory.user.readonly"],
    org_id="org-123",
)


def _mock_delegated_credentials():
    """A credentials mock that supports .with_subject() and .refresh()."""
    delegated = MagicMock()
    delegated.valid = True
    base = MagicMock()
    base.with_subject.return_value = delegated
    return base, delegated


@patch("google_workspace_connector.auth.service_account.Credentials.from_service_account_info")
def test_build_credentials_delegates_to_admin(mock_from_info):
    base, delegated = _mock_delegated_credentials()
    mock_from_info.return_value = base

    authenticator = GoogleWorkspaceAuthenticator(CONFIG)
    creds = authenticator._build_credentials()

    mock_from_info.assert_called_once_with(
        CONFIG.service_account_info, scopes=CONFIG.scopes
    )
    base.with_subject.assert_called_once_with("admin@customer.com")
    assert creds is delegated


@patch("google_workspace_connector.auth.service_account.Credentials.from_service_account_info")
def test_authenticate_raises_on_refresh_failure(mock_from_info):
    base, delegated = _mock_delegated_credentials()
    delegated.refresh.side_effect = RefreshError("delegation not authorized")
    mock_from_info.return_value = base

    authenticator = GoogleWorkspaceAuthenticator(CONFIG)

    with pytest.raises(GoogleWorkspaceAuthError, match="Token refresh failed"):
        authenticator.authenticate()


@patch("google_workspace_connector.auth.build")
@patch("google_workspace_connector.auth.service_account.Credentials.from_service_account_info")
def test_validate_true_on_successful_api_call(mock_from_info, mock_build):
    base, delegated = _mock_delegated_credentials()
    mock_from_info.return_value = base

    mock_service = MagicMock()
    mock_service.users.return_value.list.return_value.execute.return_value = {"users": []}
    mock_build.return_value = mock_service

    authenticator = GoogleWorkspaceAuthenticator(CONFIG)
    assert authenticator.validate() is True

    mock_service.users.return_value.list.assert_called_once_with(
        customer="my_customer", maxResults=1
    )


@patch("google_workspace_connector.auth.build")
@patch("google_workspace_connector.auth.service_account.Credentials.from_service_account_info")
def test_validate_false_on_http_error(mock_from_info, mock_build):
    base, delegated = _mock_delegated_credentials()
    mock_from_info.return_value = base

    mock_service = MagicMock()
    mock_response = MagicMock(status=403)
    mock_service.users.return_value.list.return_value.execute.side_effect = HttpError(
        mock_response, b'{"error": "delegation_denied"}'
    )
    mock_build.return_value = mock_service

    authenticator = GoogleWorkspaceAuthenticator(CONFIG)
    assert authenticator.validate() is False


@patch("google_workspace_connector.auth.service_account.Credentials.from_service_account_info")
def test_validate_false_on_refresh_error(mock_from_info):
    base, delegated = _mock_delegated_credentials()
    delegated.refresh.side_effect = RefreshError("bad key")
    mock_from_info.return_value = base

    authenticator = GoogleWorkspaceAuthenticator(CONFIG)
    assert authenticator.validate() is False


@patch("google_workspace_connector.auth.build")
@patch("google_workspace_connector.auth.service_account.Credentials.from_service_account_info")
def test_get_directory_service_is_cached(mock_from_info, mock_build):
    base, delegated = _mock_delegated_credentials()
    mock_from_info.return_value = base
    mock_build.return_value = MagicMock()

    authenticator = GoogleWorkspaceAuthenticator(CONFIG)
    service_1 = authenticator.get_directory_service()
    service_2 = authenticator.get_directory_service()

    assert service_1 is service_2
    mock_build.assert_called_once()
