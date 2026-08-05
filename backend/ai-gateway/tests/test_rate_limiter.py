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


def make_mock_redis(current_count):
    mock = MagicMock()
    mock.incr.return_value = current_count
    mock.ttl.return_value = 45
    return mock


def test_first_request_is_allowed():
    mock_redis = make_mock_redis(current_count=1)
    with patch.object(rate_limiter, "redis_client", mock_redis):
        result = rate_limiter.check_rate_limit("alice")
    assert result["requests_made"] == 1


def test_fifth_request_is_still_allowed():
    mock_redis = make_mock_redis(current_count=5)
    with patch.object(rate_limiter, "redis_client", mock_redis):
        result = rate_limiter.check_rate_limit("alice")
    assert result["requests_made"] == 5


def test_sixth_request_is_blocked():
    mock_redis = make_mock_redis(current_count=6)
    with patch.object(rate_limiter, "redis_client", mock_redis):
        with pytest.raises(HTTPException) as exc_info:
            rate_limiter.check_rate_limit("alice")
    assert exc_info.value.status_code == 429
