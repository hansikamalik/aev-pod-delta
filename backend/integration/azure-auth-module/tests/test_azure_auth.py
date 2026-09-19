"""
Unit tests for the Azure Authentication & Credentials module.
Run with: pytest tests/ -v
"""

import time
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from azure_auth import (
    AzureCredentials,
    EnvCredentialProvider,
    InvalidCredentialsError,
    CredentialValidationError,
    ThrottledError,
    TokenExpiredError,
    Token,
    TokenManager,
    ServicePrincipalAuthenticator,
    MockAzureAuthenticator,
)


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

class TestAzureCredentials:
    def test_valid_credentials_pass_shape_check(self):
        creds = AzureCredentials(
            tenant_id="t1", client_id="c1", client_secret="s1"
        )
        creds.validate_shape()  # should not raise

    def test_missing_field_raises(self):
        creds = AzureCredentials(tenant_id="", client_id="c1", client_secret="s1")
        with pytest.raises(InvalidCredentialsError):
            creds.validate_shape()

    def test_missing_multiple_fields_lists_all(self):
        creds = AzureCredentials(tenant_id="", client_id="", client_secret="s1")
        with pytest.raises(InvalidCredentialsError) as exc:
            creds.validate_shape()
        assert "tenant_id" in str(exc.value)
        assert "client_id" in str(exc.value)


class TestEnvCredentialProvider:
    def test_reads_from_environment(self, monkeypatch):
        monkeypatch.setenv("AZURE_TENANT_ID", "tenant-x")
        monkeypatch.setenv("AZURE_CLIENT_ID", "client-x")
        monkeypatch.setenv("AZURE_CLIENT_SECRET", "secret-x")
        creds = EnvCredentialProvider().get_credentials()
        assert creds.tenant_id == "tenant-x"
        assert creds.client_id == "client-x"
        assert creds.client_secret == "secret-x"

    def test_missing_env_vars_raises(self, monkeypatch):
        monkeypatch.delenv("AZURE_TENANT_ID", raising=False)
        monkeypatch.delenv("AZURE_CLIENT_ID", raising=False)
        monkeypatch.delenv("AZURE_CLIENT_SECRET", raising=False)
        with pytest.raises(InvalidCredentialsError):
            EnvCredentialProvider().get_credentials()


# ---------------------------------------------------------------------------
# Token manager
# ---------------------------------------------------------------------------

class TestTokenManager:
    def test_fetches_token_on_first_call(self):
        calls = {"count": 0}

        def fetch():
            calls["count"] += 1
            return Token(access_token="tok", expires_at=time.time() + 3600)

        mgr = TokenManager(fetch_fn=fetch)
        token = mgr.get_token()
        assert token.access_token == "tok"
        assert calls["count"] == 1

    def test_caches_token_on_second_call(self):
        calls = {"count": 0}

        def fetch():
            calls["count"] += 1
            return Token(access_token="tok", expires_at=time.time() + 3600)

        mgr = TokenManager(fetch_fn=fetch)
        mgr.get_token()
        mgr.get_token()
        assert calls["count"] == 1

    def test_refreshes_when_expired(self):
        calls = {"count": 0}

        def fetch():
            calls["count"] += 1
            return Token(access_token=f"tok-{calls['count']}", expires_at=time.time() - 1)

        mgr = TokenManager(fetch_fn=fetch)
        mgr.get_token()
        mgr.get_token()
        assert calls["count"] == 2

    def test_force_refresh_bypasses_cache(self):
        calls = {"count": 0}

        def fetch():
            calls["count"] += 1
            return Token(access_token="tok", expires_at=time.time() + 3600)

        mgr = TokenManager(fetch_fn=fetch)
        mgr.get_token()
        mgr.get_token(force_refresh=True)
        assert calls["count"] == 2

    def test_invalidate_clears_cache(self):
        calls = {"count": 0}

        def fetch():
            calls["count"] += 1
            return Token(access_token="tok", expires_at=time.time() + 3600)

        mgr = TokenManager(fetch_fn=fetch)
        mgr.get_token()
        mgr.invalidate()
        assert mgr.peek() is None

    def test_assert_not_expired_raises_on_expired_token(self):
        expired = Token(access_token="tok", expires_at=time.time() - 100)
        with pytest.raises(TokenExpiredError):
            TokenManager.assert_not_expired(expired)


# ---------------------------------------------------------------------------
# ServicePrincipalAuthenticator (real implementation, error paths only —
# live Azure calls are out of scope for unit tests)
# ---------------------------------------------------------------------------

class _FakeProvider:
    def __init__(self, creds):
        self._creds = creds

    def get_credentials(self):
        return self._creds


class TestServicePrincipalAuthenticator:
    def test_raises_on_invalid_credential_shape(self):
        provider = _FakeProvider(AzureCredentials(tenant_id="", client_id="", client_secret=""))
        authenticator = ServicePrincipalAuthenticator(provider)
        with pytest.raises(InvalidCredentialsError):
            authenticator.validate_credentials()

    def test_is_authenticated_false_before_any_token(self):
        provider = _FakeProvider(AzureCredentials("t", "c", "s"))
        authenticator = ServicePrincipalAuthenticator(provider)
        assert authenticator.is_authenticated() is False


# ---------------------------------------------------------------------------
# MockAzureAuthenticator — this is what Subramani / Ashwin / Bhawook use
# ---------------------------------------------------------------------------

class TestMockAzureAuthenticator:
    def test_default_mock_succeeds(self):
        auth = MockAzureAuthenticator()
        assert auth.validate_credentials() is True
        token = auth.get_token()
        assert token.access_token == "mock-access-token"

    def test_is_authenticated_after_token_fetch(self):
        auth = MockAzureAuthenticator()
        auth.get_token()
        assert auth.is_authenticated() is True

    def test_should_fail_raises_credential_validation_error(self):
        auth = MockAzureAuthenticator(should_fail=True)
        with pytest.raises(CredentialValidationError):
            auth.validate_credentials()

    def test_should_throttle_raises_throttled_error(self):
        auth = MockAzureAuthenticator(should_throttle=True)
        with pytest.raises(ThrottledError):
            auth.validate_credentials()

    def test_custom_fake_token_and_ttl(self):
        auth = MockAzureAuthenticator(fake_token="custom-tok", token_ttl_seconds=10)
        token = auth.get_token()
        assert token.access_token == "custom-tok"
        assert not token.is_expired(skew=0)
