from typing import Dict, Any

class DataValidator:
    def __init__(self, rules: Dict[str, Any]):
        self.excluded_users = [u.lower() for u in rules.get("excluded_usernames", [])]

    def is_valid_account(self, account: Dict[str, Any]) -> bool:
        username = account.get("userName", "").strip().lower()
        address = account.get("address", "").strip()

        if not username or not address:
            return False
        if username in self.excluded_users:
            return False
            
        return True
