from typing import Dict


class CostTracker:
    """
    Calculates estimated AI model usage cost
    based on input and output token counts.
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
    def calculate_cost(
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> Dict[str, float]:
        pricing = CostTracker.MODEL_PRICING.get(model)

        if pricing is None:
            return {
                "model": model,
                "input_cost": 0.0,
                "output_cost": 0.0,
                "estimated_cost": 0.0,
            }

        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]

        total_cost = input_cost + output_cost

        return {
            "model": model,
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "estimated_cost": round(total_cost, 6),
        }