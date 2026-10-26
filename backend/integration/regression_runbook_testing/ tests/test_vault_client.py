import pytest
from core.vault_client import VaultClient
from core.audit_sanitizer import VaultAuditSanitizer


def test_vault_credential_retrieval_and_rotation():
    vault = VaultClient()
    connector_id = "splunk_connector"

    # Initial fetch
    creds = vault.get_credentials(connector_id)
    assert creds is not None
    assert creds["version"] == 1
    assert "vault_token_" in creds["active_token"]

    # Mid-sync rotation
    rotated_creds = vault.rotate_credentials(connector_id)
    assert rotated_creds["version"] == 2
    assert rotated_creds["active_token"] != creds["active_token"]


def test_vault_audit_sanitization():
    sanitizer = VaultAuditSanitizer()
    token = "vault_token_9f8e7d6c5b4a"
    log_line = f"Client successfully authenticated using active token {token} for elastic_connector."

    sanitized = sanitizer.sanitize(log_line)

    assert token not in sanitized
    assert "[REDACTED]" in sanitized
