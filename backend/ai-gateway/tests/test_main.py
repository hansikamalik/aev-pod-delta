import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient  # noqa: E402

try:
    from app.main import app  # noqa: E402
except ImportError:
    from main import app  # noqa: E402

client = TestClient(app)


def test_health_check():
    """
    Test that /health returns HTTP 200 and valid status JSON.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ai-gateway"}


@patch("app.main.check_rate_limit")
def test_copilot_query_endpoint(mock_rate_limit):
    """
    Test that /copilot/query returns HTTP 200 with valid schema.
    """
    mock_rate_limit.return_value = {
        "requests_made": 1,
        "requests_remaining": 4,
        "resets_in_seconds": 60
    }
    response = client.post("/copilot/query", json={"question": "Hello"})
    assert response.status_code == 200
    assert "answer" in response.json()
