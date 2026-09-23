import logging
import re


class CredentialRedactingFormatter(logging.Formatter):
    """Custom log formatter that masks sensitive authentication details."""

    PATTERNS = [
        (r'("password"\s*:\s*")[^"]+(")', r'\1[REDACTED]\2'),
        (r'("client_secret"\s*:\s*")[^"]+(")', r'\1[REDACTED]\2'),
        (r'(Authorization\s*:\s*")[^"]+(")', r'\1[REDACTED]\2'),
        (r'(Bearer\s+)[A-Za-z0-9\-\._~\+\/]+=*', r'\1[REDACTED]'),
    ]

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        for pattern, replacement in self.PATTERNS:
            formatted = re.sub(pattern, replacement, formatted, flags=re.IGNORECASE)
        return formatted
