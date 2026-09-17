# Google Workspace auth connector (Python)

A server-side Python 3.11+ OAuth 2.0 module for a cybersecurity integration that collects Google Workspace audit and usage data. It uses the authorization-code flow with PKCE and is intentionally separate from any service-account/domain-wide-delegation connector.

## Included protections

- One-time, short-lived opaque state bound to the application's authenticated server-side session.
- PKCE (`S256`) and OIDC nonce validation.
- Signed Google ID-token verification using Google's JWKS, with issuer, audience, expiry, and nonce checks before any domain decision.
- Read-only Google Reports API scopes, optional verified-domain allow-listing, refresh with a one-minute safety margin, and remote revocation.
- Fixed Google endpoints and safe provider errors that omit codes, secrets, and token values.

## Install

```bash
python -m pip install .
```

`cryptography` is required only for the ID-token signature verification and is installed by the package.

## Integrate with your backend

```python
from google_workspace_auth import GoogleWorkspaceAuthConnector, GoogleWorkspaceAuthConfig

connector = GoogleWorkspaceAuthConnector(
    GoogleWorkspaceAuthConfig(
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        redirect_uri="https://security.example.com/integrations/google-workspace/callback",
        allowed_workspace_domains=frozenset({"example.com"}),
    ),
    encrypted_state_store,  # consume(state) must be atomic, e.g. Redis GETDEL
    encrypted_token_store,  # KMS-envelope encryption; never expose tokens to clients
)

# Authenticated GET /integrations/google-workspace/connect
authorization_url, _ = connector.start_authorization(request.session.id)
return redirect(authorization_url)

# GET /integrations/google-workspace/callback
connection = connector.complete_authorization(
    code=request.args["code"],
    state=request.args["state"],
    session_id=request.session.id,
    connection_id=tenant.id,  # server-generated and tenant-authorized
)
```

Register the exact HTTPS callback URI in Google Cloud and restrict production egress to `accounts.google.com`, `oauth2.googleapis.com`, and `www.googleapis.com`.

## Production requirements

1. Configure and publish the Google OAuth consent screen with the requested Reports API scopes. The authorizing user needs the relevant Workspace administrator privileges.
2. Implement `OAuthStateStore` with a TTL plus atomic read/delete, and `TokenStore` with KMS-backed encryption, tenant authorization, and credential-redacted logging.
3. Create the `connection_id` server-side; do not take it directly from a browser request. Rate-limit the callback and refresh routes.
4. Audit connection, refresh, and disconnect actions without logging authorization codes, access tokens, refresh tokens, or client secrets.
5. Use a separate, deliberately reviewed service-account/domain-wide-delegation implementation if interactive administrator consent does not meet the product's collection model.
