"""Tests for asset_search and exposure_query tools."""

import pytest
from app.asset_search import asset_search
from app.exposure_query import exposure_query, EXPOSURES


# =============================================================================
# asset_search tests
# =============================================================================

def test_asset_search_success():
    result = asset_search("gateway", user_id="user1")
    assert result["tool"] == "asset_search"
    assert result["count"] >= 1
    assert any(a["id"] == "asset-001" for a in result["results"])
    assert len(result["citations"]) == result["count"]
    assert result["citations"][0]["id"] == "cit-asset-asset-001"


def test_asset_search_ai_context_remote_success():
    from unittest.mock import patch, MagicMock

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "query": "cloud",
        "total_results": 1,
        "results": [
            {
                "id": "99",
                "asset_name": "Cloud VPC",
                "asset_type": "network",
                "description": "AWS production VPC",
                "similarity_score": 0.95,
            }
        ],
    }
    mock_resp.raise_for_status.return_value = None

    with patch("app.config.settings.AI_CONTEXT_URL", "http://ai-context:8000"), \
         patch("httpx.post", return_value=mock_resp):
        res = asset_search("cloud", user_id="user1")
        assert res["source"] == "ai_context"
        assert res["count"] == 1
        assert res["results"][0]["id"] == "99"
        assert res["results"][0]["name"] == "Cloud VPC"
        assert res["citations"][0]["id"] == "cit-asset-99"


def test_asset_search_by_id():
    result = asset_search("asset-002", user_id="user1")
    assert result["count"] == 1
    assert result["results"][0]["name"] == "Redis"


def test_asset_search_no_match():
    result = asset_search("nonexistent-system-xyz", user_id="user1")
    assert result["count"] == 0
    assert result["results"] == []
    assert result["citations"] == []


def test_asset_search_invalid_query_type():
    with pytest.raises(TypeError, match="query must be a string"):
        asset_search(12345, user_id="user1")  # type: ignore


def test_asset_search_empty_query():
    with pytest.raises(ValueError, match="query cannot be empty"):
        asset_search("   ", user_id="user1")


def test_asset_search_invalid_user_id_type():
    with pytest.raises(TypeError, match="user_id must be a string"):
        asset_search("gateway", user_id=None)  # type: ignore


def test_asset_search_empty_user_id():
    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        asset_search("gateway", user_id="  ")


# =============================================================================
# exposure_query tests
# =============================================================================

def test_exposure_query_all():
    result = exposure_query(user_id="user1")
    assert result["tool"] == "exposure_query"
    assert result["count"] == len(EXPOSURES)
    assert len(result["citations"]) == len(EXPOSURES)


def test_exposure_query_by_asset_id():
    result = exposure_query(user_id="user1", asset_id="asset-001")
    assert result["count"] == 1
    assert result["results"][0]["asset_id"] == "asset-001"
    assert result["citations"][0]["id"] == "cit-exposure-asset-001"


def test_exposure_query_by_severity():
    result = exposure_query(user_id="user1", severity="high")
    assert result["count"] == 1
    assert result["results"][0]["risk_level"] == "high"


def test_exposure_query_combined_filter():
    result = exposure_query(user_id="user1", asset_id="asset-003", severity="high")
    assert result["count"] == 1
    assert result["results"][0]["asset_name"] == "PostgreSQL"


def test_exposure_query_no_match():
    result = exposure_query(user_id="user1", asset_id="asset-001", severity="critical")
    assert result["count"] == 0
    assert result["results"] == []


def test_exposure_query_invalid_user_id_type():
    with pytest.raises(TypeError, match="user_id must be a string"):
        exposure_query(user_id=123)  # type: ignore


def test_exposure_query_empty_user_id():
    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        exposure_query(user_id="   ")


def test_exposure_query_invalid_asset_id_type():
    with pytest.raises(TypeError, match="asset_id must be a string"):
        exposure_query(user_id="user1", asset_id=999)  # type: ignore


def test_exposure_query_empty_asset_id():
    with pytest.raises(ValueError, match="asset_id cannot be empty"):
        exposure_query(user_id="user1", asset_id="  ")


def test_exposure_query_invalid_severity_type():
    with pytest.raises(TypeError, match="severity must be a string"):
        exposure_query(user_id="user1", severity=True)  # type: ignore


def test_exposure_query_empty_severity():
    with pytest.raises(ValueError, match="severity cannot be empty"):
        exposure_query(user_id="user1", severity="   ")


def test_exposure_query_invalid_severity_value():
    with pytest.raises(ValueError, match="severity must be low, medium, high, or critical"):
        exposure_query(user_id="user1", severity="ultra-critical")
