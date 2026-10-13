"""Comprehensive unit and integration tests for CostTracker budget alert functionality."""

from unittest.mock import patch
import pytest
from app.cost_tracker import CostTracker


@pytest.fixture(autouse=True)
def clean_cost_tracker_state():
    CostTracker.reset_org_spend()
    CostTracker.clear_notification_hooks()
    yield
    CostTracker.reset_org_spend()
    CostTracker.clear_notification_hooks()


def test_budget_alert_fake_pricing_and_running_spend():
    """Verify that fake pricing correctly accumulates running spend per org."""
    fake_pricing = {
        "fake-model-1": {
            "input": 1.0,   # $1.00 per 1000 tokens
            "output": 2.0,  # $2.00 per 1000 tokens
        }
    }

    with patch.dict(CostTracker.MODEL_PRICING, fake_pricing, clear=False):
        # Request 1: 1000 prompt tokens ($1.00) + 1000 completion tokens ($2.00) = $3.00
        r1 = CostTracker.calculate_cost(
            model="fake-model-1",
            prompt_tokens=1000,
            completion_tokens=1000,
            org_id="org-alpha",
        )
        assert r1["estimated_cost"] == 3.0
        assert r1["running_spend"] == 3.0
        assert CostTracker.get_org_spend("org-alpha") == 3.0

        # Request 2: Another $3.00 -> total running spend $6.00
        r2 = CostTracker.calculate_cost(
            model="fake-model-1",
            prompt_tokens=1000,
            completion_tokens=1000,
            org_id="org-alpha",
        )
        assert r2["estimated_cost"] == 3.0
        assert r2["running_spend"] == 6.0
        assert CostTracker.get_org_spend("org-alpha") == 6.0


def test_threshold_alerts_80_and_100_percent():
    """Verify threshold levels (80% and 100%) fire correctly."""
    fake_pricing = {
        "fake-model-1": {
            "input": 1.0,
            "output": 0.0,
        }
    }

    # Set budget cap of $10.00 for org-beta
    CostTracker.set_org_budget_cap("org-beta", 10.0)

    alerts_received = []
    CostTracker.register_notification_hook(lambda data: alerts_received.append(data))

    with patch.dict(CostTracker.MODEL_PRICING, fake_pricing, clear=False):
        # Request 1: Spend $5.00 (50%) -> no alert
        r1 = CostTracker.calculate_cost(
            model="fake-model-1",
            prompt_tokens=5000,
            completion_tokens=0,
            org_id="org-beta",
        )
        assert r1["running_spend"] == 5.0
        assert len(alerts_received) == 0

        # Request 2: Spend another $3.50 -> running spend $8.50 (85%) -> triggers 80% alert
        r2 = CostTracker.calculate_cost(
            model="fake-model-1",
            prompt_tokens=3500,
            completion_tokens=0,
            org_id="org-beta",
        )
        assert r2["running_spend"] == 8.5
        assert len(alerts_received) == 1
        assert alerts_received[0]["threshold"] == 0.8
        assert alerts_received[0]["threshold_percent"] == 80

        # Request 3: Spend another $0.50 -> running spend $9.00 (90%) -> 80% should NOT fire again!
        r3 = CostTracker.calculate_cost(
            model="fake-model-1",
            prompt_tokens=500,
            completion_tokens=0,
            org_id="org-beta",
        )
        assert r3["running_spend"] == 9.0
        assert len(alerts_received) == 1  # Hook fired once only!

        # Request 4: Spend another $1.50 -> running spend $10.50 (105%) -> triggers 100% alert
        r4 = CostTracker.calculate_cost(
            model="fake-model-1",
            prompt_tokens=1500,
            completion_tokens=0,
            org_id="org-beta",
        )
        assert r4["running_spend"] == 10.5
        assert r4["org_budget_exceeded"] is True
        assert len(alerts_received) == 2
        assert alerts_received[1]["threshold"] == 1.0
        assert alerts_received[1]["threshold_percent"] == 100


def test_notification_hook_fires_once_only():
    """Verify notification hook fires once rather than on every subsequent request."""
    fake_pricing = {"fake-model": {"input": 1.0, "output": 0.0}}
    CostTracker.set_org_budget_cap("test-corp", 10.0)

    call_count = {"count": 0}

    def _hook(d):
        call_count["count"] += 1

    CostTracker.register_notification_hook(_hook)

    with patch.dict(CostTracker.MODEL_PRICING, fake_pricing, clear=False):
        # Cross 100% immediately ($12 spend)
        CostTracker.calculate_cost(
            model="fake-model",
            prompt_tokens=12000,
            completion_tokens=0,
            org_id="test-corp",
        )
        # Should have fired 80% and 100% once
        assert call_count["count"] == 2

        # Another request still over 100% ($2 more)
        CostTracker.calculate_cost(
            model="fake-model",
            prompt_tokens=2000,
            completion_tokens=0,
            org_id="test-corp",
        )
        # Count must remain 2! No repeat firing on subsequent requests!
        assert call_count["count"] == 2


def test_org_mapping_and_cap_passing_in_query():
    """Verify that main.py query endpoint passes cap and maps org correctly."""
    from fastapi.testclient import TestClient
    from app.main import app

    fake_pricing = {"gemma-4-31b-it": {"input": 1.0, "output": 1.0}}

    with (
        patch.dict(CostTracker.MODEL_PRICING, fake_pricing, clear=False),
        patch("app.main.ask_gpt", return_value={
            "answer": "Test response",
            "model": "gemma-4-31b-it",
            "usage": {"prompt_tokens": 1000, "completion_tokens": 1000, "total_tokens": 2000},
        }),
        patch("app.main.check_rate_limit", return_value={"allowed": True}),
    ):

        with TestClient(app) as client:
            resp = client.post(
                "/copilot/query",
                headers={
                    "X-User-ID": "alice@acme.com",
                    "X-Org-ID": "acme-corp",
                    "X-Budget-Cap": "50.0",
                },
                json={"question": "What is IAM?"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["cost"]["org_id"] == "acme-corp"
            assert data["cost"]["budget_cap"] == 50.0
            assert data["cost"]["running_spend"] > 0
