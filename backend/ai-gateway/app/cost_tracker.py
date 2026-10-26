"""AI model cost calculation, persistent spend tracking, and budget-cap enforcement."""

import logging
import os
from datetime import datetime, timezone
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

    # ---- Persistent Database Spend Methods (P1-3) ---------------------------

    @classmethod
    def _ensure_spend_table(cls) -> None:
        """Create ai_spend_records table in PostgreSQL if it does not exist."""
        db_url = os.getenv("DATABASE_URL", "postgresql://aev:secret@localhost:5432/aevdb")
        try:
            import psycopg
            with psycopg.connect(db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS ai_spend_records (
                            id SERIAL PRIMARY KEY,
                            org_id VARCHAR(128) NOT NULL,
                            window_start TIMESTAMPTZ NOT NULL,
                            total_cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0.0,
                            token_count BIGINT NOT NULL DEFAULT 0,
                            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                        );
                        CREATE INDEX IF NOT EXISTS idx_spend_org
                            ON ai_spend_records (org_id, window_start);
                    """)
                    conn.commit()
        except Exception as exc:
            logger.debug("Spend table ensure skipped: %s", exc)

    @classmethod
    def record_spend_to_db(cls, org_id: str, cost_usd: float, total_tokens: int) -> None:
        """Persist individual spend transaction into PostgreSQL ai_spend_records."""
        db_url = os.getenv("DATABASE_URL", "postgresql://aev:secret@localhost:5432/aevdb")
        now = datetime.now(timezone.utc)
        window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            import psycopg
            with psycopg.connect(db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO ai_spend_records
                            (org_id, window_start, total_cost_usd, token_count)
                        VALUES (%s, %s, %s, %s);
                    """, (org_id, window_start, cost_usd, total_tokens))
                    conn.commit()
        except Exception as exc:
            logger.debug("Database spend persistence skipped: %s", exc)

    @classmethod
    def load_spend_from_db(cls, org_id: str) -> float:
        """Load cumulative spend for an organization from PostgreSQL."""
        db_url = os.getenv("DATABASE_URL", "postgresql://aev:secret@localhost:5432/aevdb")
        try:
            import psycopg
            with psycopg.connect(db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT COALESCE(SUM(total_cost_usd), 0.0)
                        FROM ai_spend_records
                        WHERE org_id = %s;
                    """, (org_id,))
                    row = cur.fetchone()
                    return float(row[0]) if row and row[0] is not None else 0.0
        except Exception:
            return 0.0

    @classmethod
    def sync_spend_from_db(cls, org_id: str) -> float:
        """Synchronize in-memory running spend counter from PostgreSQL records."""
        db_spend = cls.load_spend_from_db(org_id)
        if db_spend > cls._org_spend.get(org_id, 0.0):
            cls._org_spend[org_id] = db_spend
        return cls._org_spend.get(org_id, 0.0)

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
        - budget_cap: optional per-request cap
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

        # Per-org running spend, database persistence, and threshold alerts
        if org_id:
            clean_org = str(org_id).strip()
            prior_spend = cls._org_spend.get(clean_org, 0.0)
            new_spend = round(prior_spend + total_cost, 6)
            cls._org_spend[clean_org] = new_spend

            # P1-3: Persist spend transaction to PostgreSQL
            cls.record_spend_to_db(clean_org, total_cost, prompt_tokens + completion_tokens)

            # Org alerts always use the org's configured cap. The per-request
            # budget_cap (X-Budget-Cap header) must never override it.
            effective_org_cap = cls.get_org_budget_cap(clean_org)

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
