"""
Guardrails v3 for the AI Gateway.

Provides:
- Expanded Prompt-injection detection & corpus hardening
- Unicode/homoglyph normalisation before pattern matching
- Invisible/zero-width character stripping
- Synonym & rephrase injection coverage
- Roleplay / fiction / hypothetical wrapper detection
- System-prompt leak detection
- Input PII redaction (Credit Cards, SSNs, Emails, International Phone Numbers)
- Blocked-topic detection (expanded corpus)
- Output PII redaction
- AI-generated disclaimer
- Maximum output length enforcement

Pen-test hardening — More Shivaram (Phase 1, Oct 2026):
  Patches for 27 vulnerabilities found across 5 attack categories:
  UNI (Unicode homoglyphs), ZW (zero-width chars), SYN (synonym rephrases),
  RP (roleplay/fiction wrappers), LEAK (system-prompt leaks), BT (blocked topics).
"""

import re
import unicodedata
from typing import Dict


# ---------------------------------------------------------------------------
# Unicode confusable map — maps common homoglyphs to their ASCII equivalents.
# Covers Cyrillic, Greek, and other lookalike codepoints used in bypass attacks.
# ---------------------------------------------------------------------------
_HOMOGLYPH_MAP = str.maketrans({
    # Cyrillic lookalikes
    "\u0430": "a",  # а → a
    "\u0435": "e",  # е → e
    "\u0456": "i",  # і → i
    "\u043e": "o",  # о → o
    "\u0440": "r",  # р → r
    "\u0441": "c",  # с → c
    "\u0445": "x",  # х → x
    "\u0455": "s",  # ѕ → s
    "\u0501": "d",  # Ԁ → d
    # Greek lookalikes
    "\u0399": "I",  # Ι → I
    "\u03bf": "o",  # ο → o
    "\u03b1": "a",  # α → a
    "\u03b5": "e",  # ε → e
    # Mathematical / fullwidth
    "\uff49": "i",  # ｉ → i
    "\uff4f": "o",  # ｏ → o
    "\uff41": "a",  # ａ → a
})

# Zero-width and invisible characters that attackers insert to break keyword matching
_INVISIBLE_CHARS_RE = re.compile(
    r"[\u200b\u200c\u200d\u200e\u200f\u00ad\ufeff\u2060\u180e]"
)


def _normalize(text: str) -> str:
    """
    Canonicalize text for pattern matching:
    1. Strip zero-width / invisible characters.
    2. Replace Unicode homoglyphs with ASCII equivalents.
    3. Apply Unicode NFKC normalisation (collapses fullwidth, ligatures, etc.).
    4. Lowercase and collapse whitespace.
    """
    text = _INVISIBLE_CHARS_RE.sub("", text)
    text = text.translate(_HOMOGLYPH_MAP)
    text = unicodedata.normalize("NFKC", text)
    return " ".join(text.lower().split())


