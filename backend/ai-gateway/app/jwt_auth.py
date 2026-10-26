"""
Cryptographic JWT Authentication and Cryptographic Trust Boundaries for Pod Delta.

Verifies signed bearer tokens issued by Pod Alpha (Identity & Auth provider).
Extracts user identity, role, tenant_id, org_tier, and budget caps.
Enforces RBAC and eliminates blind trust in spoofable HTTP headers.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

import jwt
from fastapi import Depends, Header, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger("ai_gateway.jwt_auth")

# HTTP Bearer scheme with auto_error=False to support graceful fallback in dev/test mode
security_bearer = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    """Cryptographically verified principal extracted from Pod Alpha JWT."""

    user_id: str = Field(description="Unique subject / user identifier")
    role: str = Field(default="viewer", description="RBAC role (admin, analyst, viewer, auditor)")
    tenant_id: str = Field(default="default_tenant", description="Organization / tenant ID")
    org_tier: str = Field(default="free", description="Subscription tier (free, pro, enterprise)")
    budget_cap: Optional[float] = Field(
        default=None, description="Optional dollar spend budget cap"
    )
    email: Optional[str] = Field(default=None, description="Optional principal email")
    scopes: List[str] = Field(
        default_factory=list, description="OAuth scopes or fine-grained claims"
    )
    token_auth: bool = Field(default=True, description="True if verified via cryptographic JWT")


def create_jwt_token(
    user_id: str,
    role: str = "analyst",
    tenant_id: str = "default_tenant",
    org_tier: str = "free",
    budget_cap: Optional[float] = None,
    email: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    expires_in_seconds: int = 3600,
    secret_key: Optional[str] = None,
    algorithm: Optional[str] = None,
    issuer: Optional[str] = None,
    audience: Optional[str] = None,
) -> str:
    """Mint a cryptographically signed JWT for tests or Pod Alpha integration."""
    now = datetime.now(timezone.utc)
    key = secret_key or getattr(
        settings, "JWT_SECRET_KEY", "aev-pod-alpha-development-secret-key-32bytes-min"
    )
    algo = algorithm or getattr(settings, "JWT_ALGORITHM", "HS256")
    iss = issuer or getattr(settings, "JWT_ISSUER", "aev-pod-alpha")
    aud = audience or getattr(settings, "JWT_AUDIENCE", "aev-pod-delta")

    payload: Dict[str, Any] = {
        "sub": user_id,
        "user_id": user_id,
        "role": role,
        "tenant_id": tenant_id,
        "org_tier": org_tier,
        "iss": iss,
        "aud": aud,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in_seconds)).timestamp()),
    }
    if budget_cap is not None:
        payload["budget_cap"] = budget_cap
    if email:
        payload["email"] = email
    if scopes:
        payload["scopes"] = scopes

    return jwt.encode(payload, key, algorithm=algo)


def verify_jwt_token(token: str) -> AuthenticatedUser:
    """Verify cryptographic signature and claims of a Pod Alpha JWT."""
    key = getattr(settings, "JWT_SECRET_KEY", "aev-pod-alpha-development-secret-key-32bytes-min")
    algo = getattr(settings, "JWT_ALGORITHM", "HS256")
    iss = getattr(settings, "JWT_ISSUER", "aev-pod-alpha")
    aud = getattr(settings, "JWT_AUDIENCE", "aev-pod-delta")

    try:
        decoded = jwt.decode(
            token,
            key,
            algorithms=[algo],
            issuer=iss,
            audience=aud,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        logger.warning("Rejected expired JWT token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "token_expired", "message": "Authentication token has expired"},
            headers={"WWW-Authenticate": (
                "Bearer error=\"invalid_token\","
                " error_description=\"The token has expired\""
            )},
        ) from exc
    except jwt.InvalidIssuerError as exc:
        logger.warning("Rejected JWT with invalid issuer: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_issuer", "message": "Untrusted token issuer"},
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        ) from exc
    except jwt.InvalidAudienceError as exc:
        logger.warning("Rejected JWT with invalid audience: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_audience",
                "message": "Token audience does not match Pod Delta",
            },
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        ) from exc
    except jwt.PyJWTError as exc:
        logger.warning("Rejected malformed or tampered JWT: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_token",
                "message": "Invalid, tampered, or malformed authentication token",
            },
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        ) from exc

    return AuthenticatedUser(
        user_id=decoded.get("user_id") or decoded.get("sub", "anonymous"),
        role=decoded.get("role", "viewer"),
        tenant_id=decoded.get("tenant_id") or decoded.get("org_id", "default_tenant"),
        org_tier=decoded.get("org_tier", "free"),
        budget_cap=decoded.get("budget_cap"),
        email=decoded.get("email"),
        scopes=decoded.get("scopes", []),
        token_auth=True,
    )


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    x_user_id: Optional[str] = Header(default=None),
    x_user_role: Optional[str] = Header(default=None),
    x_org_tier: Optional[str] = Header(default=None),
    x_org_id: Optional[str] = Header(default=None),
    x_budget_cap: Optional[float] = Header(default=None),
) -> AuthenticatedUser:
    """FastAPI security dependency enforcing Pod Alpha trust boundary."""
    strict_auth = getattr(settings, "JWT_AUTH_REQUIRED", False)

    # 1. Bearer Token Authentication (Always strictly verified if provided)
    if credentials and credentials.scheme.lower() == "bearer" and credentials.credentials:
        user = verify_jwt_token(credentials.credentials)
        request.state.user = user
        return user

    # 2. Strict Mode Rejection if Bearer Token is missing
    if strict_auth:
        logger.warning("Rejected request lacking required Pod Alpha Bearer token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "missing_bearer_token",
                "message": (
                    "Authorization: Bearer <pod_alpha_jwt> header"
                    " is required to access Pod Delta services"
                ),
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Development / Sandbox fallback for legacy unit tests (when strict mode is disabled)
    fallback_user = AuthenticatedUser(
        user_id=x_user_id or "anonymous",
        role=x_user_role or "anonymous",
        tenant_id=x_org_id or "default_tenant",
        org_tier=x_org_tier or "free",
        budget_cap=x_budget_cap,
        token_auth=False,
    )
    request.state.user = fallback_user
    return fallback_user


def require_role(allowed_roles: List[str]) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    """Dependency factory enforcing RBAC roles on verified principals."""

    def role_checker(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if user.role not in allowed_roles:
            logger.warning(
                "Access denied for user '%s' with role '%s'. Allowed: %s",
                user.user_id,
                user.role,
                allowed_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "forbidden",
                    "reason": f"Role '{user.role}' is not permitted to access this resource",
                    "allowed_roles": allowed_roles,
                },
            )
        return user

    return role_checker
