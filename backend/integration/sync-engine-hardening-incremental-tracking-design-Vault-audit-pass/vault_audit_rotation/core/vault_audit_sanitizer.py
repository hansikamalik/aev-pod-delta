import re


class VaultAuditSanitizer:
    """Sanitizes sensitive tokens and credential data from log outputs

    to ensure Vault compliance before logs are persisted or ingested.
    """

    REDACTION_TAG = "[REDACTED_VAULT_AUDIT]"

    # Pattern to match token formats like 'token-v1-<hash>', 'token-v2-<hash>',
    # as well as key-value pairings such as active_token=<token> or previous_token=<token>
    TOKEN_PATTERN = re.compile(
        r"(?:active_token|previous_token)=([^\s.]+)|token-v\d+-[a-f0-9]+",
        re.IGNORECASE,
    )

    @classmethod
    def sanitize_log(cls, raw_log: str) -> str:
        """Replaces sensitive credential patterns in raw log strings

        with the required Vault audit redaction tag.
        """
        if not raw_log:
            return raw_log

        # Replace explicit token key=value assignments
        sanitized = re.sub(
            r"(active_token|previous_token)=token-v\d+-[a-f0-9]+",
            rf"\1={cls.REDACTION_TAG}",
            raw_log,
            flags=re.IGNORECASE,
        )

        # Fallback to replace any remaining standalone tokens matching token-vX-hash
        sanitized = re.sub(
            r"token-v\d+-[a-f0-9]+",
            cls.REDACTION_TAG,
            sanitized,
            flags=re.IGNORECASE,
        )

        return sanitized

    @classmethod
    def assert_vault_compliant(cls, sanitized_log: str) -> None:
        """Validates that no unredacted secret patterns remain in the log."""
        unredacted_match = re.search(r"token-v\d+-[a-f0-9]+", sanitized_log, re.IGNORECASE)
        if unredacted_match:
            raise AssertionError(
                f"Log compliance violation! Unredacted token found: {unredacted_match.group(0)}"
            )
