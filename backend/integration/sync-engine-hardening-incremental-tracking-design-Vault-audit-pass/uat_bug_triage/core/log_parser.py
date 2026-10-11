import re
from typing import Dict, Any, List

class LogParser:
    """Parses raw stdout/stderr from pytest, runbook_cli, and Vault rotation runs."""

    @staticmethod
    def parse_pytest_output(log_text: str) -> List[Dict[str, Any]]:
        failures = []
        
        # Match standard pytest failure blocks
        failure_blocks = re.findall(
            r"_{3,}\s+(.*?)\s+_{3,}\n(.*?)(?=\n_{3,}|\n={3,}|$)", 
            log_text, 
            re.DOTALL
        )

        for test_name, traceback in failure_blocks:
            connector_match = re.search(
                r"(AzureNormalizationPlatformPush|Azure_Normalization_Platform_Push|CyberArkAuthModule|cyberark_auth_module|CyberArkDiscoveryIntegration|cyberark-discovery-integration|ElasticConnector|elastic_connector|QRadarConnector|qradar_connector|SplunkConnector|splunk_connector|VaultEnterpriseFramework|vault-enterprise-framework)", 
                test_name,
                re.IGNORECASE
            )
            connector = connector_match.group(1) if connector_match else "Core Framework"
            
            failures.append({
                "source": "pytest",
                "test_case": test_name.strip(),
                "connector": connector,
                "traceback": traceback.strip(),
            })

        # Fallback: Capture VaultAuditViolationError or Rotation failure logs directly
        if not failures and ("VaultAuditViolationError" in log_text or "AssertionError" in log_text):
            connector_match = re.search(
                r"(AzureNormalizationPlatformPush|Azure_Normalization_Platform_Push|CyberArkAuthModule|cyberark_auth_module|CyberArkDiscoveryIntegration|cyberark-discovery-integration|ElasticConnector|elastic_connector|QRadarConnector|qradar_connector|SplunkConnector|splunk_connector|VaultEnterpriseFramework|vault-enterprise-framework)", 
                log_text,
                re.IGNORECASE
            )
            connector = connector_match.group(1) if connector_match else "VaultEnterpriseFramework"
            failures.append({
                "source": "vault_audit_rotation",
                "test_case": "Vault Audit & Credential Rotation Sweep",
                "connector": connector,
                "traceback": log_text.strip(),
            })

        return failures

    @staticmethod
    def parse_runbook_output(log_text: str) -> List[Dict[str, Any]]:
        runbook_failures = []
        connector_blocks = re.findall(
            r"---> Connector:\s+([\w-]+)\s+\[(.*?)\]\n(.*?)(?=(?:---> Connector:|$))", 
            log_text, 
            re.DOTALL
        )

        for connector, status, details in connector_blocks:
            if "FAILED" in status or "Vault Audit: False" in details or "Status: error" in details:
                runbook_failures.append({
                    "source": "runbook_cli",
                    "connector": connector.strip(),
                    "status": status.strip(),
                    "traceback": details.strip()
                })
        return runbook_failures
