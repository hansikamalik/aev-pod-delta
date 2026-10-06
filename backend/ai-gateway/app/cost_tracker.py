"""AI model cost calculation and budget-cap enforcement."""

from typing import Any, Dict, Optional


class CostTracker:
    """
    Calculates estimated AI model usage cost and enforces an optional
    per-request budget cap.
    """

    MODEL_PRICING = {
        # Keep pricing configurable so it can be updated
        # when the team finalizes the model.
        "gemma-4-26b-a4b-it": {
            "input": 0.0,
            "output": 0.0,
        },
        "gemma-4-31b-it": {
            "input": 0.0,
            "output": 0.0,
        },
    }

    @staticmethod
    def _validate_token_count(
        name: str,
        value: int,
    ) -> None:
        """Validate an individual token count."""

        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be a non-negative integer")

        if value < 0:
            raise ValueError(f"{name} must be a non-negative integer")

    @staticmethod
    def _validate_budget_cap(
        budget_cap: Optional[float],
    ) -> None:
        """Validate an optional budget cap."""

        if budget_cap is None:
            return

        if isinstance(budget_cap, bool) or not isinstance(
            budget_cap,
            (int, float),
        ):
            raise TypeError("budget_cap must be a non-negative number")

        if budget_cap < 0:
            raise ValueError("budget_cap must be a non-negative number")

    @staticmethod
    def calculate_cost(
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        budget_cap: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculate estimated model cost.

        If ``budget_cap`` is supplied, the result includes:
        - ``budget_cap``
        - ``budget_exceeded``

        The calculation remains backward compatible with
        existing AI Gateway usage.
        """

        if not isinstance(model, str) or not model.strip():
            raise ValueError("model must be a non-empty string")

        CostTracker._validate_token_count(
            "prompt_tokens",
            prompt_tokens,
        )
        CostTracker._validate_token_count(
            "completion_tokens",
            completion_tokens,
        )
        CostTracker._validate_budget_cap(budget_cap)

        pricing = CostTracker.MODEL_PRICING.get(model)

        # Preserve existing behavior for models whose pricing
        # is not configured yet.
        if pricing is None:
            result: Dict[str, Any] = {
                "model": model,
                "input_cost": 0.0,
                "output_cost": 0.0,
                "estimated_cost": 0.0,
            }

            if budget_cap is not None:
                result["budget_cap"] = round(
                    float(budget_cap),
                    6,
                )
                result["budget_exceeded"] = False

            return result

        input_price = pricing.get("input", 0.0)
        output_price = pricing.get("output", 0.0)

        if not isinstance(input_price, (int, float)):
            raise TypeError("input pricing must be numeric")

        if not isinstance(output_price, (int, float)):
            raise TypeError("output pricing must be numeric")

        if input_price < 0:
            raise ValueError("input pricing must be non-negative")

        if output_price < 0:
            raise ValueError("output pricing must be non-negative")

        input_cost = (prompt_tokens / 1000) * input_price
        output_cost = (completion_tokens / 1000) * output_price
        total_cost = input_cost + output_cost

        result = {
            "model": model,
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "estimated_cost": round(total_cost, 6),
        }

        if budget_cap is not None:
            result["budget_cap"] = round(
                float(budget_cap),
                6,
            )
            result["budget_exceeded"] = total_cost > budget_cap

        return result
