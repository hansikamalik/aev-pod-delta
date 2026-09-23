from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_citations_endpoint_matches_documents():
    payload = {
        "text": "The vulnerability was found in the Active Directory service.",
        "source_documents": ["Active Directory", "SentinelOne", "GitHub"]
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
        "source_documents": ["Microsoft Defender", "GitHub", "Elastic"]
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
        "source_documents": ["CVE-2024-1234", "Malware-X"]
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
        "source_documents": []
    }
    response = client.post("/citations/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["citations"] == []
    assert data["matched_count"] == 0
