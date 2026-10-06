import sys
from pathlib import Path

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

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

def run_rotation_sweep():
    print("======================================================================")
    print("   VAULT AUDIT & CREDENTIAL ROTATION SUITE FOR CONNECTORS   ")
    print("======================================================================\n")

    rotator = CredentialRotator()
    passed = 0

    for idx, conn in enumerate(CONNECTORS, 1):
        print(f"[{idx}/7] Processing Connector: {conn}")
        rotator.seed_initial_credentials(conn)
        
        # Trigger Rotation
        new_secrets = rotator.rotate_credentials(conn)
        print(f"  ├─ Vault Secret Rotated -> New Version: v{new_secrets['version']}")

        # Simulate Sync Log
        raw_log = f"LOG [{conn}]: Authenticated using api_key={new_secrets['active_token']}."
        sanitized = VaultAuditSanitizer.sanitize_log(raw_log)

        try:
            VaultAuditSanitizer.assert_vault_compliant(sanitized)
            print(f"  └─ STATUS: [VAULT AUDIT PASSED] Credentials rotated & sanitized properly.\n")
            passed += 1
        except AssertionError as e:
            print(f"  └─ STATUS: [VAULT AUDIT FAILED] {e}\n")

    print("======================================================================")
    print(f"ROTATION & AUDIT SWEEP COMPLETE: {passed}/{len(CONNECTORS)} Connectors Passed")
    print("======================================================================")

    if passed != len(CONNECTORS):
        sys.exit(1)

if __name__ == "__main__":
    run_rotation_sweep()
