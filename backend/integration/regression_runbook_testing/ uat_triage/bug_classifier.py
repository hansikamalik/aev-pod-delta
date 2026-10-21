class BugClassifier:
    """Classifies incoming UAT bug reports into strict enterprise severity tiers."""

    @staticmethod
    def classify(error_message: str, affected_connectors_count: int) -> str:
        # Check for credential leakage or systemic multi-connector failures
        if "vault_token_" in error_message or "TokenLeak" in error_message or affected_connectors_count > 5:
            return "Sev-1 (Critical)"
        # Check for checkpoint or connection failures affecting a single connector
        elif "Checkpoint" in error_message or "ConnectionRefused" in error_message or affected_connectors_count == 1:
            return "Sev-2 (Major)"
        # Check for rate limiting or timeouts
        elif "Timeout" in error_message or "RateLimit" in error_message or "429" in error_message:
            return "Sev-3 (Moderate)"
        
        return "Sev-4 (Low)"
