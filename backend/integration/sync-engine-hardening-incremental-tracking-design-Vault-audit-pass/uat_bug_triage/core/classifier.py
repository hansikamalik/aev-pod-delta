from typing import Dict, Any

class SeverityClassifier:
    """Classifies bug severity based on Vault Audit rules and execution impact."""

    @staticmethod
    def classify_defect(failure: Dict[str, Any], vault_check: Dict[str, Any]) -> Dict[str, str]:
        # Rule 1: Secret Leak / Vault Audit Violation is ALWAYS P0 Blocker
        if vault_check["has_leak"] or "VaultAuditViolationError" in failure.get("traceback", ""):
            return {
                "severity": "P0 - Blocker",
                "priority": "Immediate (24h SLA)",
                "category": "Vault Audit & Security Violation",
                "summary": f"Unredacted sensitive token or Vault Audit Failure detected in {failure.get('connector')}"
            }

        # Rule 2: Complete Operation Failure during Sync/Ingest is P1 Critical
        traceback = failure.get("traceback", "")
        if "sync" in traceback.lower() or "ingest" in traceback.lower() or "AssertionError" in traceback:
            return {
                "severity": "P1 - Critical",
                "priority": "High (Current Sprint)",
                "category": "Data Lifecycle / Normalization Failure",
                "summary": f"Lifecycle operation failed for connector {failure.get('connector')}"
            }

        # Default Fallback: Operational Issue
        return {
            "severity": "P2 - Major",
            "priority": "Medium",
            "category": "Health / Discovery Edge Case",
            "summary": f"Regression failure in connector {failure.get('connector')}"
        }
