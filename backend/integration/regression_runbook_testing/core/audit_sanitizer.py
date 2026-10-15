import re


class VaultAuditSanitizer:
    """Ensures zero-leak compliance by redacting Vault tokens from audit logs."""

    def sanitize(self, message: str) -> str:
        # Regex pattern matching vault token prefixes
        return re.sub(r"vault_token_[a-zA-Z0-9]+", "[REDACTED]", message)
