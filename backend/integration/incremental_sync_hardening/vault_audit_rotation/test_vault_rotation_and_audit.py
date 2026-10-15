import pytest
from connectors.catalog import ALL_21_CONNECTORS
from core.vault_client import VaultClient
from core.audit_sanitizer import VaultAuditSanitizer


@pytest.mark.parametrize("connector_name", list(ALL_21_CONNECTORS.keys()))
def test_inflight_credential_rotation_and_audit_pass(connector_name):
    vault = VaultClient()
    sanitizer = VaultAuditSanitizer()
    
    creds = vault.get_credentials(connector_name)
    token_v1 = creds["active_token"]
    
    log_line_v1 = f"Connector {connector_name} active session using token {token_v1}"
    sanitized_v1 = sanitizer.sanitize(log_line_v1)
    assert token_v1 not in sanitized_v1
    assert "[REDACTED]" in sanitized_v1

    rotated = vault.rotate_credentials(connector_name)
    token_v2 = rotated["active_token"]
    assert token_v2 != token_v1

    log_line_v2 = f"Connector {connector_name} rotated session using token {token_v2}"
    sanitized_v2 = sanitizer.sanitize(log_line_v2)
    assert token_v2 not in sanitized_v2
    assert "[REDACTED]" in sanitized_v2
