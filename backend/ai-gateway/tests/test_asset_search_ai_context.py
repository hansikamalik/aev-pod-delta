"""AI Context integration for the asset_search tool."""

import httpx

from app import asset_search as asset_search_module
from app.asset_search import asset_search
from app.config import settings


def _ok_response():
    request = httpx.Request("POST", "http://ai-context/copilot/asset-search")
    return httpx.Response(
        200,
        request=request,
        json={
            "query": "database",
            "total_results": 1,
            "results": [
                {
                    "id": "ctx-9",
                    "asset_name": "prod-db-01",
                    "asset_type": "database",
                    "description": "Primary DB",
                    "risk_score": 88,
                    "similarity_score": 0.91,
                }
            ],
        },
    )


def test_uses_ai_context_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "AI_CONTEXT_URL", "http://ai-context")
    monkeypatch.setattr(asset_search_module.httpx, "post", lambda *a, **k: _ok_response())

    r = asset_search("database", "u1")

    assert r["source"] == "ai_context"
    assert r["results"][0]["name"] == "prod-db-01"
    assert r["citations"][0] == {
        "id": "cit-asset-ctx-9",
        "type": "asset",
        "id_ref": "ctx-9",
        "url": "/assets/ctx-9",
    }


def test_falls_back_to_local_when_ai_context_fails(monkeypatch):
    monkeypatch.setattr(settings, "AI_CONTEXT_URL", "http://ai-context")

    def boom(*args, **kwargs):
        raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr(asset_search_module.httpx, "post", boom)

    r = asset_search("redis", "u1")

    assert r["source"] == "local"
    assert r["results"][0]["name"] == "Redis"


def test_local_only_when_url_not_set(monkeypatch):
    monkeypatch.setattr(settings, "AI_CONTEXT_URL", "")

    def should_not_run(*args, **kwargs):
        raise AssertionError("must not call AI Context when URL is empty")

    monkeypatch.setattr(asset_search_module.httpx, "post", should_not_run)

    assert asset_search("redis", "u1")["source"] == "local"


def test_passes_timeout_to_ai_context(monkeypatch):
    monkeypatch.setattr(settings, "AI_CONTEXT_URL", "http://ai-context")
    monkeypatch.setattr(settings, "AI_CONTEXT_TIMEOUT", 2.5)
    seen = {}

    def fake_post(url, **kwargs):
        seen.update(kwargs, url=url)
        return _ok_response()

    monkeypatch.setattr(asset_search_module.httpx, "post", fake_post)
    asset_search("database", "u1")

    assert seen["timeout"] == 2.5
    assert seen["url"] == "http://ai-context/copilot/asset-search"


def test_passes_bearer_token_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "AI_CONTEXT_URL", "http://ai-context")
    monkeypatch.setattr(settings, "AI_CONTEXT_TOKEN", "test-secret-token-32-chars-minimum")
    seen = {}

    def fake_post(url, **kwargs):
        seen.update(kwargs, url=url)
        return _ok_response()

    monkeypatch.setattr(asset_search_module.httpx, "post", fake_post)
    asset_search("database", "u1")

    assert seen["headers"].get("Authorization") == "Bearer test-secret-token-32-chars-minimum"