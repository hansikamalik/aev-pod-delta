import time
import pytest
import requests
import requests_mock
from src.auth import CyberArkAuthManager
from src.ccp import CyberArkCCPClient
from src.exceptions import CyberArkAuthError
import re


class TestCyberArkAuthManager:

    @pytest.fixture
    def auth_mgr(self):
        return CyberArkAuthManager("https://pvwa.domain.com", verify_ssl=False, timeout=5)

    def test_login_standard_success(self, auth_mgr, requests_mock):
        requests_mock.post(
            "https://pvwa.domain.com/PasswordVault/API/Auth/CyberArk/Logon",
            status_code=200,
            json="token_123"
        )
        token = auth_mgr.authenticate("Admin", "Pass123!", use_radius=False)
        assert token == "token_123"
        assert auth_mgr.get_auth_headers()["Authorization"] == "token_123"

    def test_login_radius_success(self, auth_mgr, requests_mock):
        requests_mock.post(
            "https://pvwa.domain.com/PasswordVault/API/Auth/Radius/Logon",
            status_code=200,
            text='"radius_token_999"'
        )
        token = auth_mgr.authenticate("Admin", "Pass123!", use_radius=True)
        assert token == "radius_token_999"

    def test_login_http_failure(self, auth_mgr, requests_mock):
        requests_mock.post(
            "https://pvwa.domain.com/PasswordVault/API/Auth/CyberArk/Logon",
            status_code=401,
            text="Unauthorized"
        )
        with pytest.raises(CyberArkAuthError, match="Auth failed"):
            auth_mgr.authenticate("Admin", "Wrong")

    def test_login_network_failure(self, auth_mgr, requests_mock):
        requests_mock.post(
            "https://pvwa.domain.com/PasswordVault/API/Auth/CyberArk/Logon",
            exc=requests.exceptions.ConnectionError("Offline")
        )
        with pytest.raises(CyberArkAuthError, match="Network error"):
            auth_mgr.authenticate("Admin", "Pass")

    def test_get_headers_expired_token(self, auth_mgr):
        auth_mgr._auth_token = "old_token"
        auth_mgr._token_expiry = time.time() - 10
        with pytest.raises(CyberArkAuthError, match="No active or valid authentication token"):
            auth_mgr.get_auth_headers()

    def test_logoff_success(self, auth_mgr, requests_mock):
        auth_mgr._auth_token = "active_token"
        auth_mgr._token_expiry = time.time() + 1000
        requests_mock.post(
            "https://pvwa.domain.com/PasswordVault/API/Auth/Logoff",
            status_code=200
        )
        assert auth_mgr.logoff() is True
        assert auth_mgr._auth_token is None

    def test_logoff_no_token(self, auth_mgr):
        assert auth_mgr.logoff() is True

    def test_logoff_exception(self, auth_mgr, requests_mock):
        auth_mgr._auth_token = "active_token"
        auth_mgr._token_expiry = time.time() + 1000
        requests_mock.post(
            "https://pvwa.domain.com/PasswordVault/API/Auth/Logoff",
            exc=requests.exceptions.ConnectionError("Disconnect error")
        )
        assert auth_mgr.logoff() is False


class TestCyberArkCCPClient:

    def test_ccp_get_credential_success(self, requests_mock):
        ccp = CyberArkCCPClient("https://ccp.domain.com/AIMWebService/api/Accounts", app_id="TestApp")
        requests_mock.get(
            "https://ccp.domain.com/AIMWebService/api/Accounts?AppID=TestApp&Safe=MySafe&Object=MyObject&Folder=Root",
            status_code=200,
            json={"Content": "Secret123!"}
        )
        res = ccp.get_credential("MySafe", "MyObject", folder="Root")
        assert res["Content"] == "Secret123!"

    def test_ccp_http_error(self, requests_mock):
        ccp = CyberArkCCPClient("https://ccp.domain.com/AIMWebService/api/Accounts", app_id="TestApp")
        # Match using regex or the module-level matcher
        requests_mock.get(re.compile(".*"), status_code=404, text="Not Found")
        
        with pytest.raises(CyberArkAuthError, match="CCP Secret retrieval failed"):
            ccp.get_credential("Safe", "Object")

    def test_ccp_network_error(self, requests_mock):
        ccp = CyberArkCCPClient("https://ccp.domain.com/AIMWebService/api/Accounts", app_id="TestApp")
        requests_mock.get(re.compile(".*"), exc=requests.exceptions.ConnectionError("Connection timed out"))
        
        with pytest.raises(CyberArkAuthError, match="Network error querying CCP"):
            ccp.get_credential("Safe", "Object")

 
