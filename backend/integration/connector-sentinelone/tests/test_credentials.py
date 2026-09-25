import pytest

from sentinelone_connector.credentials import (
    CredentialError,
    MockVaultClient,
    load_sentinelone_credentials,
)

PATH = "secret/connectors/sentinelone/org-1"


def test_load_credentials_success():
    vault = MockVaultClient({PATH: {"base_url": "https://acme.sentinelone.net", "api_token": "t"}})
    cfg = load_sentinelone_credentials(vault, "org-1")
    assert cfg.api_token == "t"
    assert cfg.base_url == "https://acme.sentinelone.net"


def test_missing_path_raises_keyerror():
    with pytest.raises(KeyError):
        load_sentinelone_credentials(MockVaultClient({}), "org-1")


def test_missing_field_raises_credential_error():
    vault = MockVaultClient({PATH: {"base_url": "https://acme.sentinelone.net"}})
    with pytest.raises(CredentialError):
        load_sentinelone_credentials(vault, "org-1")


def test_non_https_base_url_rejected():
    vault = MockVaultClient({PATH: {"base_url": "http://acme.sentinelone.net", "api_token": "t"}})
    with pytest.raises(CredentialError):
        load_sentinelone_credentials(vault, "org-1")
