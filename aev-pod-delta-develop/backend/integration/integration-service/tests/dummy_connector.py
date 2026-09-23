"""
A fake/dummy connector used only to prove the shared Connector
interface actually works end-to-end. Not a real integration -
no real API calls, just hardcoded fake data.
"""
from app.connector_interface import Asset, Connector, SyncResult


class DummyConnector(Connector):
    def discover(self) -> list[Asset]:
        return [
            Asset(id="dummy-1", type="server", name="Test Server 1"),
            Asset(id="dummy-2", type="database", name="Test DB 1"),
        ]

    def ingest(self) -> list[Asset]:
        return self.discover()

    def sync(self) -> SyncResult:
        assets = self.ingest()
        return SyncResult(success=True, records_synced=len(assets))

    def health_check(self) -> bool:
        return True

    def get_config_schema(self) -> dict:
        return {"region": "string"}

    def get_credential_schema(self) -> dict:
        return {"api_key": "string"}
