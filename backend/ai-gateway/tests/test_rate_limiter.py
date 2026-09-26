import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest.mock import patch, MagicMock  # noqa: E402
from fastapi import HTTPException  # noqa: E402
import pytest  # noqa: E402

try:
    import app.rate_limiter as rate_limiter  # noqa: E402
except ImportError:
    import rate_limiter  # noqa: E402


def make_mock_script(return_value):
    """Mock the Lua script callable that check_rate_limit invokes."""
    mock_script = MagicMock(return_value=return_value)
    return mock_script


def test_request_is_allowed_when_tokens_available():
    # allowed=1, tokens_remaining=7 (bucket had room)
    mock_script = make_mock_script([1, 7])
    with patch.object(rate_limiter, "_token_bucket", mock_script):
        result = rate_limiter.check_rate_limit("alice")
    assert result["allowed"] is True
    assert result["tokens_remaining"] == 7


def test_request_allowed_on_last_token():
    # allowed=1, tokens_remaining=0 (used the last token, still allowed)
    mock_script = make_mock_script([1, 0])
    with patch.object(rate_limiter, "_token_bucket", mock_script):
        result = rate_limiter.check_rate_limit("alice")
    assert result["allowed"] is True
    assert result["tokens_remaining"] == 0


def test_request_is_blocked_when_bucket_empty():
    # allowed=0, tokens_remaining=0 (no tokens left, request rejected)
    mock_script = make_mock_script([0, 0])
    with patch.object(rate_limiter, "_token_bucket", mock_script):
        with pytest.raises(HTTPException) as exc_info:
            rate_limiter.check_rate_limit("alice")
    assert exc_info.value.status_code == 429


def test_redis_unavailable_falls_back_gracefully():
    import redis as redis_module
    mock_script = MagicMock(side_effect=redis_module.exceptions.ConnectionError)
    with patch.object(rate_limiter, "_token_bucket", mock_script):
        result = rate_limiter.check_rate_limit("alice")
    assert result["allowed"] is True
    assert result["warning"] == "Redis unavailable"