import re
from fastapi import HTTPException

# ── 1. BLOCKED TOPICS / MALICIOUS PROMPTS ──────────────────────────
BLOCKED_KEYWORDS = [
    "jailbreak",
    "bypass security",
    "ignore previous instructions",
    "ignore all instructions",
    "system prompt leak",
    "sql injection",
    "malware script",
    "exploit vulnerability",
]


def check_blocked_topics(text: str) -> None:
    """
    Scans the prompt for security-violating or malicious keywords.
    Raises HTTP 400 Bad Request if a blocked topic is detected.
    """
    text_lower = text.lower()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in text_lower:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Guardrail violation",
                    "message": f"Query rejected. Restricted keyword detected: '{keyword}'.",
                }
            )


# ── 2. PII REDACTION PATTERNS ─────────────────────────────────────
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PHONE_PATTERN = re.compile(
    r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
)
SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
CREDIT_CARD_PATTERN = re.compile(r'\b(?:\d[ -]*?){13,16}\b')


def redact_pii(text: str) -> str:
    """
    Scans text and redacts sensitive PII (emails, phone numbers, SSNs, credit cards).
    Replaces sensitive tokens with explicit placeholders.
    """
    if not text:
        return text

    redacted = EMAIL_PATTERN.sub("<EMAIL_REDACTED>", text)
    redacted = SSN_PATTERN.sub("<SSN_REDACTED>", redacted)
    redacted = PHONE_PATTERN.sub("<PHONE_REDACTED>", redacted)
    redacted = CREDIT_CARD_PATTERN.sub("<CREDIT_CARD_REDACTED>", redacted)

    return redacted
