"""Role checks, input limits and caps on the admin/audit/flag endpoints."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

FLAG_BODY = {
    "interaction_id": "int-1",
    "citation_id": "cit-policy-1",
    "reason": "Does not apply.",
}


# ---- /admin/retention-cleanup ----------------------------------------------

def test_retention_cleanup_admin_allowed():
    with patch("app.main.cleanup_expired_rows", return_value=0) as job:
        r = client.post("/admin/retention-cleanup", headers={"X-User-Role": "admin"})
    assert r.status_code == 200
    assert job.called


def test_retention_cleanup_denied_for_other_roles():
    for role in ["analyst", "viewer", "auditor", "anonymous"]:
        with patch("app.main.cleanup_expired_rows") as job:
            r = client.post("/admin/retention-cleanup", headers={"X-User-Role": role})
        assert r.status_code == 403
        assert not job.called


def test_retention_cleanup_denied_without_header():
    with patch("app.main.cleanup_expired_rows") as job:
        r = client.post("/admin/retention-cleanup")
    assert r.status_code == 403
    assert not job.called


# ---- /copilot/citations/flag -----------------------------------------------

def test_flag_denied_for_anonymous_and_auditor():
    for role in [None, "anonymous", "auditor"]:
        headers = {"X-User-ID": "u1"}
        if role:
            headers["X-User-Role"] = role
        with patch("app.main.flag_citation") as flag:
            r = client.post("/copilot/citations/flag", headers=headers, json=FLAG_BODY)
        assert r.status_code == 403
        assert not flag.called


def test_flag_allowed_for_analyst():
    with patch("app.main.flag_citation") as flag:
        r = client.post(
            "/copilot/citations/flag",
            headers={"X-User-ID": "u1", "X-User-Role": "analyst"},
            json=FLAG_BODY,
        )
    assert r.status_code == 200
    assert flag.called


def test_flag_reason_too_long_returns_422():
    body = dict(FLAG_BODY, reason="x" * 1001)
    with patch("app.main.flag_citation") as flag:
        r = client.post(
            "/copilot/citations/flag",
            headers={"X-User-ID": "u1", "X-User-Role": "analyst"},
            json=body,
        )
    assert r.status_code == 422
    assert not flag.called


def test_flag_empty_reason_returns_422():
    body = dict(FLAG_BODY, reason="")
    r = client.post(
        "/copilot/citations/flag",
        headers={"X-User-ID": "u1", "X-User-Role": "analyst"},
        json=body,
    )
    assert r.status_code == 422


# ---- /copilot/audit-log limit cap ------------------------------------------

def test_audit_log_limit_above_cap_returns_422():
    with patch("app.main.query_interactions", return_value=[]) as q:
        r = client.get(
            "/copilot/audit-log",
            params={"limit": 501},
            headers={"X-User-Role": "admin"},
        )
    assert r.status_code == 422
    assert not q.called


def test_audit_log_limit_zero_returns_422():
    r = client.get(
        "/copilot/audit-log",
        params={"limit": 0},
        headers={"X-User-Role": "admin"},
    )
    assert r.status_code == 422


def test_audit_log_limit_at_cap_is_allowed():
    with patch("app.main.query_interactions", return_value=[]) as q:
        r = client.get(
            "/copilot/audit-log",
            params={"limit": 500},
            headers={"X-User-Role": "admin"},
        )
    assert r.status_code == 200
    assert q.call_args.kwargs["limit"] == 500