class Guardrails:
    """Apply configurable safety checks to AI Gateway input and output."""

    def __init__(self, max_output_length: int = 4000):
        self.max_output_length = max_output_length

        # ------------------------------------------------------------------
        # Prompt injection patterns
        # Matched against the normalized (homoglyph-cleaned, lowercased,
        # whitespace-collapsed) version of the input.
        # ------------------------------------------------------------------
        self.prompt_injection_patterns = [
            # Original corpus
            r"ignore\s+(all\s+)?previous\s+instructions",
            r"ignore\s+(your\s+)?previous\s+instructions",
            r"forget\s+(everything|all)\s+(above|before)",
            r"override\s+(the\s+)?system\s+instructions?",
            r"reveal\s+(the\s+)?system\s+prompt",
            r"show\s+(me\s+)?the\s+system\s+prompt",
            r"print\s+(your\s+)?initial\s+prompt",
            r"output\s+the\s+text\s+(above|before)",
            r"you\s+are\s+now\s+dan",
            r"enable\s+developer\s+mode",
            r"you\s+are\s+now\s+in\s+developer\s+mode",
            r"bypass\s+(all\s+)?safety\s+(rules|restrictions)",
            r"act\s+as\s+an\s+unrestricted",
            r"disregard\s+(all\s+)?(previous|prior)\s+instructions",
            r"new\s+instructions\s*:",
            r"pretend\s+(you\s+are|to\s+be)\s+an?\s+unrestricted",
            r"jailbreak",
            r"ignore\s+(ethical|safety)\s+guidelines",

            # --- Pen-test additions (Phase 1 hardening) ---

            # SYN-01 / SYN-02 / SYN-03: synonym rephrases of "ignore instructions"
            r"discard\s+(all\s+)?(prior|previous)\s+(directives|instructions|rules)",
            r"forget\s+(your\s+)?(rules|guidelines|constraints)",
            r"drop\s+(all\s+)?constraints",

            # SYN-04: "act as if you have no restrictions"
            r"act\s+as\s+if\s+(you\s+have\s+)?no\s+restrictions",

            # SYN-05: "suppress your safety filters"
            r"suppress\s+(your\s+)?safety\s+filters?",

            # RP-01: "roleplay as an AI with no safety rules"
            r"roleplay\s+as\s+an?\s+ai\s+with\s+no\s+(safety|ethical)?\s*"
            r"(rules|restrictions|guidelines|filters)",

            # RP-02: "write/act as an AI that ignores all guidelines"
            r"(write|act)\s+as\s+an?\s+ai\s+that\s+ignores?\s+(all\s+)?"
            r"(guidelines|rules|restrictions|filters)",

            # RP-03: "in this hypothetical, you have no restrictions"
            r"(in\s+(this\s+)?hypothetical|hypothetically)[^.]*no\s+restrictions",

            # RP-04: "imagine you are an AI with no ethical constraints"
            # Two patterns: explicit "an ai" form, and direct constraint-phrase form
            r"imagine\s+(you\s+are|yourself\s+as)\s+an?\s+ai\s+(with\s+no|without\s+(any\s+)?)"
            r"(ethical\s+)?(constraints|restrictions|rules|guidelines|filters)",
            r"imagine\s+(you\s+are|yourself\s+as)\s+.{0,40}no\s+(ethical\s+)?"
            r"(constraints|restrictions|rules|guidelines|filters)",

            # RP-05: "simulate an AI that can answer anything with no filters"
            r"simulate\s+an?\s+ai\s+(that\s+can\s+answer\s+anything|with\s+no\s+filters?)",

            # LEAK-01 / LEAK-02 / LEAK-03 / LEAK-04: system prompt leaking
            r"what\s+is\s+your\s+system\s+prompt",
            r"repeat\s+(your\s+)?instructions\s+back",
            r"what\s+were\s+you\s+told\s+at\s+the\s+start",
            r"show\s+me\s+(what\s+)?your\s+initial\s+prompt",
        ]

        # ------------------------------------------------------------------
        # Blocked topic keywords / phrases
        # Matched as substrings of the normalized input.
        # ------------------------------------------------------------------
        self.blocked_topics = [
            # Original corpus
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

            # --- Pen-test additions (Phase 1 hardening) ---

            # BT-01: TATP / specific explosive compounds
            "synthesize tatp",
            "tatp",

            # BT-02: pipe bomb and device variants
            "pipe bomb",
            "improvised explosive",
            "make a bomb",
            "create a bomb",

            # BT-03: ransomware creation
            "ransomware payload",
            "craft a ransomware",
            "create ransomware",
            "build ransomware",
            "deploy ransomware",

            # BT-04: keylogger / spyware code requests
            "write a keylogger",
            "build a keylogger",
            "create a keylogger",
            "keylogger in python",

            # BT-05: shellcode / exploit code
            "shellcode",
            "buffer overflow exploit",

            # BT-06: Molotov cocktail / IED variants
            "molotov cocktail",
            "incendiary device",

            # BT-07: C4 / military explosives
            "making c4",
            "c4 explosive",
            "plastic explosive",
            "military explosive",

            # BT-08: trojan horse malware
            "deploy a trojan",
            "trojan horse",
            "create a trojan",
        ]

    def is_prompt_injection(self, text: str) -> bool:
        """Return True when the input resembles a prompt injection.

        Normalizes the text (strips invisible chars, maps homoglyphs, NFKC,
        lowercases, collapses whitespace) before matching so that obfuscated
        variants are caught alongside their plain-text equivalents.
        """
        normalized = _normalize(text)

        return any(
            re.search(pattern, normalized, re.IGNORECASE)
            for pattern in self.prompt_injection_patterns
        )

    def is_blocked_topic(self, text: str) -> bool:
        """Return True when the input contains a configured blocked topic."""
        normalized = _normalize(text)

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
        """Redact common credit card, email, SSN, and phone number patterns."""
        # 1. Credit Card Redaction (13-19 digits)
        text = re.sub(
            r"\b\d(?:[ -]?\d){12,18}\b",
            lambda match: (
                "[REDACTED_CREDIT_CARD]"
                if len(re.sub(r"[ -]", "", match.group())) >= 13
                else match.group()
            ),
            text,
        )

        # 2. Email Redaction
        text = re.sub(
            r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
            "[REDACTED_EMAIL]",
            text,
            flags=re.IGNORECASE,
        )

        # 3. SSN Redaction (hyphenated or spaced 9 digits: XXX-XX-XXXX)
        text = re.sub(
            r"\b\d{3}[- ]\d{2}[- ]\d{4}\b",
            "[REDACTED_SSN]",
            text,
        )

        # 4. International & Standard Phone Numbers (10-15 digits)
        text = re.sub(
            (
                r"(?:\+\d{1,3}[-.\s]?(?:\(\d{2,5}\)[-.\s]?)?"
                r"|\(\d{2,5}\)[-.\s]?)\d{3,5}[-.\s]?\d{3,5}\b"
            ),
            lambda match: (
                "[REDACTED_PHONE]"
                if 10 <= len(re.sub(r"\D", "", match.group())) <= 15
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
        sanitized_text = self.redact_pii(text)
        return {
            **check_result,
            "text": sanitized_text,
            "pii_redacted": sanitized_text != text,
        }

    def process_output(self, text: str) -> str:
        """Redact PII, add disclaimer, and enforce maximum length."""
        sanitized = self.redact_pii(text)

        disclaimer = "\n\nAI-generated, verify before acting."

        available_length = max(
            0,
            self.max_output_length - len(disclaimer),
        )

        sanitized = sanitized[:available_length]

        return sanitized + disclaimer
