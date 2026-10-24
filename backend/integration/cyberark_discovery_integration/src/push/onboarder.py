from typing import List, Dict, Any
from src.push.cyberark_client import CyberArkClient
from src.utils.logger import get_logger

logger = get_logger("Onboarder")

class Onboarder:
    def __init__(self, client: CyberArkClient):
        self.client = client

    def bulk_push(self, accounts: List[Dict[str, Any]]) -> Dict[str, int]:
        results = {"success": 0, "failed": 0}
        for account in accounts:
            success = self.client.push_discovered_account(account)
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1
                logger.error(f"Failed pushing account: {account['userName']}@{account['address']}")
        return results
