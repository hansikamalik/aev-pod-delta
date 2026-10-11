import re
from typing import List, Dict, Any

class VaultAuditChecker:
    """Detects unredacted raw credentials in log outputs or test traces."""

    def __init__(self, blacklist_tokens: List[str]):
        self.blacklist_tokens = blacklist_tokens

    def inspect_unredacted_secrets(self, text: str) -> Dict[str, Any]:
        found_leaks = []
        for token in self.blacklist_tokens:
            # Pattern matches key=value or "key": "value" where value isn't REDACTED
            pattern = re.compile(rf'["\']?{token}["\']?\s*[:=]\s*["\']?(?!\s*\[REDACTED)([^"\'\s,}}]+)', re.IGNORECASE)
            matches = pattern.findall(text)
            if matches:
                # Exclude assertion statements in code lines
                real_leaks = [m for m in matches if not m.startswith("==") and "assert" not in m]
                if real_leaks:
                    found_leaks.append({"token_key": token, "sample": real_leaks[0][:4] + "****"})

        return {
            "has_leak": len(found_leaks) > 0,
            "leaked_tokens": found_leaks
        }
