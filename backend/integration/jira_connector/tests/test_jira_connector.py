import pytest
from connector_sdk import AssetType, SyncStatus

from jira_connector import FakeJiraAPIClient, InMemoryPlatformClient, JiraConnector
from jira_connector.auth import JiraAuthError, JiraTokenAuth


# ---- discovery / normalization (status sync back to platform) ----------


def test_discover_returns_ticket_assets():
    connector = JiraConnector(
        base_url="https://acme.atlassian.net",
        project_key="SEC",
        client=FakeJiraAPIClient(),
    )
    assets = list(connector.discover())

    assert len(assets) == 2
    assert all(a.type == AssetType.TICKET for a in assets)
    assert all(a.source == "jira" for a in assets)


def test_discovered_tickets_carry_status_tag():
    connector = JiraConnector(base_url="https://acme.atlassian.net", project_key="SEC", client=FakeJiraAPIClient())
    assets = {a.id: a for a in connector.discover()}

    assert assets["SEC-101"].tags["status"] == "In Progress"
    assert assets["SEC-102"].tags["status"] == "Done"


def test_ingest_pushes_ticket_status_to_platform():
    platform = InMemoryPlatformClient()
    connector = JiraConnector(
        base_url="https://acme.atlassian.net",
        project_key="SEC",
        client=FakeJiraAPIClient(),
        platform_client=platform,
    )
    assets = list(connector.discover())
    pushed = connector.ingest(assets)

    assert pushed == 2
    assert platform.pushed == assets


def test_sync_success_path():
    connector = JiraConnector(base_url="https://acme.atlassian.net", project_key="SEC", client=FakeJiraAPIClient())
    result = connector.sync()

    assert result.status == SyncStatus.SUCCESS
    assert result.assets_discovered == 2
    assert result.assets_pushed == 2


def test_sync_reports_failure_when_push_fails():
    connector = JiraConnector(
        base_url="https://acme.atlassian.net",
        project_key="SEC",
        client=FakeJiraAPIClient(),
        platform_client=InMemoryPlatformClient(fail=True),
    )
    result = connector.sync()

    assert result.status == SyncStatus.FAILED
    assert result.assets_pushed == 0
    assert len(result.errors) == 1


# ---- ticket creation from exposures (direction 1) -----------------------


def test_create_ticket_from_exposure_returns_ticket_asset():
    fake_client = FakeJiraAPIClient()
    connector = JiraConnector(base_url="https://acme.atlassian.net", project_key="SEC", client=fake_client)

    exposure = {"title": "Public S3 bucket", "description": "Bucket demo-app-uploads allows public read."}
    ticket = connector.create_ticket_from_exposure(exposure)

    assert ticket.type == AssetType.TICKET
    assert ticket.name == "Public S3 bucket"
    assert ticket.id.startswith("SEC-")
    assert len(fake_client.created_issues) == 1


def test_create_ticket_uses_platform_exposure_label():
    fake_client = FakeJiraAPIClient()
    connector = JiraConnector(base_url="https://acme.atlassian.net", project_key="SEC", client=fake_client)

    connector.create_ticket_from_exposure({"title": "x", "description": "y"})
    created = fake_client.created_issues[0]

    assert "platform-exposure" in created["fields"]["labels"]


# ---- health check --------------------------------------------------


def test_check_health_true_and_false():
    healthy = JiraConnector(base_url="https://acme.atlassian.net", project_key="SEC", client=FakeJiraAPIClient())
    unhealthy = JiraConnector(
        base_url="https://acme.atlassian.net", project_key="SEC", client=FakeJiraAPIClient(fail_ping=True)
    )

    assert healthy.check_health() is True
    assert unhealthy.check_health() is False


def test_check_health_false_when_no_credentials_configured():
    connector = JiraConnector(base_url="https://acme.atlassian.net", project_key="SEC")
    assert connector.check_health() is False


# ---- config / credential schemas ---------------------------------------


def test_describe_config_and_credentials_are_schema_dicts():
    connector = JiraConnector(base_url="https://acme.atlassian.net", project_key="SEC", client=FakeJiraAPIClient())

    config_schema = connector.describe_config()
    cred_schema = connector.describe_credentials()

    assert "base_url" in config_schema["properties"]
    assert "project_key" in config_schema["properties"]

    assert cred_schema["properties"]["api_token"]["secret"] is True
    assert "email" in cred_schema["required"]
    assert "api_token" in cred_schema["required"]


# ---- auth module ------------------------------------------------------


def test_auth_builds_basic_auth_header():
    auth = JiraTokenAuth(email="bot@acme.com", api_token="tok123")
    headers = auth.basic_auth_header()
    assert headers["Authorization"].startswith("Basic ")


def test_auth_rejects_invalid_email():
    auth = JiraTokenAuth(email="not-an-email", api_token="tok123")
    with pytest.raises(JiraAuthError):
        auth.validate()


def test_auth_rejects_missing_token():
    auth = JiraTokenAuth(email="bot@acme.com", api_token="")
    with pytest.raises(JiraAuthError):
        auth.validate()
