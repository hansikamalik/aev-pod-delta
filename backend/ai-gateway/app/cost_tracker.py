"""AI model cost calculation and budget-cap enforcement."""

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("ai_gateway.cost_tracker")


class CostTracker:
    """
    Calculates estimated AI model usage cost and enforces an optional
    per-request budget cap, per-org budget cap, running spend tracking,
    threshold alerts (e.g. 80%, 100%), and notification hooks.
    """

    MODEL_PRICING = {
        # Configurable pricing table (per 1000 tokens)
        "gemma-4-26b-a4b-it": {
            "input": 0.0,
            "output": 0.0,
        },
        "gemma-4-31b-it": {
            "input": 0.0,
            "output": 0.0,
        },
    }

    # Running spend tracking per organization: {org_id: float}
    _org_spend: Dict[str, float] = {}

    # Track fired threshold notifications per org to fire only once: {org_id: set(thresholds)}
    _org_alerted_thresholds: Dict[str, set] = {}

    # Notification callback hooks: list of callables receiving (alert_data: dict)
    _notification_hooks: List[Callable[[Dict[str, Any]], None]] = []

    # Configured per-org budget caps: {org_id: float}
    ORG_BUDGET_CAPS: Dict[str, float] = {
        "default": 100.0,
        "free": 10.0,
        "pro": 100.0,
        "enterprise": 500.0,
    }

    ALERT_THRESHOLDS = (0.8, 1.0)  # 80% warning, 100% cap reached

    @classmethod
    def reset_org_spend(cls, org_id: Optional[str] = None) -> None:
        """Reset running spend and alert history (useful for tests and billing resets)."""
        if org_id:
            cls._org_spend.pop(org_id, None)
            cls._org_alerted_thresholds.pop(org_id, None)
        else:
            cls._org_spend.clear()
            cls._org_alerted_thresholds.clear()

    @classmethod
    def get_org_spend(cls, org_id: str) -> float:
        """Get current running spend for an organization."""
        return cls._org_spend.get(org_id, 0.0)

    @classmethod
    def set_org_budget_cap(cls, org_id: str, cap: float) -> None:
        """Set a budget cap for an organization."""
        cls._validate_budget_cap(cap)
        cls.ORG_BUDGET_CAPS[org_id] = float(cap)

    @classmethod
    def get_org_budget_cap(cls, org_id: str) -> Optional[float]:
        """Get budget cap for an organization, falling back to default."""
        return cls.ORG_BUDGET_CAPS.get(org_id, cls.ORG_BUDGET_CAPS.get("default"))

    @classmethod
    def register_notification_hook(cls, hook: Callable[[Dict[str, Any]], None]) -> None:
        """Register a notification hook callable that triggers on threshold breach."""
        if callable(hook) and hook not in cls._notification_hooks:
            cls._notification_hooks.append(hook)

    @classmethod
    def clear_notification_hooks(cls) -> None:
        """Clear all registered notification hooks."""
        cls._notification_hooks.clear()

    @classmethod
    def _fire_notification(cls, alert_data: Dict[str, Any]) -> None:
        """Fire all registered notification hooks and log the alert."""
        logger.warning("Budget alert triggered: %s", alert_data)
        for hook in cls._notification_hooks:
            try:
                hook(alert_data)
            except Exception as exc:
                logger.error("Notification hook failed: %s", exc, exc_info=True)

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

    @classmethod
    def calculate_cost(
        cls,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        budget_cap: Optional[float] = None,
        org_id: Optional[str] = None,
        thresholds: tuple = ALERT_THRESHOLDS,
    ) -> Dict[str, Any]:
        """
        Calculate estimated model cost and enforce budget caps.

        Parameters:
        - model: model identifier
        - prompt_tokens: number of prompt tokens
        - completion_tokens: number of completion tokens
        - budget_cap: optional per-request cap or override
        - org_id: organization identifier for running spend and per-org cap
        - thresholds: alert percentage levels, default (0.8, 1.0)
        """
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model must be a non-empty string")

        cls._validate_token_count("prompt_tokens", prompt_tokens)
        cls._validate_token_count("completion_tokens", completion_tokens)
        cls._validate_budget_cap(budget_cap)

        pricing = cls.MODEL_PRICING.get(model)

        if pricing is None:
            total_cost = 0.0
            input_cost = 0.0
            output_cost = 0.0
        else:
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

        result: Dict[str, Any] = {
            "model": model,
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "estimated_cost": round(total_cost, 6),
        }

        # Per-request budget cap
        if budget_cap is not None:
            result["budget_cap"] = round(float(budget_cap), 6)
            result["budget_exceeded"] = total_cost > budget_cap

        # Per-org running spend and threshold alerts
        if org_id:
            clean_org = str(org_id).strip()
            prior_spend = cls._org_spend.get(clean_org, 0.0)
            new_spend = round(prior_spend + total_cost, 6)
            cls._org_spend[clean_org] = new_spend

            effective_org_cap = (
                budget_cap if budget_cap is not None else cls.get_org_budget_cap(clean_org)
            )

            result["org_id"] = clean_org
            result["running_spend"] = new_spend
            result["org_budget_cap"] = effective_org_cap

            if effective_org_cap and effective_org_cap > 0:
                result["spend_percentage"] = round((new_spend / effective_org_cap) * 100, 2)
                result["org_budget_exceeded"] = new_spend >= effective_org_cap

                alerted = cls._org_alerted_thresholds.setdefault(clean_org, set())
                alerts_triggered = []

                for th in sorted(thresholds):
                    threshold_spend = effective_org_cap * th
                    if new_spend >= threshold_spend and th not in alerted:
                        alerted.add(th)
                        alert_info = {
                            "org_id": clean_org,
                            "threshold": th,
                            "threshold_percent": int(th * 100),
                            "running_spend": new_spend,
                            "budget_cap": effective_org_cap,
                            "exceeded": new_spend >= effective_org_cap,
                        }
                        alerts_triggered.append(alert_info)
                        cls._fire_notification(alert_info)

                if alerts_triggered:
                    result["alerts_triggered"] = alerts_triggered

        return result
