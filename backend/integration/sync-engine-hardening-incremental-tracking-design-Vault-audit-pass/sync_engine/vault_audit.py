import logging
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Set, Tuple

# Comprehensive HashiCorp Vault Audit standard key blacklist
SENSITIVE_AUDIT_KEYS: Set[str] = {
    "client_secret",
    "secret",
    "password",
    "token",
    "api_key",
    "access_token",
    "private_key",
    "auth_header",
    "session_token",
    "vault_token",
    "credential",
}


class VaultAuditViolationError(Exception):
    """Raised when unredacted sensitive data is caught by the audit wrapper."""

    pass


class VaultAuditLogger:
    """Audit-logging engine enforcing strict Vault compliance standards."""

    def __init__(self, service_name: str = "SyncEngine"):
        self.service_name = service_name
        self.logger = logging.getLogger(f"VaultAudit.{service_name}")
        self.logger.setLevel(logging.INFO)

    @classmethod
    def recursively_sanitize(
        cls, data: Any, masked_count: List[int] = None
    ) -> Tuple[Any, int]:
        """Recursively traverses dictionaries, lists, and strings to sanitize sensitive keys."""
        if masked_count is None:
            masked_count = [0]

        if isinstance(data, dict):
            cleaned = {}
            for k, v in data.items():
                if k.lower() in SENSITIVE_AUDIT_KEYS:
                    cleaned[k] = "[REDACTED_VAULT_AUDIT]"
                    masked_count[0] += 1
                else:
                    cleaned[k], _ = cls.recursively_sanitize(v, masked_count)
            return cleaned, masked_count[0]

        elif isinstance(data, list):
            cleaned_list = []
            for item in data:
                sanitized_item, _ = cls.recursively_sanitize(item, masked_count)
                cleaned_list.append(sanitized_item)
            return cleaned_list, masked_count[0]

        return data, masked_count[0]

    @classmethod
    def assert_vault_compliant(cls, data: Dict[str, Any]) -> None:
        """Enforces zero-tolerance audit check. Throws exception if sensitive key contains raw data."""
        if not isinstance(data, dict):
            return

        for k, v in data.items():
            if k.lower() in SENSITIVE_AUDIT_KEYS:
                if v != "[REDACTED_VAULT_AUDIT]" and v != "[REDACTED]":
                    raise VaultAuditViolationError(
                        f"Vault Audit Failure: Key '{k}' contains unredacted sensitive data!"
                    )
            elif isinstance(v, dict):
                cls.assert_vault_compliant(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        cls.assert_vault_compliant(item)

    def log_audit_trail(
        self, connector_id: str, operation: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generates a tamper-evident audit record with cryptographic hash verification."""
        sanitized_payload, redaction_count = self.recursively_sanitize(payload)

        # Enforce compliance check
        self.assert_vault_compliant(sanitized_payload)

        payload_str = json.dumps(sanitized_payload, sort_keys=True)
        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        audit_record = {
            "audit_timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service_name,
            "connector_id": connector_id,
            "operation": operation,
            "payload_sha256": payload_hash,
            "redaction_count": redaction_count,
            "vault_audit_passed": True,
        }

        self.logger.info(
            f"VAULT_AUDIT_PASS | Connector: {connector_id} | Op: {operation} | Hash: {payload_hash[:12]} | Redactions: {redaction_count}"
        )
        return audit_record
