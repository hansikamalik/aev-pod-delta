from google_workspace_connector.connector import GoogleWorkspaceConnector


class Auth:
    def credentials(self, config, credentials):
        return object()


def test_schema_contract():
    connector = GoogleWorkspaceConnector(Auth())
    config = connector.config_schema()
    credentials = connector.credential_schema()

    assert "customer_id" in config["required"]
    assert "domain" in config["required"]
    assert "service_account" in credentials["required"]
