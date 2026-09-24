from config import get_config_schema, get_credentials_schema
from models import normalize_splunk_event_to_asset


def test_splunk_vault_schema_isolation():
    config_schema = get_config_schema()
    cred_schema = get_credentials_schema()

    assert "bearer_token" not in config_schema.get("properties", {})
    
    cred_props = cred_schema.get("properties", {})
    assert cred_props["bearer_token"]["secret"] is True


def test_splunk_event_sanitization():
    leaky_event = {
        "_cd": "1:50",
        "_time": "2026-09-24T12:00:00Z",
        "_raw": "User Login Success",
        "bearer_token": "SENSITIVE_LEAKED_TOKEN",
        "session_key": "SECRET_SESSION"
    }

    asset = normalize_splunk_event_to_asset(leaky_event, "splunk")

    assert "bearer_token" not in asset.raw
    assert "session_key" not in asset.raw
    assert asset.id == "1:50"
    assert asset.source == "splunk"
