# Pod Alpha $\leftrightarrow$ Pod Delta: Cryptographic Trust Boundary Contract (P1-1)

> **Document Status:** Active Engineering Specification  
> **Applicable Pods:** Pod Alpha (Identity & Access) & Pod Delta (Module 4 AI & Integrations)  
> **Protocol:** JSON Web Tokens (RFC 7519) via OAuth2 Bearer Authentication (RFC 6750)

---

## 1. Executive Summary

Pod Delta services (`ai-gateway`, `integration-service`, `ai-context`) operate behind a cryptographic trust boundary. Raw HTTP header-based identity assertion (`X-User-ID`, `X-User-Role`) is deprecated. Every inbound request originating from outside Pod Delta must carry a signed JSON Web Token (JWT) issued by Pod Alpha.

---

## 2. Inbound Authorization Format

All protected endpoints require an `Authorization` header containing an signed bearer token:

```http
Authorization: Bearer <pod_alpha_signed_jwt>
```

Requests lacking this header in strict production mode will be rejected immediately:
```json
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer

{
  "detail": {
    "error": "missing_bearer_token",
    "message": "Authorization: Bearer <pod_alpha_jwt> header is required to access Pod Delta services"
  }
}
```

---

## 3. Supported Signing Algorithms & Keys

Pod Delta supports both symmetric staging and asymmetric production verification:

| Environment | Algorithm | Verification Key Configuration | Notes |
| :--- | :--- | :--- | :--- |
| **Staging / Dev** | `HS256` | Shared secret `JWT_SECRET_KEY` (minimum 256 bits) | Fast local development |
| **Production** | `RS256` | Pod Alpha Public Key (PEM) or JWKS endpoint | Zero-knowledge secret sharing |

---

## 4. Token Payload Claims Schema

Pod Alpha must mint JWT tokens conforming to the following JSON schema:

```json
{
  "sub": "usr_99812_sarah_analyst",
  "user_id": "sarah_analyst",
  "role": "analyst",
  "tenant_id": "org_fintech_corp",
  "org_tier": "enterprise",
  "budget_cap": 2500.00,
  "email": "sarah@fintech.example.com",
  "scopes": ["copilot:query", "audit:read", "integrations:sync"],
  "iss": "aev-pod-alpha",
  "aud": "aev-pod-delta",
  "iat": 1730000000,
  "nbf": 1730000000,
  "exp": 1730003600
}
```

### Required Standard Claims
* `iss` *(Issuer)*: Must match `aev-pod-alpha` (configurable via `JWT_ISSUER`).
* `aud` *(Audience)*: Must match `aev-pod-delta` (configurable via `JWT_AUDIENCE`).
* `sub` *(Subject)*: Unique user identifier for token tracking and rate limiting.
* `exp` *(Expiration)*: Unix timestamp in seconds; token must be refreshed before expiry.
* `nbf` *(Not Before)*: Unix timestamp before which token is invalid.

### Required Custom Claims
* `role` *(String)*: RBAC role assigned to the user. Valid values:
  * `admin`: Complete platform control (cleanup, policy overrides, all tools).
  * `analyst`: Standard security engineer (tool execution, citation flagging, workflow runs).
  * `auditor`: Compliance and governance (audit log reading, report access).
  * `viewer`: Read-only basic queries without sensitive tool invocations.
* `tenant_id` *(String)*: Organization / tenant ID for strict multi-tenant database vector isolation.
* `org_tier` *(String)*: Subscription tier determining rate limits (`free`, `pro`, `enterprise`).
* `budget_cap` *(Float, Optional)*: Optional maximum dollar limit for dynamic LLM spend.

---

## 5. Security Enforcements & Error Matrix

| Condition | HTTP Status | Response Payload |
| :--- | :---: | :--- |
| Token missing in strict mode | `401 Unauthorized` | `{"error": "missing_bearer_token"}` |
| Token expired (`exp` < now) | `401 Unauthorized` | `{"error": "token_expired"}` |
| Tampered signature or invalid secret | `401 Unauthorized` | `{"error": "invalid_token"}` |
| Untrusted issuer (`iss` mismatch) | `401 Unauthorized` | `{"error": "invalid_issuer"}` |
| Wrong audience (`aud` mismatch) | `401 Unauthorized` | `{"error": "invalid_audience"}` |
| User role not allowed for endpoint | `403 Forbidden` | `{"error": "forbidden", "reason": "Role 'viewer' is not permitted..."}` |

---

## 6. Endpoints Exempt from Authentication

The following endpoints do not require Bearer tokens to facilitate Kubernetes health probes and reverse proxy telemetry:
* `GET /health`
* `GET /metrics/fallback`
* `GET /docs`
* `GET /openapi.json`
