import os
import requests
import hvac
import logging
import requests_mock
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CyberArkToVaultMigrator")

CYBERARK_PVWA_URL = os.getenv("CYBERARK_PVWA_URL", "https://pvwa.company.local/PasswordVault")
CYBERARK_USER = os.getenv("CYBERARK_USER", "VaultAdmin")
CYBERARK_PASS = os.getenv("CYBERARK_PASS", "CyberArkPassword123!")

VAULT_ADDR = os.getenv("VAULT_ADDR", "http://127.0.0.1:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "")
VAULT_KV_MOUNT = os.getenv("VAULT_KV_MOUNT", "secret")
MOCK_CYBERARK = os.getenv("MOCK_CYBERARK", "true").lower() == "true"

requests.packages.urllib3.disable_warnings()


class CyberArkToVaultMigrator:
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        self.cyberark_token: Optional[str] = None
        self.vault_client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN, verify=False)

        if MOCK_CYBERARK:
            logger.info("Initializing Mock CyberArk API Endpoints for Local Testing...")
            self.adapter = requests_mock.Adapter()
            self.session.mount("https://", self.adapter)
            self.session.mount("http://", self.adapter)
            self._setup_mock_routes()

    def _setup_mock_routes(self):
        # 1. Mock Logon
        self.adapter.register_uri(
            "POST", f"{CYBERARK_PVWA_URL}/api/auth/Logon",
            text='"mocked_session_token_998877"'
        )
        # 2. Mock Accounts Retrieval
        for safe in ["Linux-Enterprise-Safe", "Windows-Server-Safe", "Database-Credentials-Safe"]:
            self.adapter.register_uri(
                "GET", f"{CYBERARK_PVWA_URL}/api/Accounts?filter=safeName eq {safe}",
                json={"value": [
                    {"id": f"{safe}_101", "userName": "root", "address": "srv-db01.local", "platformId": "UnixSSH"},
                    {"id": f"{safe}_102", "userName": "admin", "address": "app-web01.local", "platformId": "WinServer"}
                ]}
            )
        # 3. Mock Password Retrieval
        self.adapter.register_uri(
            "POST", requests_mock.ANY,
            text='"MigratedSuperSecret123!"'
        )

    def cyberark_login(self) -> None:
        url = f"{CYBERARK_PVWA_URL}/api/auth/Logon"
        payload = {"username": CYBERARK_USER, "password": CYBERARK_PASS}
        response = self.session.post(url, json=payload, timeout=10)
        response.raise_for_status()
        self.cyberark_token = response.text.strip('"')
        self.session.headers.update({"Authorization": self.cyberark_token})
        logger.info("Authenticated successfully with CyberArk PVWA.")

    def get_cyberark_accounts(self, safe_name: str) -> List[Dict[str, Any]]:
        url = f"{CYBERARK_PVWA_URL}/api/Accounts?filter=safeName eq {safe_name}"
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        return response.json().get("value", [])

    def retrieve_account_password(self, account_id: str) -> Optional[str]:
        url = f"{CYBERARK_PVWA_URL}/api/Accounts/{account_id}/Password/Retrieve"
        payload = {"Reason": "Migration to HashiCorp Vault KV v2"}
        response = self.session.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return response.text.strip('"')
        logger.error(f"Failed retrieving credential for Account ID {account_id}: {response.text}")
        return None

    def migrate_safe(self, safe_name: str) -> Dict[str, int]:
        accounts = self.get_cyberark_accounts(safe_name)
        logger.info(f"Discovered {len(accounts)} accounts in CyberArk Safe: '{safe_name}'.")

        stats = {"success": 0, "failed": 0}

        for acc in accounts:
            account_id = acc.get("id")
            username = acc.get("userName")
            address = acc.get("address", "global")
            platform_id = acc.get("platformId")

            password = self.retrieve_account_password(account_id)
            if not password:
                stats["failed"] += 1
                continue

            vault_path = f"cyberark_migrated/{safe_name.lower()}/{address.lower()}/{username.lower()}"

            secret_payload = {
                "username": username,
                "password": password,
                "address": address,
                "platform_id": platform_id,
                "cyberark_account_id": account_id,
                "origin_safe": safe_name
            }

            try:
                self.vault_client.secrets.kv.v2.create_or_update_secret(
                    mount_point=VAULT_KV_MOUNT,
                    path=vault_path,
                    secret=secret_payload
                )
                logger.info(f"[SUCCESS] Migrated {username}@{address} -> Vault: {VAULT_KV_MOUNT}/data/{vault_path}")
                stats["success"] += 1
            except Exception as e:
                logger.error(f"[FAILURE] Vault write failed for {username}@{address}: {str(e)}")
                stats["failed"] += 1

        return stats


if __name__ == "__main__":
    migrator = CyberArkToVaultMigrator()
    migrator.cyberark_login()

    SAFES_TO_MIGRATE = [
        "Linux-Enterprise-Safe",
        "Windows-Server-Safe",
        "Database-Credentials-Safe"
    ]

    for safe in SAFES_TO_MIGRATE:
        summary = migrator.migrate_safe(safe)
        logger.info(f"Migration Summary for '{safe}': Success={summary['success']}, Failed={summary['failed']}")
