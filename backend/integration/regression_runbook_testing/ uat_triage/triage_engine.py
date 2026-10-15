import asyncio
import json
from typing import List, Dict, Any
from uat_triage.bug_classifier import BugClassifier
from connectors.catalog import ALL_21_CONNECTORS
from core.vault_client import VaultClient


class UATTriageEngine:
    """Automated UAT Bug Triage Engine for the 21 enterprise connectors."""

    def __init__(self, incoming_bugs: List[Dict[str, Any]]):
        self.incoming_bugs = incoming_bugs
        self.vault = VaultClient()

    async def process_triage(self) -> List[Dict[str, Any]]:
        triage_results = []
        for bug in self.incoming_bugs:
            connector = bug.get("connector", "unknown")
            error_msg = bug.get("error", "")
            affected_count = bug.get("affected_connectors_count", 1)

            # 1. Automated Severity Classification
            severity = BugClassifier.classify(error_msg, affected_count)
            
            # 2. Automated Isolation Check against Vault & Connector Catalog
            isolation_status = "PASSED"
            if connector in ALL_21_CONNECTORS:
                try:
                    creds = self.vault.get_credentials(connector)
                    if not creds or "active_token" not in creds:
                        isolation_status = "FAILED (Vault Credential Missing)"
                except Exception as e:
                    isolation_status = f"FAILED ({str(e)})"
            else:
                isolation_status = "WARNING (Connector not found in registry)"

            # 3. Compile Triage Record
            triage_results.append({
                "bug_id": bug.get("bug_id", "UAT-000"),
                "connector": connector,
                "severity": severity,
                "error_signature": error_msg,
                "isolation_check": isolation_status,
                "assigned_team": self._assign_owner(connector)
            })

        return triage_results

    def _assign_owner(self, connector: str) -> str:
        """Routes bug tickets based on the connector ownership matrix."""
        connector_lower = connector.lower()
        if any(k in connector_lower for k in ["splunk", "qradar", "elastic", "chronicle", "sentinel"]):
            return "SIEM / Log Team (@sec-siem-oncall)"
        elif any(k in connector_lower for k in ["aws", "azure", "okta", "ping"]):
            return "Cloud & Identity Team (@sec-cloud-idp)"
        elif any(k in connector_lower for k in ["crowdstrike", "paloalto", "qualys", "tenable"]):
            return "SecOps & Endpoint Team (@sec-endpoint-ops)"
        elif any(k in connector_lower for k in ["cyberark", "vault"]):
            return "Vault & Auth Core Team (@sec-vault-core)"
        return "ITSM & Alerting Team (@sec-itsm-ops)"


if __name__ == "__main__":
    async def main():
        # Load sample incoming bug reports
        template_path = "uat_triage/templates/bug_report_template.json"
        try:
            with open(template_path, "r") as f:
                bugs = json.load(f)
        except FileNotFoundError:
            bugs = [
                {
                    "bug_id": "UAT-101",
                    "connector": "splunk_connector",
                    "error": "Checkpoint synchronization timeout after 30s",
                    "affected_connectors_count": 1
                }
            ]

        engine = UATTriageEngine(bugs)
        results = await engine.process_triage()
        print("=== UAT BUG TRIAGE REPORT ===")
        print(json.dumps(results, indent=2))

    asyncio.run(main())
