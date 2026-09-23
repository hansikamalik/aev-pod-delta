"""The shared contract suite, run against the SDK's own fake connector.

Proves the suite passes for a compliant connector. Each real connector adds
its own subclass; see connectors/README or the sample connector tests.
"""

import pytest

from connector_sdk.testing import ConnectorContractTests, FakeConnector


class TestFakeConnectorContract(ConnectorContractTests):
    @pytest.fixture
    def connector(self):
        return FakeConnector()
