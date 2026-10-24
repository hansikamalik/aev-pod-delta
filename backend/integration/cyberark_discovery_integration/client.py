from typing import Dict, Any, List
import requests


class CyberArkClient:
    """REST Client wrapper for discovering CyberArk resources."""

    def __init__(self, auth_module, base_url: str, verify_tls: bool = True):
        self.auth = auth_module
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.verify_tls = verify_tls

    def list_accounts(self) -> List[Dict[str, Any]]:
        headers = self.auth.get_auth_header()
        url = f"{self.base_url}/PasswordVault/API/Accounts"
        resp = requests.get(url, headers=headers, verify=self.verify_tls)
        if resp.status_code == 200:
            return resp.json().get("value", [])
        return []

    def list_safes(self) -> List[Dict[str, Any]]:
        headers = self.auth.get_auth_header()
        url = f"{self.base_url}/PasswordVault/API/Safes"
        resp = requests.get(url, headers=headers, verify=self.verify_tls)
        if resp.status_code == 200:
            return resp.json().get("value", [])
        return []
