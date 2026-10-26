"""
Unit tests for P1-1: JWT Authentication Middleware & Cryptographic Trust Boundaries.
Tests Pod Alpha token verification, RBAC enforcement, header-spoofing defense, and strict mode.
"""

import time
from fastapi.testclient import TestClient
import jwt
import pytest

from app.config import settings
from app.jwt_auth import AuthenticatedUser, create_jwt_token, verify_jwt_token
from app.main import app


@pytest.fixture
def test_client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_rate_and_gpt(monkeypatch):
    """Bypass external upstream APIs during unit test execution."""
    monkeypatch.setattr(
        "app.main.check_rate_limit",
        lambda user_id, org_tier="free": {
            "allowed": True,
            "tokens_remaining": 100,
            "bucket_capacity": 100,
            "org_tier": org_tier,
        },
    )
    monkeypatch.setattr(
        "app.main.ask_gpt",
        lambda question, tools=None: {
            "answer": "Cryptographically verified answer for test.",
            "model": "gemma-4-31b-it",
            "usage": {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25},
        },
    )


class TestJWTTokenMintingAndDecoding:
    """Test cryptographic JWT token generation and claims extraction."""

    def test_mint_and_verify_valid_token(self):
        token = create_jwt_token(
            user_id="alice_sec",
            role="analyst",
            tenant_id="fintech_corp",
            org_tier="enterprise",
            budget_cap=500.0,
        )
        user: AuthenticatedUser = verify_jwt_token(token)

        assert user.user_id == "alice_sec"
        assert user.role == "analyst"
        assert user.tenant_id == "fintech_corp"
        assert user.org_tier == "enterprise"
        assert user.budget_cap == 500.0
        assert user.token_auth is True

    def test_reject_expired_token(self):
        # Create token that expired 10 seconds ago
        token = create_jwt_token(
            user_id="bob_expired",
            role="viewer",
            expires_in_seconds=-10,
        )
        with pytest.raises(Exception) as exc_info:
            verify_jwt_token(token)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error"] == "token_expired"

    def test_reject_tampered_signature(self):
        token = create_jwt_token(user_id="charlie", role="admin")
        # Tamper token signature
        tampered = token[:-6] + "xyz123"
        with pytest.raises(Exception) as exc_info:
            verify_jwt_token(tampered)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error"] == "invalid_token"

    def test_reject_wrong_issuer(self):
        token = create_jwt_token(user_id="dave", issuer="untrusted-rogue-issuer")
        with pytest.raises(Exception) as exc_info:
            verify_jwt_token(token)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error"] == "invalid_issuer"

    def test_reject_wrong_audience(self):
        token = create_jwt_token(user_id="eve", audience="aev-pod-gamma-unrelated")
        with pytest.raises(Exception) as exc_info:
            verify_jwt_token(token)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error"] == "invalid_audience"


class TestCryptographicTrustBoundariesAPI:
    """Test API endpoint protection and trust boundaries under strict auth."""

    def test_strict_mode_rejects_missing_bearer_token(self, test_client, monkeypatch):
        monkeypatch.setattr(settings, "JWT_AUTH_REQUIRED", True)

        resp = test_client.post(
            "/copilot/query",
            json={"question": "What is the status?"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"]["error"] == "missing_bearer_token"

    def test_strict_mode_rejects_invalid_token(self, test_client, monkeypatch):
        monkeypatch.setattr(settings, "JWT_AUTH_REQUIRED", True)

        resp = test_client.post(
            "/copilot/query",
            headers={"Authorization": "Bearer not-a-real-token"},
            json={"question": "What is the status?"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"]["error"] == "invalid_token"

    def test_strict_mode_allows_valid_bearer_token(self, test_client, mock_rate_and_gpt, monkeypatch):
        monkeypatch.setattr(settings, "JWT_AUTH_REQUIRED", True)

        token = create_jwt_token(user_id="analyst_sarah", role="analyst", org_tier="enterprise")
        resp = test_client.post(
            "/copilot/query",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "What is our general security posture?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data

    def test_header_spoofing_resistance(self, test_client, monkeypatch):
        """Ensure an unprivileged bearer token cannot be escalated via raw X-User-Role header."""
        monkeypatch.setattr(settings, "JWT_AUTH_REQUIRED", True)

        # Token claims: role=viewer
        viewer_token = create_jwt_token(user_id="malicious_viewer", role="viewer")

        # Caller attempts to spoof X-User-Role: admin
        resp = test_client.post(
            "/admin/retention-cleanup",
            headers={
                "Authorization": f"Bearer {viewer_token}",
                "X-User-Role": "admin",
            },
        )
        # MUST be 403 Forbidden because verified token role is viewer
        assert resp.status_code == 403
        assert "not permitted" in resp.json()["detail"]["reason"]

    def test_admin_role_authorization_via_token(self, test_client, monkeypatch):
        monkeypatch.setattr(settings, "JWT_AUTH_REQUIRED", True)

        admin_token = create_jwt_token(user_id="admin_user", role="admin")
        resp = test_client.post(
            "/admin/retention-cleanup",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_audit_logs_rbac_via_token(self, test_client, monkeypatch):
        monkeypatch.setattr(settings, "JWT_AUTH_REQUIRED", True)
        monkeypatch.setattr("app.main.query_interactions", lambda **kwargs: [])

        # Viewer role denied
        viewer_token = create_jwt_token(user_id="viewer_bob", role="viewer")
        resp_v = test_client.get(
            "/copilot/audit-log",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp_v.status_code == 403

        # Auditor role allowed
        auditor_token = create_jwt_token(user_id="auditor_dan", role="auditor")
        resp_a = test_client.get(
            "/copilot/audit-log",
            headers={"Authorization": f"Bearer {auditor_token}"},
        )
        assert resp_a.status_code == 200

    def test_public_endpoints_bypass_auth_in_strict_mode(self, test_client, monkeypatch):
        """Liveness and metrics endpoints must not require tokens."""
        monkeypatch.setattr(settings, "JWT_AUTH_REQUIRED", True)

        resp_health = test_client.get("/health")
        assert resp_health.status_code == 200
        assert resp_health.json()["status"] == "healthy"

        resp_metrics = test_client.get("/metrics/fallback")
        assert resp_metrics.status_code == 200
        assert "fallback_rate" in resp_metrics.json()
