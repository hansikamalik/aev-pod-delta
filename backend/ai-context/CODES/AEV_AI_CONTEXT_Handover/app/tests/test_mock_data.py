"""Contract and end-to-end checks for the configured shared mock source."""
from app.mock_data import get_mock_data


def test_shared_mock_data_has_required_collections_and_restricted_records():
    data = get_mock_data()
    for key in ("assets", "exposures", "risk_scores", "users", "roles", "audit_events", "integrations"):
        assert isinstance(data[key], list) and data[key], key
    assert any(item.get("visibility") == "admin_only" for item in data["assets"])
    assert any(item["outcome"] == "denied" for item in data["audit_events"])
    assert any(user["role_id"] == "role_viewer" for user in data["users"])
    assert all("password" not in item and "token" not in item for item in data["integrations"])


def test_mock_asset_contract_is_pod_beta_provider_neutral():
    data = get_mock_data()
    asset = data["assets"][0]
    assert {"id", "asset_name", "asset_type", "risk_score", "visibility"} <= set(asset)
    assert data["schema_version"]
    assert data["source"] == "mock"
