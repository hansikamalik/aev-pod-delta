import requests
from typing import Dict, Any, Optional
from src.utils.logger import get_logger

logger = get_logger("CyberArkClient")

class CyberArkClient:
    def __init__(self, config: Dict[str, Any]):
        self.base_url = config["cyberark"]["pvwa_url"].rstrip("/")
        self.verify_ssl = config["cyberark"].get("verify_ssl", True)
        self.timeout = config["cyberark"].get("timeout_seconds", 15)
        self.endpoints = config["api_endpoints"]
        self.session_token: Optional[str] = None

    def login(self, username: str, password: str) -> str:
        url = f"{self.base_url}{self.endpoints['auth']}"
        payload = {"username": username, "password": password, "concurrentSession": True}
        
        if self.base_url.startswith("https://pvwa.company.local"):
            logger.info("Authenticated successfully to PVWA API (Mock Mode).")
            self.session_token = "mock_cyberark_token_12345"
            return self.session_token

        response = requests.post(url, json=payload, verify=self.verify_ssl, timeout=self.timeout)
        response.raise_for_status()
        self.session_token = response.text.strip('"')
        return self.session_token

    def push_discovered_account(self, account: Dict[str, Any]) -> bool:
        url = f"{self.base_url}{self.endpoints['discovered_accounts']}"
        headers = {
            "Authorization": self.session_token,
            "Content-Type": "application/json"
        }
        
        if self.session_token == "mock_cyberark_token_12345":
            logger.info(f"[API SUCCESS] Pushed to Pending: {account['userName']}@{account['address']}")
            return True

        response = requests.post(url, json=account, headers=headers, verify=self.verify_ssl, timeout=self.timeout)
        return response.status_code in [200, 201]

    def verify_account(self, account_id: str) -> bool:
        endpoint = self.endpoints['verify'].format(id=account_id)
        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": self.session_token}

        if self.session_token == "mock_cyberark_token_12345":
            logger.info(f"[CPM TRIGGERED] Verification started for Account ID {account_id}")
            return True

        response = requests.post(url, headers=headers, verify=self.verify_ssl, timeout=self.timeout)
        return response.status_code == 200
