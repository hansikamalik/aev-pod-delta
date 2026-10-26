"""
Unit tests for P1-3: Persistent Spend Tracking & External Alert Webhooks.
Tests Slack Block Kit formatting, PagerDuty Events v2 payload, threshold triggers (80%, 100%),
and PostgreSQL spend record persistence.
"""

from unittest.mock import MagicMock, patch
import httpx
import pytest

from app.alerts import dispatch_budget_alert, send_pagerduty_alert, send_slack_alert
from app.config import settings
from app.cost_tracker import CostTracker


@pytest.fixture(autouse=True)
def clean_cost_state():
    CostTracker.reset_org_spend()
    CostTracker.clear_notification_hooks()
    yield
    CostTracker.reset_org_spend()
    CostTracker.clear_notification_hooks()


class TestExternalAlertWebhooks:
    """Test webhook payload formatting and network dispatch."""

    def test_send_slack_alert_success(self, monkeypatch):
        """Verify Slack Block Kit payload is correctly structured and dispatched."""
        sent_payloads = []

        class _FakeResponse:
            status_code = 200
            text = "ok"
            is_success = True

        class _FakeClient:
            def __init__(self, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def post(self, url, **kwargs):
                sent_payloads.append(kwargs.get("json", {}))
                return _FakeResponse()

        monkeypatch.setattr("app.alerts.httpx.Client", _FakeClient)

        alert_data = {
            "org_id": "fintech_org",
            "threshold": 0.8,
            "threshold_percent": 80,
            "running_spend": 85.00,
            "budget_cap": 100.00,
            "exceeded": False,
        }
        success = send_slack_alert(alert_data, webhook_url="https://hooks.slack.com/services/TEST/SLACK/HOOK")

        assert success is True
        assert len(sent_payloads) == 1
        sent_payload = sent_payloads[0]
        assert "fintech_org" in sent_payload["text"]
        assert sent_payload["blocks"][0]["type"] == "header"
        fields = sent_payload["blocks"][2]["fields"]
        assert any("80%" in f["text"] for f in fields)
        assert any("85.0000" in f["text"] for f in fields)

    def test_send_pagerduty_alert_success(self, monkeypatch):
        """Verify PagerDuty Events v2 payload is correctly structured and dispatched."""
        sent_payloads = []

        class _FakeResponse:
            status_code = 202
            text = "Enqueued."
            is_success = True

        class _FakeClient:
            def __init__(self, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def post(self, url, **kwargs):
                sent_payloads.append(kwargs.get("json", {}))
                return _FakeResponse()

        monkeypatch.setattr("app.alerts.httpx.Client", _FakeClient)

        alert_data = {
            "org_id": "cloud_corp",
            "threshold": 1.0,
            "threshold_percent": 100,
            "running_spend": 510.00,
            "budget_cap": 500.00,
            "exceeded": True,
        }
        success = send_pagerduty_alert(alert_data, webhook_url_or_key="https://events.pagerduty.com/v2/enqueue")

        assert success is True
        assert len(sent_payloads) == 1
        sent_payload = sent_payloads[0]
        assert sent_payload["event_action"] == "trigger"
        assert sent_payload["payload"]["severity"] == "critical"
        assert "cloud_corp" in sent_payload["payload"]["summary"]

    def test_skip_when_webhook_url_empty(self):
        alert_data = {"org_id": "org_x", "threshold_percent": 80}
        assert send_slack_alert(alert_data, webhook_url="") is False
        assert send_pagerduty_alert(alert_data, webhook_url_or_key="") is False


class TestCostTrackerThresholdBreachAndPersistence:
    """Test threshold triggers and DB spend recording."""

    def test_threshold_breach_triggers_registered_webhook_dispatcher(self, monkeypatch):
        dispatched_alerts = []

        def mock_dispatcher(data):
            dispatched_alerts.append(data)
            return {"slack": True, "pagerduty": True}

        CostTracker.register_notification_hook(mock_dispatcher)
        CostTracker.set_org_budget_cap("org-threshold-test", 100.0)

        fake_pricing = {"paid-model": {"input": 10.0, "output": 10.0}}

        with patch.dict(CostTracker.MODEL_PRICING, fake_pricing, clear=False):
            # 1. Spend $50 (50% - no alert)
            r1 = CostTracker.calculate_cost(
                model="paid-model",
                prompt_tokens=2500,
                completion_tokens=2500,
                org_id="org-threshold-test",
            )
            assert len(dispatched_alerts) == 0

            # 2. Spend another $35 -> total $85 (85% -> triggers 80% warning)
            r2 = CostTracker.calculate_cost(
                model="paid-model",
                prompt_tokens=1750,
                completion_tokens=1750,
                org_id="org-threshold-test",
            )
            assert len(dispatched_alerts) == 1
            assert dispatched_alerts[0]["threshold_percent"] == 80
            assert dispatched_alerts[0]["running_spend"] == 85.0

            # 3. Spend another $20 -> total $105 (105% -> triggers 100% cap exceeded)
            r3 = CostTracker.calculate_cost(
                model="paid-model",
                prompt_tokens=1000,
                completion_tokens=1000,
                org_id="org-threshold-test",
            )
            assert len(dispatched_alerts) == 2
            assert dispatched_alerts[1]["threshold_percent"] == 100
            assert dispatched_alerts[1]["exceeded"] is True

    def test_persistent_spend_db_methods_graceful_handling(self, monkeypatch):
        """Verify DB persistence methods do not raise even if DB connection fails."""
        CostTracker.record_spend_to_db("test_org", 15.50, 1000)
        spend = CostTracker.load_spend_from_db("test_org")
        assert isinstance(spend, float)
