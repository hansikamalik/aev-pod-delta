import pytest

from sentinel_connector.credentials import (
    CredentialError,
    MockVaultClient,
    load_sentinel_credentials,
)


def full_secret():
    return {
        "tenant_id": "t1",
        "client_id": "c1",
        "client_secret": "s1",
        "subscription_id": "sub1",
        "resource_group": "rg1",
        "workspace_name": "ws1",
    }


def test_load_credentials_success():
    vault = MockVaultClient({"secret/connectors/microsoft-sentinel/org-1": full_secret()})
    config = load_sentinel_credentials(vault, "org-1")
    assert config.tenant_id == "t1"
    assert config.workspace_name == "ws1"


def test_load_credentials_missing_path_raises_keyerror():
    vault = MockVaultClient({})
    with pytest.raises(KeyError):
        load_sentinel_credentials(vault, "org-missing")


def test_load_credentials_missing_field_raises_credential_error():
    secret = full_secret()
    del secret["client_secret"]
    vault = MockVaultClient({"secret/connectors/microsoft-sentinel/org-2": secret})
    with pytest.raises(CredentialError):
        load_sentinel_credentials(vault, "org-2")
