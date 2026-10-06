import pytest
from vault_audit_rotation.core.vault_audit_sanitizer import VaultAuditSanitizer
from vault_audit_rotation.core.credential_rotator import CredentialRotator

CONNECTORS = [
    "Azure_Normalization_Platform_Push",
    "cyberark_auth_module",
    "cyberark-discovery-integration",
    "elastic_connector",
    "qradar_connector",
    "splunk_connector",
    "vault-enterprise-framework"
]

@pytest.fixture(scope="module")
def rotation_engine():
    rotator = CredentialRotator()
    for conn in CONNECTORS:
        rotator.seed_initial_credentials(conn)
    return rotator

@pytest.mark.parametrize("connector", CONNECTORS)
def test_inflight_credential_rotation_and_audit_pass(rotation_engine, connector):
    # Step 1: Verify Initial Credentials Active
    initial_creds = rotation_engine.get_active_credentials(connector)
    assert initial_creds["version"] == 1

    # Step 2: Trigger Mid-Flight Secret Rotation
    rotated_creds = rotation_engine.rotate_credentials(connector)
    assert rotated_creds["version"] == 2
    assert rotated_creds["active_token"] != initial_creds["active_token"]

    # Step 3: Simulate Connector Sync Operation Logging
    raw_execution_log = (
        f"INFO [{connector}] Sync cycle started with active_token={rotated_creds['active_token']} "
        f"and fallback previous_token={rotated_creds['previous_token']}. Connection established."
    )

    # Step 4: Enforce Vault Audit Redaction
    sanitized_log = VaultAuditSanitizer.sanitize_log(raw_execution_log)
    
    # Step 5: Validate Log Compliance
    VaultAuditSanitizer.assert_vault_compliant(sanitized_log)
    assert VaultAuditSanitizer.REDACTION_TAG in sanitized_log
    assert rotated_creds["active_token"] not in sanitized_log
