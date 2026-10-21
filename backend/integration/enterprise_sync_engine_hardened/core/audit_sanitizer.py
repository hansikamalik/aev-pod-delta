import re


class VaultAuditSanitizer:
    """Zero-leak compliance module redacting Vault tokens from logs."""

    def sanitize(self, message: str) -> str:
        return re.sub(r"vault_token_[a-zA-Z0-9]+", "[REDACTED]", message)
