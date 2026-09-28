from fastapi.testclient import TestClient

from app.main import app


def _patch_dependencies(monkeypatch, seen):
    """Mock the model, rate limiter and database so no services are needed."""

    def mock_ask_gpt(question):
        seen["question"] = question
        return {
            "answer": "Mock answer",
            "model": "gemma-4-31b-it",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
        }

    def mock_rate_limit(user_id, org_tier="free"):
        return {
            "allowed": True,
            "tokens_remaining": 4,
            "bucket_capacity": 8,
            "org_tier": org_tier,
        }

    monkeypatch.setattr("app.main.ask_gpt", mock_ask_gpt)
    monkeypatch.setattr("app.main.check_rate_limit", mock_rate_limit)
    monkeypatch.setattr("app.main.setup_database", lambda: None)
    monkeypatch.setattr(
        "app.main.log_interaction", lambda **kwargs: "test-interaction-id"
    )


def _ask(question, role=None):
    headers = {"X-User-ID": "test-user"}
    if role:
        headers["X-User-Role"] = role
    with TestClient(app) as client:
        return client.post(
            "/copilot/query", headers=headers, json={"question": question}
        )


def test_analyst_gets_tool_result_and_citation(monkeypatch):
    seen = {}
    _patch_dependencies(monkeypatch, seen)

    response = _ask("How risky is asset-001?", role="analyst")

    assert response.status_code == 200
    data = response.json()
    assert data["tool_call"]["ok"] is True
    assert data["tool_call"]["result"]["band"] == "Critical"
    assert data["citations"] == [
        {
            "id": "cit-risk-asset-001",
            "type": "risk_score",
            "id_ref": "asset-001",
            "url": "/risk/asset-001",
        }
    ]
    assert "Verified data from the risk_score_get tool" in seen["question"]


def test_viewer_is_denied_the_risk_tool(monkeypatch):
    _patch_dependencies(monkeypatch, {})

    response = _ask("How risky is asset-001?", role="viewer")

    assert response.status_code == 403
    assert response.json()["detail"]["error"] == "Permission denied"


def test_no_role_is_denied_the_risk_tool(monkeypatch):
    _patch_dependencies(monkeypatch, {})

    response = _ask("How risky is asset-001?")

    assert response.status_code == 403


def test_question_without_asset_skips_the_tool(monkeypatch):
    seen = {}
    _patch_dependencies(monkeypatch, seen)

    response = _ask("Explain what a firewall does.")

    assert response.status_code == 200
    data = response.json()
    assert data["tool_call"] is None
    assert data["citations"] == []
    assert "Verified data" not in seen["question"]


def test_unknown_asset_reports_tool_error_without_crashing(monkeypatch):
    _patch_dependencies(monkeypatch, {})

    response = _ask("How risky is asset-999?", role="analyst")

    assert response.status_code == 200
    data = response.json()
    assert data["tool_call"]["ok"] is False
    assert "not found" in data["tool_call"]["error"]
    assert data["citations"] == []
