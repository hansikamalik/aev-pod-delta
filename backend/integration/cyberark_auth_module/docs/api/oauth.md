---

## `docs/api/oauth.md`
```markdown
# API Reference: OAuth2Authenticator

Handles OAuth2 Client Credentials Grant authentication against CyberArk Identity Platform.

## Constructor

```python
OAuth2Authenticator(
    base_url: str,
    client_id: str,
    client_secret: str,
    scope: str = "oauthcustomscope"
)
