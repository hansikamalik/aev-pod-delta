import time
import requests
from typing import Dict, Optional
from src.exceptions import CyberArkAuthError


class CyberArkAuthManager:
    """Manages session-based REST API authentication with CyberArk PVWA."""

    def __init__(self, pas_url: str, verify_ssl: bool = True, timeout: int = 10):
        self.pas_url = pas_url.rstrip("/")
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.session = requests.Session()
        
        self._auth_token: Optional[str] = None
        self._token_expiry: float = 0.0
        self._last_username: Optional[str] = None
        self._last_password: Optional[str] = None
        self._last_use_radius: bool = False

    def authenticate(self, username: str, password: str, use_radius: bool = False) -> str:
        """Logs into PVWA via standard or RADIUS authentication endpoints."""
        endpoint = "/PasswordVault/API/Auth/Radius/Logon" if use_radius else "/PasswordVault/API/Auth/CyberArk/Logon"
        url = f"{self.pas_url}{endpoint}"
        payload = {"username": username, "password": password, "concurrentSession": True}

        try:
            resp = self.session.post(url, json=payload, verify=self.verify_ssl, timeout=self.timeout)
            if resp.status_code != 200:
                raise CyberArkAuthError(f"Auth failed [HTTP {resp.status_code}]: {resp.text}")

            self._auth_token = resp.json() if isinstance(resp.json(), str) else resp.text.strip('"')
            self._token_expiry = time.time() + (25 * 60)
            self._last_username = username
            self._last_password = password
            self._last_use_radius = use_radius
            return self._auth_token

        except requests.RequestException as exc:
            raise CyberArkAuthError(f"Network error during authentication: {str(exc)}") from exc

    def get_auth_headers(self) -> Dict[str, str]:
        """Returns HTTP headers populated with the active session token."""
        if not self._auth_token or time.time() >= self._token_expiry:
            raise CyberArkAuthError("No active or valid authentication token available.")
        return {"Authorization": self._auth_token, "Content-Type": "application/json"}

    def logoff(self) -> bool:
        """Terminates the active session with PVWA."""
        if not self._auth_token:
            return True
        url = f"{self.pas_url}/PasswordVault/API/Auth/Logoff"
        try:
            resp = self.session.post(url, headers=self.get_auth_headers(), verify=self.verify_ssl, timeout=self.timeout)
            self._auth_token = None
            return resp.status_code == 200
        except requests.RequestException:
            return False
