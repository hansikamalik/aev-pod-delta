import pytest
import requests
import requests_mock
from src.oauth import CyberArkIdentityOAuthClient
from src.exceptions import CyberArkAuthError


class TestCyberArkIdentityOAuthClient:

    @pytest.fixture
    def oauth_client(self):
        return CyberArkIdentityOAuthClient(
            tenant_url="https://tenant.id.cyberark.cloud",
            client_id="client_id",
            client_secret="secret",
            verify_ssl=False
        )

    def test_get_token_success(self, oauth_client, requests_mock):
        requests_mock.post(
            "https://tenant.id.cyberark.cloud/oauth2/token",
            status_code=200,
            json={"access_token": "token_abc", "token_type": "Bearer", "expires_in": 3600}
        )
        token = oauth_client.get_token(scope="read")
        assert token == "token_abc"
        assert oauth_client.get_auth_headers(scope="read")["Authorization"] == "Bearer token_abc"

    def test_get_token_caching(self, oauth_client, requests_mock):
        mock_post = requests_mock.post(
            "https://tenant.id.cyberark.cloud/oauth2/token",
            status_code=200,
            json={"access_token": "token_abc", "expires_in": 3600}
        )
        oauth_client.get_token()
        oauth_client.get_token()
        assert mock_post.call_count == 1

    def test_get_token_missing_token_field(self, oauth_client, requests_mock):
        requests_mock.post(
            "https://tenant.id.cyberark.cloud/oauth2/token",
            status_code=200,
            json={"expires_in": 3600}
        )
        with pytest.raises(CyberArkAuthError, match="did not contain an 'access_token'"):
            oauth_client.get_token()

    def test_get_token_http_failure(self, oauth_client, requests_mock):
        requests_mock.post(
            "https://tenant.id.cyberark.cloud/oauth2/token",
            status_code=400,
            text="Bad Request"
        )
        with pytest.raises(CyberArkAuthError, match="OAuth2 Auth failed"):
            oauth_client.get_token()

    def test_get_token_network_failure(self, oauth_client, requests_mock):
        requests_mock.post(
            "https://tenant.id.cyberark.cloud/oauth2/token",
            exc=requests.exceptions.ConnectionError("Unreachable")
        )
        with pytest.raises(CyberArkAuthError, match="Network error during OAuth2 authentication"):
            oauth_client.get_token()
