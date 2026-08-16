from typing import Any, Dict


class TokenTracker:
    """Extract token usage information from an AI model response."""

    @staticmethod
    def extract_usage(response: Any) -> Dict[str, int]:
        """
        Extract prompt, completion, and total token counts.

        Supports:
        - Gemini usage_metadata
        - OpenAI usage
        - Normalized gateway dictionaries
        """

        if isinstance(response, dict):
            usage = response.get("usage", response)

            return {
                "prompt_tokens": int(
                    usage.get("prompt_tokens", 0) or 0
                ),
                "completion_tokens": int(
                    usage.get("completion_tokens", 0) or 0
                ),
                "total_tokens": int(
                    usage.get("total_tokens", 0) or 0
                ),
            }

        usage = getattr(response, "usage_metadata", None)

        if usage is None:
            usage = getattr(response, "usage", None)

        if usage is None:
            return {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }

        prompt_tokens = getattr(
            usage,
            "prompt_token_count",
            getattr(usage, "prompt_tokens", 0),
        )

        completion_tokens = getattr(
            usage,
            "candidates_token_count",
            getattr(usage, "completion_tokens", 0),
        )

        total_tokens = getattr(
            usage,
            "total_token_count",
            getattr(usage, "total_tokens", 0),
        )

        return {
            "prompt_tokens": int(prompt_tokens or 0),
            "completion_tokens": int(completion_tokens or 0),
            "total_tokens": int(total_tokens or 0),
        }
