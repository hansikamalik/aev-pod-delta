from types import SimpleNamespace

from app.main import _asset_facts, _explain_match, _fact_check, _freshness_status, app


def sample_asset(**overrides):
    values = {
        "id": 7,
        "asset_name": "Finance Laptop",
        "asset_type": "laptop",
        "operating_system": "Windows 11",
        "ip_address": "10.0.0.7",
        "risk_score": 9,
        "description": "Finance department endpoint",
        "created_at": None,
        "embedding": [0.1, 0.2],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_asset_facts_are_database_grounded():
    facts = _asset_facts(sample_asset())
    assert facts["asset_name"] == "Finance Laptop"
    assert facts["risk_score"] == 9
    assert facts["has_embedding"] is True


def test_fact_check_marks_missing_fields():
    facts = _asset_facts(sample_asset(risk_score=None, description=None))
    result = _fact_check(facts)
    assert "risk_score" in result["unverified_or_missing"]
    assert "description" in result["unverified_or_missing"]


def test_explain_match_mentions_overlapping_stored_terms():
    result = _explain_match("finance laptop", sample_asset())
    assert "finance" in result.lower()


def test_freshness_reports_missing_embedding():
    result = _freshness_status(sample_asset(embedding=None))
    assert result["freshness_status"] == "stale_or_missing"
    assert result["sla_seconds"] == 60


def test_required_copilot_routes_exist():
    paths = {route.path for route in app.routes}
    assert "/copilot/asset-search" in paths
    assert "/copilot/asset-summary/{asset_id}" in paths
    assert "/copilot/exposure-explain/{asset_id}" in paths
    assert "/copilot/remediation-plan/{asset_id}" in paths
    assert "/copilot/executive-summary" in paths
    assert "/copilot/recommendations" in paths


def test_freshness_reports_measured_lag():
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    result = _freshness_status(sample_asset(
        updated_at=now - timedelta(seconds=75),
        embedding_updated_at=now,
    ))
    assert result["measured_lag_seconds"] == 75
    assert result["freshness_status"] == "sla_breached"


def test_fact_check_webhook_not_configured(monkeypatch):
    from app.main import _gateway_fact_check
    monkeypatch.delenv("FACT_CHECK_WEBHOOK_URL", raising=False)
    result = _gateway_fact_check({"asset_name": "test"})
    assert result["status"] == "not_configured"
    assert result["verified"] is False
