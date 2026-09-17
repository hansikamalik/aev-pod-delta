import pytest
from src.discovery import LDAPScanner, CloudScanner, APIScanner

@pytest.fixture
def targets_config():
    return {
        "ldap": {
            "server": "ldap://dc1.company.local",
            "base_dn": "OU=Servers,DC=company,DC=local"
        },
        "cloud": {
            "aws_regions": ["us-east-1", "us-west-2"]
        },
        "api_inventory": {
            "url": "https://cmdb.company.local/api/v1/assets",
            "token_env_var": "TEST_TOKEN"
        }
    }

def test_ldap_scanner(targets_config):
    scanner = LDAPScanner(targets_config)
    results = scanner.scan()
    assert isinstance(results, list)
    assert len(results) == 3
    assert results[0]["raw_username"] == "adm_jdoe"

def test_cloud_scanner(targets_config):
    scanner = CloudScanner(targets_config)
    results = scanner.scan()
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["raw_username"] == "aws_admin_svc"

def test_api_scanner(targets_config, monkeypatch):
    monkeypatch.setenv("TEST_TOKEN", "mock_api_key_abc123")
    scanner = APIScanner(targets_config)
    results = scanner.scan()
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["raw_username"] == "db_admin_local"
