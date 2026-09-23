"""Wire the shared contract suite into this connector. Do not skip tests here."""

import pytest

from connector_sdk.testing import ConnectorContractTests, InMemoryPlatformClient

from ..connector import TemplateConnector


class TestTemplateContract(ConnectorContractTests):
    @pytest.fixture
    def connector(self):
        return TemplateConnector(
            config={"region": "eastus"},
            credentials={"api_key": "test"},
            client=None,  # TODO: your mock client
            platform_client=InMemoryPlatformClient(),
        )
