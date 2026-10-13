"""Tests for the load generator module."""

from unittest.mock import MagicMock, patch
import pytest
import requests

from app.load_generator import (
    run_load_generator,
    send_request,
)


def test_zero_requests_raise_value_error():
    with pytest.raises(ValueError, match="must be positive"):
        run_load_generator(total_requests=0, max_workers=1)


def test_zero_workers_raise_value_error():
    with pytest.raises(ValueError, match="must be positive"):
        run_load_generator(total_requests=1, max_workers=0)


def test_negative_requests_raise_value_error():
    with pytest.raises(ValueError, match="must be positive"):
        run_load_generator(total_requests=-1, max_workers=1)


def test_negative_workers_raise_value_error():
    with pytest.raises(ValueError, match="must be positive"):
        run_load_generator(total_requests=1, max_workers=-1)


def test_invalid_user_count_raises_value_error(monkeypatch):
    monkeypatch.setattr("app.load_generator.USER_COUNT", 0)
    with pytest.raises(ValueError, match="LOAD_TEST_USERS must be positive"):
        run_load_generator(total_requests=1, max_workers=1)


def test_send_request_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("requests.post", return_value=mock_resp):
        res = send_request(1)
        assert res["status"] == 200
        assert "latency" in res


def test_send_request_failure():
    with patch("requests.post", side_effect=requests.RequestException("boom")):
        res = send_request(1)
        assert res["status"] is None
        assert "latency" in res


def test_run_load_generator_metrics():
    mock_results = [
        {"status": 200, "latency": 0.01},
        {"status": 429, "latency": 0.02},
        {"status": 500, "latency": 0.03},
        {"status": None, "latency": 0.04},
    ]

    with patch(
        "app.load_generator.send_request",
        side_effect=mock_results,
    ):
        results = run_load_generator(total_requests=4, max_workers=2)
        assert len(results) == 4
        assert results[0]["status"] == 200
