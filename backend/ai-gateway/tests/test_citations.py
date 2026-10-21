"""Tests for citations router and citation verification utilities."""

from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.citations import (
    build_citation,
    ensure_response_citation,
)
from app.main import app

client = TestClient(app)


def test_citations_endpoint_matches_documents():
    payload = {
        "text": "The vulnerability was found in the Active Directory service.",
        "source_documents": ["Active Directory", "SentinelOne", "GitHub"],
    }
    response = client.post("/citations/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["citations"]) == 1
    assert data["citations"][0]["name"] == "Active Directory"
    assert data["matched_count"] == 1


def test_citations_endpoint_multiple_matches():
    payload = {
        "text": "Both Microsoft Defender and GitHub were impacted by the incident.",
        "source_documents": ["Microsoft Defender", "GitHub", "Elastic"],
    }
    response = client.post("/citations/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    names = [doc["name"] for doc in data["citations"]]
    assert "Microsoft Defender" in names
    assert "GitHub" in names
    assert data["matched_count"] == 2


def test_citations_endpoint_no_matches():
    payload = {
        "text": "Clean system scan completed with no issues.",
        "source_documents": ["CVE-2024-1234", "Malware-X"],
    }
    response = client.post("/citations/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["citations"] == []
    assert data["matched_count"] == 0


def test_citations_endpoint_empty_sources():
    payload = {
        "text": "Some text content here.",
        "source_documents": [],
    }
    response = client.post("/citations/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["citations"] == []
    assert data["matched_count"] == 0


def test_build_citation_supported_and_unsupported_types():
    cit_valid = build_citation("asset", "asset-001", "Production DB")
    assert cit_valid["id"] == "cit-asset-asset-001"
    assert cit_valid["type"] == "asset"

    cit_unsupported = build_citation("random_type", "ref-999")
    assert cit_unsupported["type"] == "reference"


def test_ensure_response_citation_empty_adds_default():
    empty_res = ensure_response_citation([], question="What is MFA?", answer="MFA is ...")
    assert len(empty_res) == 1
    assert empty_res[0]["type"] == "kb_article"
    assert "Enterprise Security Knowledge Base" in empty_res[0]["title"]


def test_ensure_response_citation_non_empty_retains_existing():
    existing = [{"id": "cit-1", "type": "asset", "id_ref": "asset-123"}]
    res = ensure_response_citation(existing)
    assert len(res) == 1
    assert res[0]["id"] == "cit-1"


def test_query_always_carries_citation():
    with patch("app.main.ask_gpt", return_value={
        "answer": "This is a safe answer without tool citation.",
        "model": "test-model",
        "citations": [],
    }):
        response = client.post(
            "/copilot/query",
            headers={"X-User-ID": "test-user"},
            json={"question": "Explain the zero trust architecture."},
        )
        assert response.status_code == 200
        data = response.json()
        assert "citations" in data
        assert len(data["citations"]) >= 1
        assert any(c.get("type") in {"kb_article", "document", "reference", "asset"}
                   for c in data["citations"])


def test_flag_citation_endpoint_success():
    mock_conn = MagicMock()
    with patch("app.audit_log._get_connection", return_value=mock_conn):
        response = client.post(
            "/copilot/citations/flag",
            headers={"X-User-ID": "analyst-1"},
            json={
                "interaction_id": "int-123",
                "citation_id": "cit-policy-1",
                "reason": "This policy rule does not apply to database.",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert mock_conn.__enter__.return_value.execute.called
        assert mock_conn.__enter__.return_value.commit.called


def test_flag_citation_endpoint_missing_fields_returns_422():
    response = client.post(
        "/copilot/citations/flag",
        headers={"X-User-ID": "analyst-1"},
        json={
            "interaction_id": "int-123",
        },
    )
    assert response.status_code == 422

