from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_copilot_query_end_to_end(monkeypatch):
    """Test the complete /copilot/query request flow."""

    def mock_ask_gpt(question):
        return {
            "answer": f"Mock answer for: {question}",
            "model": "gemma-4-31b-it",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
        }

    def mock_rate_limit(user_id):
        return {
            "requests_made": 1,
            "requests_remaining": 4,
            "resets_in_seconds": 60,
        }

    monkeypatch.setattr("app.main.ask_gpt", mock_ask_gpt)
    monkeypatch.setattr("app.main.check_rate_limit", mock_rate_limit)

    response = client.post(
        "/copilot/query",
        headers={"X-User-ID": "test-user"},
        json={
            "question": "Explain what a firewall does."
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["question"] == "Explain what a firewall does."
    assert data["answer"].startswith("Mock answer for:")
    assert data["model"] == "gemma-4-31b-it"

    assert data["usage"]["prompt_tokens"] == 10
    assert data["usage"]["completion_tokens"] == 20
    assert data["usage"]["total_tokens"] == 30

    assert data["cost"]["model"] == "gemma-4-31b-it"
    assert "estimated_cost" in data["cost"]

    assert data["rate_limit"]["requests_made"] == 1

    assert data["guardrails"]["disclaimer_added"] is True
    assert data["guardrails"]["max_output_length"] == 4000

    assert "AI-generated, verify before acting." in data["answer"]