from fastapi.testclient import TestClient

from app.main import app


def _ask(question, role="admin", user="hans"):
    headers = {"X-User-ID": user}
    if role:
        headers["X-User-Role"] = role
    with TestClient(app) as client:
        return client.get(
            "/copilot/audit-log", params={"user_id": user}, headers=headers
        )


def test_admin_can_read_audit_log(monkeypatch):
    monkeypatch.setattr(
        "app.main.query_interactions",
        lambda **kwargs: [{"id": "row-1", "user_id": "hans", "model": "gemma-4-31b-it"}],
    )
    response = _ask("ignored", role="admin")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["results"][0]["user_id"] == "hans"


def test_auditor_can_read_audit_log(monkeypatch):
    monkeypatch.setattr("app.main.query_interactions", lambda **kwargs: [])
    response = _ask("ignored", role="auditor")
    assert response.status_code == 200


def test_viewer_is_denied(monkeypatch):
    monkeypatch.setattr("app.main.query_interactions", lambda **kwargs: [])
    response = _ask("ignored", role="viewer")
    assert response.status_code == 403
    assert response.json()["detail"]["error"] == "Permission denied"


def test_filters_are_passed_through(monkeypatch):
    seen = {}

    def fake_query(**kwargs):
        seen.update(kwargs)
        return []

    monkeypatch.setattr("app.main.query_interactions", fake_query)

    with TestClient(app) as client:
        client.get(
            "/copilot/audit-log",
            params={
                "user_id": "hans",
                "model": "gemma-4-31b-it",
                "start_date": "2026-09-01",
                "end_date": "2026-09-30",
                "limit": 10,
            },
            headers={"X-User-ID": "hans", "X-User-Role": "admin"},
        )

    assert seen["user_id"] == "hans"
    assert seen["model"] == "gemma-4-31b-it"
    assert seen["start_date"] == "2026-09-01"
    assert seen["end_date"] == "2026-09-30"
    assert seen["limit"] == 10