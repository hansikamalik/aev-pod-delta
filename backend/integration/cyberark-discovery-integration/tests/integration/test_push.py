import pytest
from src.push.cyberark_client import CyberArkClient
from src.push.onboarder import Onboarder

@pytest.fixture
def cybr_config():
    return {
        "cyberark": {
            "pvwa_url": "https://pvwa.company.local/PasswordVault",
            "verify_ssl": False,
            "timeout_seconds": 5
        },
        "api_endpoints": {
            "auth": "/api/auth/Logon",
            "discovered_accounts": "/api/DiscoveredAccounts",
            "verify": "/api/Accounts/{id}/Verify"
        }
    }

def test_full_push_flow(cybr_config):
    client = CyberArkClient(cybr_config)
    token = client.login("VaultAdmin", "password")
    assert token == "mock_cyberark_token_12345"

    onboarder = Onboarder(client)
    mock_accounts = [
        {"userName": "adm_jdoe", "address": "srv-db01.local", "platformId": "WinServerLocal"},
        {"userName": "root", "address": "app-linux01.local", "platformId": "UnixSSH"}
    ]
    summary = onboarder.bulk_push(mock_accounts)
    assert summary["success"] == 2
    assert summary["failed"] == 0

def test_client_verify_account(cybr_config):
    client = CyberArkClient(cybr_config)
    client.login("VaultAdmin", "password")
    assert client.verify_account("account_123") is True

def test_onboarder_failure_path(cybr_config, monkeypatch):
    client = CyberArkClient(cybr_config)
    client.login("VaultAdmin", "password")
    
    # Simulate API failure during push
    monkeypatch.setattr(client, "push_discovered_account", lambda acc: False)
    
    onboarder = Onboarder(client)
    mock_accounts = [{"userName": "bad_user", "address": "srv01.local"}]
    summary = onboarder.bulk_push(mock_accounts)
    
    assert summary["success"] == 0
    assert summary["failed"] == 1

def test_real_http_calls_with_mock(requests_mock):
    real_config = {
        "cyberark": {
            "pvwa_url": "https://real-pvwa.company.local/PasswordVault",
            "verify_ssl": False,
            "timeout_seconds": 5
        },
        "api_endpoints": {
            "auth": "/api/auth/Logon",
            "discovered_accounts": "/api/DiscoveredAccounts",
            "verify": "/api/Accounts/{id}/Verify"
        }
    }
    
    # Mock PVWA API REST Endpoints
    requests_mock.post("https://real-pvwa.company.local/PasswordVault/api/auth/Logon", text='"token_abc_987"', status_code=200)
    requests_mock.post("https://real-pvwa.company.local/PasswordVault/api/DiscoveredAccounts", status_code=201)
    requests_mock.post("https://real-pvwa.company.local/PasswordVault/api/Accounts/acc_1/Verify", status_code=200)

    client = CyberArkClient(real_config)
    token = client.login("real_admin", "real_password")
    assert token == "token_abc_987"

    account = {"userName": "user1", "address": "10.0.0.1", "platformId": "WinServerLocal"}
    assert client.push_discovered_account(account) is True
    assert client.verify_account("acc_1") is True
