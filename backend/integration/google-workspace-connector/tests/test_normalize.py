from google_workspace_connector.normalize import normalize_audit_event, normalize_user


def test_normalize_user():
    asset = normalize_user(
        {
            "id": "123",
            "primaryEmail": "alice@example.com",
            "name": {"fullName": "Alice Example"},
            "suspended": False,
            "isAdmin": True,
        }
    )
    assert asset.external_id == "123"
    assert asset.name == "Alice Example"
    assert asset.type == "google_workspace_user"
    assert asset.attributes["primary_email"] == "alice@example.com"


def test_normalize_audit_event():
    event = normalize_audit_event(
        {
            "id": {"time": "2026-01-01T00:00:00Z", "applicationName": "login"},
            "actor": {"email": "alice@example.com"},
            "events": [{"name": "login_success"}],
        }
    )
    assert event["type"] == "google_workspace_audit_event"
    assert event["application"] == "login"
