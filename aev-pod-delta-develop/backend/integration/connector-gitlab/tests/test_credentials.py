import pytest

from gitlab_connector.credentials import CredentialError, MockVaultClient, load_gitlab_credentials

PATH = "secret/connectors/gitlab/org-1"


def test_success_with_default_api_url():
    cfg = load_gitlab_credentials(MockVaultClient({PATH: {"token": "t", "group": "acme"}}), "org-1")
    assert cfg.group == "acme" and cfg.api_base == "https://gitlab.com/api/v4"


def test_numeric_group_id_is_accepted_and_stringified():
    cfg = load_gitlab_credentials(MockVaultClient({PATH: {"token": "t", "group": 1234}}), "org-1")
    assert cfg.group == "1234"


def test_custom_api_url():
    vault = MockVaultClient({PATH: {"token": "t", "group": "a", "api_url": "https://gitlab.acme.com"}})
    assert load_gitlab_credentials(vault, "org-1").api_base == "https://gitlab.acme.com/api/v4"


def test_missing_path_raises_keyerror():
    with pytest.raises(KeyError):
        load_gitlab_credentials(MockVaultClient({}), "org-1")


def test_missing_field_raises_credential_error():
    with pytest.raises(CredentialError):
        load_gitlab_credentials(MockVaultClient({PATH: {"token": "t"}}), "org-1")


def test_non_https_api_url_rejected():
    vault = MockVaultClient({PATH: {"token": "t", "group": "a", "api_url": "http://gitlab.acme.com"}})
    with pytest.raises(CredentialError):
        load_gitlab_credentials(vault, "org-1")
