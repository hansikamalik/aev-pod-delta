class PublicConnectorSDK:
    """Public SDK base class for all enterprise connectors."""
    def __init__(self, connector_id: str):
        self.connector_id = connector_id
