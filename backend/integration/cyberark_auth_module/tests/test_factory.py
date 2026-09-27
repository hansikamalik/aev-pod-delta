import logging
from unittest.mock import patch
import pytest
import requests
import requests_mock
from src.factory import CyberArkAuthFactory
from src.middleware import with_auto_refresh
from src.utils import CredentialRedactingFormatter
from src.exceptions import CyberArkAuthError


class DummyOAuthAPIClient:
    """Mock service using OAuth client with middleware."""
    def __init__(self, auth_client):
        self.auth_client = auth_client
        self.call_count = 0

    @with_auto_refresh(max_retries=1)
    def call_api(self):
        self.call_count += 1
        if self.call_count == 1:
            resp = requests.Response()
            resp.status_code = 401
            raise requests.HTTPError("401 Unauthorized", response=resp)
        return {"status": "ok"}


class DummySessionAPIClient:
    """Mock service using Interactive Auth client with middleware."""
    def __init__(self, auth_client):
        self.auth_client = auth_client
        self.call_count = 0

    @with_auto_refresh(max_retries=1)
    def call_api(self):
        self.call_count += 1
        if self.call_count == 1:
            resp = requests.Response()
            resp.status_code = 401
            raise requests.HTTPError("401 Unauthorized", response=resp)
        return {"status": "ok"}


