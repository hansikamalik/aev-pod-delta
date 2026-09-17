from __future__ import annotations

import hashlib
import hmac
import math
import secrets
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from urllib.parse import urlencode, urlparse

from .errors import OAuthError
from .http import HttpClient, UrllibHttpClient
from .id_token import GoogleIdTokenVerifier
from .models import (
    GoogleWorkspaceAuthConfig,
    GoogleWorkspaceConnection,
    OAuthStateStore,
    PendingAuthorization,
    TokenStore,
)

GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_REVOCATION_ENDPOINT = "https://oauth2.googleapis.com/revoke"

# Least privilege for security-event and usage ingestion through Reports API.
GOOGLE_WORKSPACE_SECURITY_SCOPES = (
    "openid",
    "email",
    "https://www.googleapis.com/auth/admin.reports.audit.readonly",
    "https://www.googleapis.com/auth/admin.reports.usage.readonly",
)


class GoogleWorkspaceAuthConnector:
    def __init__(
        self,
        config: GoogleWorkspaceAuthConfig,
        state_store: OAuthStateStore,
        token_store: TokenStore,
        http_client: HttpClient | None = None,
    ) -> None:
        if not config.client_id or not config.client_secret or not config.redirect_uri:
            raise ValueError("Google OAuth client_id, client_secret, and redirect_uri are required.")
        if config.authorization_ttl_seconds <= 0:
            raise ValueError("authorization_ttl_seconds must be positive.")
        _assert_safe_redirect_uri(config.redirect_uri)
        self._config = replace(
            config,
            allowed_workspace_domains=frozenset(
                domain.strip().lower() for domain in config.allowed_workspace_domains if domain.strip()
            ),
        )
        self._states = state_store
        self._tokens = token_store
        self._http = http_client or UrllibHttpClient()
        self._id_tokens = GoogleIdTokenVerifier(self._http)

    def start_authorization(self, session_id: str, login_hint: str | None = None) -> tuple[str, str]:
        """Return `(authorization_url, state)` from an authenticated backend route."""
        if not session_id:
            raise ValueError("A server-side session_id is required.")
        now = _utcnow()
        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)  # RFC 7636: 43-128 chars
        nonce = secrets.token_urlsafe(32)
        self._states.put(
            PendingAuthorization(
                state=state,
                code_verifier=code_verifier,
                nonce=nonce,
                session_id=session_id,
                created_at=now,
                expires_at=now + timedelta(seconds=self._config.authorization_ttl_seconds),
            )
        )
        parameters = {
            "client_id": self._config.client_id,
            "redirect_uri": self._config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(GOOGLE_WORKSPACE_SECURITY_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
            "nonce": nonce,
            "code_challenge": _sha256_base64url(code_verifier),
            "code_challenge_method": "S256",
        }
        if login_hint:
            parameters["login_hint"] = login_hint
        return f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{urlencode(parameters)}", state

    def complete_authorization(
        self, *, code: str, state: str, session_id: str, connection_id: str
    ) -> GoogleWorkspaceConnection:
        """Consume the state, exchange the code, validate identity, and save credentials."""
        pending = self._states.consume(state)
        if pending is None:
            raise OAuthError("Authorization state is invalid or already used.", "invalid_state")
        if pending.expires_at <= _utcnow():
            raise OAuthError("Authorization state has expired.", "expired_state")
        if not _constant_time_equal(pending.session_id, session_id):
            raise OAuthError("Authorization response belongs to another session.", "invalid_session")
        if not code or not connection_id:
            raise OAuthError("Authorization callback is incomplete.", "oauth_provider_error")

        token = self._request_token(
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self._config.redirect_uri,
                "code_verifier": pending.code_verifier,
            }
        )
        connection = self._connection_from_token(connection_id, token, nonce=pending.nonce)
        self._tokens.save(connection)
        return connection

    def get_valid_access_token(self, connection_id: str) -> str:
        """Return a token with at least a one-minute validity margin."""
        existing = self._tokens.get(connection_id)
        if existing is None:
            raise LookupError("Google Workspace connection was not found.")
        if existing.expires_at > _utcnow() + timedelta(minutes=1):
            return existing.access_token
        if not existing.refresh_token:
            raise OAuthError("Google did not grant a refresh token; reconnect the tenant.", "invalid_token_response")
        token = self._request_token(
            {"grant_type": "refresh_token", "refresh_token": existing.refresh_token}
        )
        refreshed = self._connection_from_token(connection_id, token, previous=existing)
        self._tokens.save(refreshed)
        return refreshed.access_token

    def disconnect(self, connection_id: str) -> None:
        """Revoke the Google grant and erase locally encrypted credentials."""
        existing = self._tokens.get(connection_id)
        if existing is None:
            return
        try:
            response = self._http.post_form(
                GOOGLE_REVOCATION_ENDPOINT,
                {"token": existing.refresh_token or existing.access_token},
            )
            if response.status not in (200, 204):
                raise OAuthError("Google could not revoke the authorization grant.", "oauth_provider_error")
        finally:
            # Keeping credentials after a disconnect attempt is more dangerous.
            self._tokens.delete(connection_id)

    def _request_token(self, parameters: Mapping[str, str]) -> Mapping[str, Any]:
        response = self._http.post_form(
            GOOGLE_TOKEN_ENDPOINT,
            {
                **parameters,
                "client_id": self._config.client_id,
                "client_secret": self._config.client_secret,
            },
        )
        try:
            body = response.json()
        except Exception as error:
            raise OAuthError("Google token endpoint did not return JSON.", "oauth_provider_error") from error
        if response.status != 200 or not isinstance(body, dict) or isinstance(body.get("error"), str):
            # Do not add provider text, authorization codes, or tokens to this error.
            raise OAuthError("Google rejected the authorization request.", "oauth_provider_error")
        return body

    def _connection_from_token(
        self,
        connection_id: str,
        token: Mapping[str, Any],
        previous: GoogleWorkspaceConnection | None = None,
        nonce: str | None = None,
    ) -> GoogleWorkspaceConnection:
        access_token = token.get("access_token")
        expires_in = token.get("expires_in")
        if (
            not isinstance(access_token, str)
            or not isinstance(expires_in, (int, float))
            or isinstance(expires_in, bool)
            or not math.isfinite(expires_in)
            or expires_in <= 0
        ):
            raise OAuthError("Google token response is missing required fields.", "invalid_token_response")

        identity = None
        if nonce:
            id_token = token.get("id_token")
            if not isinstance(id_token, str):
                raise OAuthError("Google token response is missing an ID token.", "invalid_token_response")
            identity = self._id_tokens.verify(id_token, self._config.client_id, nonce)
        domain = _email_domain(identity.email) if identity and identity.email_verified else (previous.workspace_domain if previous else None)
        if self._config.allowed_workspace_domains and not domain:
            raise OAuthError("Google did not return a verified Workspace domain.", "unauthorized_domain")
        if domain and self._config.allowed_workspace_domains and domain not in self._config.allowed_workspace_domains:
            raise OAuthError("This Google Workspace domain is not allowed for this connector.", "unauthorized_domain")

        now = _utcnow()
        scope = token.get("scope")
        if nonce and (
            not isinstance(scope, str)
            or not set(GOOGLE_WORKSPACE_SECURITY_SCOPES).issubset(scope.split())
        ):
            raise OAuthError("Google did not grant all required security scopes.", "insufficient_scope")
        return GoogleWorkspaceConnection(
            connection_id=connection_id,
            access_token=access_token,
            refresh_token=token.get("refresh_token") if isinstance(token.get("refresh_token"), str) else (previous.refresh_token if previous else None),
            expires_at=now + timedelta(seconds=expires_in),
            scope=tuple(scope.split()) if isinstance(scope, str) else (previous.scope if previous else ()),
            created_at=previous.created_at if previous else now,
            updated_at=now,
            google_subject=identity.subject if identity else (previous.google_subject if previous else None),
            workspace_domain=domain,
        )


def _assert_safe_redirect_uri(uri: str) -> None:
    parsed = urlparse(uri)
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Google OAuth redirect_uri must include a valid host.")
    if parsed.scheme == "https" and hostname:
        return
    if parsed.scheme == "http" and hostname == "localhost":
        return
    raise ValueError("Google OAuth redirect_uri must use HTTPS (localhost is allowed for development).")


def _constant_time_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)


def _sha256_base64url(value: str) -> str:
    return base64url_encode(hashlib.sha256(value.encode("ascii")).digest())


def base64url_encode(value: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _email_domain(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    local, domain = email.rsplit("@", 1)
    return domain.lower() if local and domain else None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
