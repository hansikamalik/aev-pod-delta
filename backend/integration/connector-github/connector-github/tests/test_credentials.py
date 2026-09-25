import pytest

from github_connector.credentials import CredentialError, MockVaultClient, load_github_credentials

PATH = "secret/connectors/github/org-1"


def test_success_with_default_api_url():
    cfg = load_github_credentials(MockVaultClient({PATH: {"token": "t", "org": "acme"}}), "org-1")
    assert cfg.org == "acme" and cfg.api_url == "https://api.github.com"


def test_custom_enterprise_api_url():
    vault = MockVaultClient({PATH: {"token": "t", "org": "acme", "api_url": "https://ghe.acme.com/api/v3"}})
    assert load_github_credentials(vault, "org-1").api_url == "https://ghe.acme.com/api/v3"


def test_missing_path_raises_keyerror():
    with pytest.raises(KeyError):
        load_github_credentials(MockVaultClient({}), "org-1")


def test_missing_field_raises_credential_error():
    with pytest.raises(CredentialError):
        load_github_credentials(MockVaultClient({PATH: {"token": "t"}}), "org-1")


def test_non_https_api_url_rejected():
    vault = MockVaultClient({PATH: {"token": "t", "org": "a", "api_url": "http://ghe.acme.com"}})
    with pytest.raises(CredentialError):
        load_github_credentials(vault, "org-1")
