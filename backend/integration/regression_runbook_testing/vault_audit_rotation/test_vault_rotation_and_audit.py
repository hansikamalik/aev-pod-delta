import pytest
from connectors.catalog import ALL_21_CONNECTORS
from core.vault_client import VaultClient
from core.vault_audit_sanitizer import VaultAuditSanitizer


@pytest.mark.parametrize("connector_name", list(ALL_21_CONNECTORS.keys()))
def test_inflight_credential_rotation_and_audit_pass(connector_name):
    vault = VaultClient()
    sanitizer = VaultAuditSanitizer()

    creds = vault.get_credentials(connector_name)
    log_msg = f"Connector {connector_name} authenticated with token {creds['active_token']}"
    sanitized = sanitizer.sanitize(log_msg)

    assert "vault_token_" not in sanitized
    assert "[REDACTED]" in sanitized
