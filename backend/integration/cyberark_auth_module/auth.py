from typing import Dict, Any
import requests


class CyberArkAuthModule:
    """Authentication client module for CyberArk REST API session handling."""

    def __init__(self, base_url: str, verify_tls: bool = True):
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.verify_tls = verify_tls
        self.session_token: str = ""

    def authenticate(self, credentials: Dict[str, Any]) -> str:
        url = f"{self.base_url}/PasswordVault/API/auth/Cyberark/Logon"
        payload = {
            "username": credentials.get("username"),
            "password": credentials.get("password"),
        }

        response = requests.post(
            url, json=payload, verify=self.verify_tls, timeout=10
        )
        response.raise_for_status()

        self.session_token = response.json()
        return self.session_token

    def get_auth_header(self) -> Dict[str, str]:
        if not self.session_token:
            raise ValueError("Client is not authenticated with CyberArk.")
        return {
            "Authorization": self.session_token,
            "Content-Type": "application/json",
        }
