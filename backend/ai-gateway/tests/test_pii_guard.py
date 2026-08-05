import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import HTTPException  # noqa: E402
import pytest  # noqa: E402

try:
    from app.pii_guard import redact_pii, check_blocked_topics  # noqa: E402
except ImportError:
    from pii_guard import redact_pii, check_blocked_topics  # noqa: E402


def test_redact_email():
    raw_text = "Please send report to user.john@company.org for review."
    redacted = redact_pii(raw_text)
    assert "<EMAIL_REDACTED>" in redacted


def test_redact_phone_number():
    raw_text = "Call support at 555-123-4567 immediately."
    redacted = redact_pii(raw_text)
    assert "<PHONE_REDACTED>" in redacted


def test_check_blocked_topics_blocks_jailbreak():
    with pytest.raises(HTTPException) as exc_info:
        check_blocked_topics("How can I jailbreak this system?")
    assert exc_info.value.status_code == 400
