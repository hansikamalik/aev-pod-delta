"""
Guardrails v1 for the AI Gateway.

Provides:
- Prompt-injection detection
- Input PII redaction
- Blocked-topic detection
- Output PII redaction
- AI-generated disclaimer
- Maximum output length enforcement
"""

import re
from typing import Dict


class Guardrails:
    """Apply configurable safety checks to AI Gateway input and output."""

    def __init__(self, max_output_length: int = 4000):
        self.max_output_length = max_output_length

        self.prompt_injection_patterns = [
            r"ignore\s+(all\s+)?previous\s+instructions",
            r"ignore\s+(your\s+)?previous\s+instructions",
            r"forget\s+(everything|all)\s+(above|before)",
            r"override\s+(the\s+)?system\s+instructions?",
            r"reveal\s+(the\s+)?system\s+prompt",
            r"show\s+(me\s+)?the\s+system\s+prompt",
            r"you\s+are\s+now\s+dan",
            r"bypass\s+(all\s+)?safety\s+(rules|restrictions)",
            r"act\s+as\s+an\s+unrestricted",
            r"disregard\s+(all\s+)?(previous|prior)\s+instructions",
            r"new\s+instructions\s*:",
            r"pretend\s+(you\s+are|to\s+be)\s+an?\s+unrestricted",
        ]

        self.blocked_topics = [
            "build a bomb",
            "make an explosive",
            "create malware",
            "creating malware",
            "build a weapon",
            "make a weapon",
            "build an explosive device",
            "create a virus",
            "creating a virus",
            "write malware",
            "writing malware",
        ]

    def is_prompt_injection(self, text: str) -> bool:
        """Return True when the input resembles a prompt injection."""

        normalized = " ".join(text.lower().split())

        return any(
            re.search(pattern, normalized, re.IGNORECASE)
            for pattern in self.prompt_injection_patterns
        )

    def is_blocked_topic(self, text: str) -> bool:
        """Return True when the input contains a configured blocked topic."""

        normalized = " ".join(text.lower().split())

        return any(
            topic.lower() in normalized
            for topic in self.blocked_topics
        )

    def check_input(self, text: str) -> Dict[str, object]:
        """Check input for prompt injection and blocked topics."""

        if self.is_prompt_injection(text):
            return {
                "allowed": False,
                "reason": "prompt_injection",
            }

        if self.is_blocked_topic(text):
            return {
                "allowed": False,
                "reason": "blocked_topic",
            }

        return {
            "allowed": True,
            "reason": None,
        }

    @staticmethod
    def redact_pii(text: str) -> str:
        """Redact common email, SSN and credit-card patterns."""

        text = re.sub(
            r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
            "[REDACTED_EMAIL]",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\b\d{3}-\d{2}-\d{4}\b",
            "[REDACTED_SSN]",
            text,
        )

        text = re.sub(
            r"\b\d(?:[ -]?\d){12,18}\b",
            lambda match: (
                "[REDACTED_CREDIT_CARD]"
                if len(re.sub(r"[ -]", "", match.group())) >= 13
                else match.group()
            ),
            text,
        )

        return text

    def process_input(self, text: str) -> Dict[str, object]:
        """Validate and redact an incoming prompt."""

        check_result = self.check_input(text)

        if not check_result["allowed"]:
            return {
                **check_result,
                "text": text,
            }

        return {
            **check_result,
            "text": self.redact_pii(text),
        }

    def process_output(self, text: str) -> str:
        """
        Redact PII, add disclaimer, and enforce maximum length.
        """

        sanitized = self.redact_pii(text)

        disclaimer = "\n\nAI-generated, verify before acting."

        # Reserve space for the disclaimer so the FINAL response
        # never exceeds max_output_length.
        available_length = max(
            0,
            self.max_output_length - len(disclaimer),
        )

        sanitized = sanitized[:available_length]

        return sanitized + disclaimer
