import time
import requests
from typing import Dict, Any, Optional
from src.exceptions import CyberArkAuthError


class CyberArkIdentityOAuthClient:
    """Handles OAuth2 Client Credentials authentication flow for CyberArk Identity Cloud."""

    def __init__(
        self,
        tenant_url: str,
        client_id: str,
        client_secret: str,
        token_endpoint_path: str = "/oauth2/token",
        verify_ssl: bool = True,
        timeout: int = 10
    ):
        self.tenant_url = tenant_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_endpoint = f"{self.tenant_url}{token_endpoint_path}"
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        
        self._access_token: Optional[str] = None
        self._token_type: str = "Bearer"
        self._expires_at: float = 0.0

    def get_token(self, scope: Optional[str] = None, force_refresh: bool = False) -> str:
        """Fetches a valid Bearer token. Reuses cached tokens until expiry."""
        if self._access_token and time.time() < (self._expires_at - 30) and not force_refresh:
            return self._access_token

        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        if scope:
            payload["scope"] = scope

        try:
            response = requests.post(
                self.token_endpoint,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            if response.status_code != 200:
                raise CyberArkAuthError(f"OAuth2 Auth failed [HTTP {response.status_code}]: {response.text}")

            data: Dict[str, Any] = response.json()
            self._access_token = data.get("access_token")
            self._token_type = data.get("token_type", "Bearer")
            expires_in = data.get("expires_in", 3600)
            self._expires_at = time.time() + float(expires_in)

            if not self._access_token:
                raise CyberArkAuthError("OAuth2 response did not contain an 'access_token'.")

            return self._access_token

        except requests.RequestException as exc:
            raise CyberArkAuthError(f"Network error during OAuth2 authentication: {str(exc)}") from exc

    def get_auth_headers(self, scope: Optional[str] = None) -> Dict[str, str]:
        """Returns ready-to-use headers containing the Bearer token."""
        token = self.get_token(scope=scope)
        return {
            "Authorization": f"{self._token_type} {token}",
            "Content-Type": "application/json"
        }
