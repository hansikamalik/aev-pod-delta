from typing import List, Dict, Any
from src.normalization.validator import DataValidator
from src.utils.logger import get_logger

logger = get_logger("Transformer")

class Normalizer:
    def __init__(self, rules: Dict[str, Any]):
        self.rules = rules
        self.validator = DataValidator(rules)
        self.platform_mappings = rules.get("platform_mappings", {})
        self.default_platform = rules.get("default_platform", "GenericPlatform")

    def transform_single(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        username = raw_data.get("raw_username", "").strip().lower()
        address = raw_data.get("host", "").strip().lower()
        os_type = raw_data.get("os_type", "")

        platform_id = self.platform_mappings.get(os_type, self.default_platform)

        return {
            "userName": username,
            "address": address,
            "platformId": platform_id,
            "accountType": "Local",
            "customProperties": {
                "IPAddress": raw_data.get("ip", ""),
                "DiscoveredOSType": os_type
            }
        }

    def process(self, raw_accounts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized_list = []
        for raw in raw_accounts:
            transformed = self.transform_single(raw)
            if self.validator.is_valid_account(transformed):
                normalized_list.append(transformed)
            else:
                logger.warning(
                    f"Account excluded by validation policy: {transformed['userName']}@{transformed['address']}"
                )
        return normalized_list
