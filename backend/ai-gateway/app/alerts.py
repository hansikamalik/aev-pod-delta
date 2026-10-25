"""
External Alert Webhook Dispatcher for Slack and PagerDuty (P1-3).
Dispatches rich notifications when an organization breaches spend thresholds (80%, 100%).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

from app.config import settings

logger = logging.getLogger("ai_gateway.alerts")


def send_slack_alert(alert_data: Dict[str, Any], webhook_url: Optional[str] = None) -> bool:
    """Send formatted Block Kit budget alert to Slack incoming webhook URL."""
    url = webhook_url or getattr(settings, "SLACK_ALERT_WEBHOOK_URL", "") or os.getenv("SLACK_ALERT_WEBHOOK_URL", "")
    if not url:
        logger.debug("Slack alert skipped: No SLACK_ALERT_WEBHOOK_URL configured.")
        return False

    org_id = alert_data.get("org_id", "unknown")
    threshold_pct = alert_data.get("threshold_percent", 80)
    running_spend = alert_data.get("running_spend", 0.0)
    budget_cap = alert_data.get("budget_cap", 0.0)
    exceeded = alert_data.get("exceeded", False)

    status_icon = "🛑" if exceeded else "⚠️"
    headline = f"{status_icon} Budget Cap Exceeded" if exceeded else f"{status_icon} Budget Threshold Warning ({threshold_pct}%)"

    payload = {
        "text": f"{status_icon} [AEV Alert] {org_id} has reached {threshold_pct}% of budget cap (${running_spend:.2f} / ${budget_cap:.2f})",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{status_icon} AEV AI Gateway Spend Alert", "emoji": True},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{headline}*\nOrganization *{org_id}* has consumed *{threshold_pct}%* of its allocated monthly LLM budget.",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Organization:*\n`{org_id}`"},
                    {"type": "mrkdwn", "text": f"*Threshold:*\n`{threshold_pct}%`"},
                    {"type": "mrkdwn", "text": f"*Current Spend:*\n`${running_spend:.4f}`"},
                    {"type": "mrkdwn", "text": f"*Budget Cap:*\n`${budget_cap:.2f}`"},
                ],
            },
        ],
    }

    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(url, json=payload)
            if resp.is_success:
                logger.info("Successfully dispatched Slack budget alert for org '%s' (%s%%)", org_id, threshold_pct)
                return True
            logger.warning("Slack webhook returned HTTP %d: %s", resp.status_code, resp.text)
            return False
    except Exception as exc:
        logger.error("Failed to deliver Slack webhook: %s", exc)
        return False


def send_pagerduty_alert(alert_data: Dict[str, Any], webhook_url_or_key: Optional[str] = None) -> bool:
    """Send PagerDuty Events API v2 trigger alert on budget breach."""
    target = webhook_url_or_key or getattr(settings, "PAGERDUTY_ALERT_WEBHOOK_URL", "") or os.getenv("PAGERDUTY_ALERT_WEBHOOK_URL", "")
    if not target:
        logger.debug("PagerDuty alert skipped: No PAGERDUTY_ALERT_WEBHOOK_URL configured.")
        return False

    org_id = alert_data.get("org_id", "unknown")
    threshold_pct = alert_data.get("threshold_percent", 80)
    running_spend = alert_data.get("running_spend", 0.0)
    budget_cap = alert_data.get("budget_cap", 0.0)
    exceeded = alert_data.get("exceeded", False)

    endpoint = target if target.startswith("http") else "https://events.pagerduty.com/v2/enqueue"
    routing_key = target if not target.startswith("http") else target.split("/")[-1]

    payload = {
        "routing_key": routing_key,
        "event_action": "trigger",
        "dedup_key": f"aev-gateway-budget-{org_id}-{threshold_pct}",
        "payload": {
            "summary": f"AEV Gateway Spend Alert: Org '{org_id}' reached {threshold_pct}% of budget (${running_spend:.2f}/${budget_cap:.2f})",
            "source": "aev-ai-gateway",
            "severity": "critical" if exceeded else "warning",
            "component": "ai-gateway",
            "group": "finance-and-governance",
            "custom_details": alert_data,
        },
    }

    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(endpoint, json=payload)
            if resp.is_success or resp.status_code in (200, 201, 202):
                logger.info("Successfully dispatched PagerDuty budget alert for org '%s' (%s%%)", org_id, threshold_pct)
                return True
            logger.warning("PagerDuty webhook returned HTTP %d: %s", resp.status_code, resp.text)
            return False
    except Exception as exc:
        logger.error("Failed to deliver PagerDuty alert: %s", exc)
        return False


def dispatch_budget_alert(alert_data: Dict[str, Any]) -> Dict[str, bool]:
    """Top-level handler registered with CostTracker to notify external channels."""
    slack_sent = send_slack_alert(alert_data)
    pd_sent = send_pagerduty_alert(alert_data)
    return {"slack": slack_sent, "pagerduty": pd_sent}