class TestFactoryMiddlewareUtils:

    # --- Factory Tests --- #

    def test_factory_create_interactive(self, requests_mock):
        requests_mock.post("https://pvwa.domain.com/PasswordVault/API/Auth/CyberArk/Logon", status_code=200, json="t_123")
        cfg = {"auth_type": "interactive", "pas_url": "https://pvwa.domain.com", "username": "Admin", "password": "Pass"}
        client = CyberArkAuthFactory.create_client(cfg)
        assert client.get_auth_headers()["Authorization"] == "t_123"

    def test_factory_create_interactive_missing_pas_url(self):
        with pytest.raises(CyberArkAuthError, match="Missing parameter 'pas_url'"):
            CyberArkAuthFactory.create_client({"auth_type": "interactive"})

    def test_factory_create_ccp(self):
        cfg = {"auth_type": "ccp", "ccp_url": "https://ccp.domain.com/AIMWebService/api/Accounts", "app_id": "TestApp"}
        client = CyberArkAuthFactory.create_client(cfg)
        assert client.app_id == "TestApp"

    def test_factory_create_ccp_missing_params(self):
        with pytest.raises(CyberArkAuthError, match="Missing required parameters"):
            CyberArkAuthFactory.create_client({"auth_type": "ccp", "ccp_url": "https://ccp.domain.com"})

    def test_factory_create_oauth2_missing_params(self):
        with pytest.raises(CyberArkAuthError, match="Missing required parameters"):
            CyberArkAuthFactory.create_client({"auth_type": "oauth2", "tenant_url": "https://tenant.cloud"})

    def test_factory_invalid_type(self):
        with pytest.raises(CyberArkAuthError, match="Unsupported 'auth_type'"):
            CyberArkAuthFactory.create_client({"auth_type": "unknown"})

    # --- Middleware Tests --- #

    def test_auto_refresh_middleware_oauth(self, requests_mock):
        requests_mock.post(
            "https://tenant.id.cyberark.cloud/oauth2/token",
            status_code=200,
            json={"access_token": "token_new", "expires_in": 3600}
        )
        cfg = {
            "auth_type": "oauth2",
            "tenant_url": "https://tenant.id.cyberark.cloud",
            "client_id": "id",
            "client_secret": "sec"
        }
        auth_client = CyberArkAuthFactory.create_client(cfg)

        api_client = DummyOAuthAPIClient(auth_client)
        res = api_client.call_api()
        assert res["status"] == "ok"
        assert api_client.call_count == 2

    def test_auto_refresh_middleware_interactive_success(self, requests_mock):
        requests_mock.post(
            "https://pvwa.domain.com/PasswordVault/API/Auth/CyberArk/Logon",
            status_code=200,
            json="refreshed_token_456"
        )
        cfg = {
            "auth_type": "interactive",
            "pas_url": "https://pvwa.domain.com",
            "username": "Admin",
            "password": "Password123!"
        }
        auth_client = CyberArkAuthFactory.create_client(cfg)

        api_client = DummySessionAPIClient(auth_client)
        res = api_client.call_api()
        assert res["status"] == "ok"
        assert api_client.call_count == 2

    def test_auto_refresh_middleware_interactive_no_stored_creds(self):
        cfg = {"auth_type": "interactive", "pas_url": "https://pvwa.domain.com"}
        auth_client = CyberArkAuthFactory.create_client(cfg)

        api_client = DummySessionAPIClient(auth_client)
        with pytest.raises(CyberArkAuthError, match="No active or valid authentication token available"):
            api_client.call_api()

    def test_auto_refresh_non_401_exception(self):
        class FaultyClient:
            def __init__(self):
                self.auth_client = self

            @with_auto_refresh(max_retries=1)
            def raise_500(self):
                resp = requests.Response()
                resp.status_code = 500
                raise requests.HTTPError("500 Internal Error", response=resp)

        faulty = FaultyClient()
        with pytest.raises(requests.HTTPError):
            faulty.raise_500()

    def test_auto_refresh_exhausts_retries(self, requests_mock):
        requests_mock.post(
            "https://tenant.id.cyberark.cloud/oauth2/token",
            [
                {"json": {"access_token": "init_token", "expires_in": 3600}, "status_code": 200},
                {"json": {"access_token": "retry_token", "expires_in": 3600}, "status_code": 200}
            ]
        )
        cfg = {
            "auth_type": "oauth2",
            "tenant_url": "https://tenant.id.cyberark.cloud",
            "client_id": "id",
            "client_secret": "sec"
        }
        auth_client = CyberArkAuthFactory.create_client(cfg)

        class AlwaysFailing401Client:
            def __init__(self, auth_client):
                self.auth_client = auth_client

            @with_auto_refresh(max_retries=1)
            def call_api(self):
                resp = requests.Response()
                resp.status_code = 401
                raise requests.HTTPError("401 Unauthorized", response=resp)

        api_client = AlwaysFailing401Client(auth_client)

        with pytest.raises(requests.HTTPError):
            api_client.call_api()

    def test_auto_refresh_reauth_failure_raises_cyberark_error(self, requests_mock):
        requests_mock.post(
            "https://tenant.id.cyberark.cloud/oauth2/token",
            status_code=200,
            json={"access_token": "init_token", "expires_in": 3600}
        )
        cfg = {
            "auth_type": "oauth2",
            "tenant_url": "https://tenant.id.cyberark.cloud",
            "client_id": "id",
            "client_secret": "sec"
        }
        auth_client = CyberArkAuthFactory.create_client(cfg)
        api_client = DummyOAuthAPIClient(auth_client)

        with patch.object(auth_client, "get_token", side_effect=RuntimeError("Unexpected re-auth crash")):
            with pytest.raises(CyberArkAuthError, match="Auto-refresh failed: Unexpected re-auth crash"):
                api_client.call_api()

    def test_auto_refresh_middleware_login_method(self):
        class MockLoginAuthClient:
            def __init__(self):
                self.login_called = False

            def login(self):
                self.login_called = True

        class DummyLoginAPIClient:
            def __init__(self, auth_client):
                self.auth_client = auth_client
                self.call_count = 0

            @with_auto_refresh(max_retries=1)
            def call_api(self):
                self.call_count += 1
                if self.call_count == 1:
                    resp = requests.Response()
                    resp.status_code = 401
                    raise requests.HTTPError("401 Unauthorized", response=resp)
                return {"status": "ok"}

        auth_client = MockLoginAuthClient()
        api_client = DummyLoginAPIClient(auth_client)
        res = api_client.call_api()

        assert res["status"] == "ok"
        assert auth_client.login_called is True

    def test_auto_refresh_middleware_no_supported_auth_method(self):
        class DummyUnsupportedClient:
            def __init__(self):
                self.auth_client = object()

            @with_auto_refresh(max_retries=1)
            def call_api(self):
                resp = requests.Response()
                resp.status_code = 401
                raise requests.HTTPError("401 Unauthorized", response=resp)

        api_client = DummyUnsupportedClient()
        with pytest.raises(CyberArkAuthError, match="Auth client has no supported re-authentication method"):
            api_client.call_api()

    # --- Utils / Log Formatter Tests --- #

    def test_credential_redacting_formatter(self):
        formatter = CredentialRedactingFormatter("%(message)s")
        record = logging.LogRecord(
            "test",
            logging.INFO,
            "",
            0,
            'Posting {"password": "SuperSecretPassword123!", "client_secret": "Secret456"} Authorization: "Bearer token_789"',
            (),
            None
        )
        output = formatter.format(record)
        assert "[REDACTED]" in output
        assert "SuperSecretPassword123!" not in output
        assert "Secret456" not in output
        assert "token_789" not in output
